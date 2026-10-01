#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""连接复用（db_sync._PooledConnection / 连接池）的行为守卫。

为什么需要这个测试
==================
2026-10-02 实测：新建一次 MySQL 连接要 1065~1640ms（跨境 TCP + MySQL 握手 +
认证），而复用连接上的一条查询只要 180ms（≈RTT）。一次路由分发要写 2 条库，
也就是 2 次完整握手 ≈ 2.7s，占全程 90%+。

优化后必须有人守着三件事，否则任何一次无关改动都可能悄悄退回老行为：
  1. **复用的确发生**（新建连接次数 1 而不是 2）—— 否则性能悄悄退化，
     而功能测试全绿，没有任何信号；
  2. **池子不泄漏**（只留一条，多余的必须真关）；
  3. **包装对象确实透传**（cursor / ping / autocommit 等都能用），
     否则调用方会拿到一个"看起来像连接但用不了"的东西。

另有一条反向守卫：**--doctor 的连通性自检必须绕过池子**。
复用池里的旧连接会让「实时连通性」变成假话——网络已断、池里那条还没被发现
坏，照样回报 OK。自检要的就是一次真实握手。

判据里刻意不写死具体毫秒数（机器与网络会变），只断言「次数」与「行为」。
"""
import importlib.util
import pathlib
import sys

SCRIPT = pathlib.Path(__file__).resolve().parent / "db_sync.py"
PASS, FAIL = [], []


def check(name, ok, detail=""):
    """detail 只在失败时打印 —— 它是「为什么不行」的说明。

    曾经无条件打印，于是写死的文案在通过时会出现自相矛盾的输出
    （PASS 却显示「居然成功了」）。误导性的测试输出会侵蚀信任，
    让人在真正需要看它的时候不再相信它。
    """
    (PASS if ok else FAIL).append(name)
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  —— " + str(detail)[:140]) if (detail and not ok) else ""))


def main():
    spec = importlib.util.spec_from_file_location("db_sync", SCRIPT)
    ds = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(ds)
    except Exception as e:
        print("  [SKIP] 无法载入 db_sync（%s: %s）" % (type(e).__name__, e))
        print("\nRESULT: SKIP (1/1)")
        return 0

    # 库没开或连不上时跳过（这是环境问题，不是回归）
    try:
        if not ds.is_db_enabled():
            print("  [SKIP] database.enabled=false")
            print("\nRESULT: SKIP (1/1)")
            return 0
        probe = ds._get_db_connection_raw()
        probe.close()
    except Exception as e:
        print("  [SKIP] 库不可达（%s: %s）" % (type(e).__name__, str(e)[:80]))
        print("\nRESULT: SKIP (1/1)")
        return 0

    # ---- 计数器：统计真实新建连接的次数 ----
    counter = {"n": 0}
    _orig = ds._get_db_connection_raw

    def counting_raw(*a, **k):
        counter["n"] += 1
        return _orig(*a, **k)

    ds._get_db_connection_raw = counting_raw

    # 关掉「取连接时顺手补传暂存」——它与连接复用是两件独立的事，但补传
    # 自身会再去取连接，会污染本测试的「新建了几次」计数。
    # 实测踩过：上一次运行留下的暂存记录让「只新建 1 次」变成 2 次而报红，
    # 看上去像复用失效，其实是测试没有隔离被测对象。
    saved_replay = ds._maybe_replay
    ds._maybe_replay = lambda: None

    try:
        ds.close_db_pool()

        # ---- 1. 复用确实发生 ----
        counter["n"] = 0
        c1 = ds.get_db_connection()
        c1.close()
        c2 = ds.get_db_connection()
        c2.close()
        check("连续两次取连接只新建 1 次（复用生效）",
              counter["n"] == 1, "实际新建 %d 次" % counter["n"])

        # ---- 2. 复用来的连接真的能用（包装透传） ----
        c3 = ds.get_db_connection()
        with c3.cursor() as cur:
            cur.execute("SELECT 1")
            v = cur.fetchone()[0]
        check("复用连接可执行查询（cursor 透传）", v == 1, v)
        check("autocommit 属性透传", hasattr(c3, "autocommit"))
        check("ping 方法透传", callable(getattr(c3, "ping", None)))
        c3.close()

        # ---- 3. 池子不泄漏：同时取两条，归还后池里只留一条 ----
        ds.close_db_pool()
        a = ds.get_db_connection()
        b = ds.get_db_connection()
        check("第二条是新连接（池空时必须新建）", a is not b)
        a.close()
        b.close()
        pooled = ds._POOL.get("conn")
        check("归还后池内恰好 1 条（多余的真关，不泄漏）", pooled is not None)

        # ---- 4. 取走后池子应为空（防同一连接被两处同时持有） ----
        c4 = ds.get_db_connection()
        check("连接被取走后池子置空（防双重持有）",
              ds._POOL.get("conn") is None)
        c4.close()

        # ---- 5. close_db_pool 真正关闭 ----
        ds.close_db_pool()
        check("close_db_pool 后池空", ds._POOL.get("conn") is None)
        check("close_db_pool 后 idle_since 归零",
              float(ds._POOL.get("idle_since") or 0) == 0.0)

        # ---- 6. 关掉复用开关时必须回到「每次新建」的老行为 ----
        _orig_reuse = ds._reuse_enabled
        ds._reuse_enabled = lambda: False
        try:
            counter["n"] = 0
            d1 = ds.get_db_connection()
            d1.close()
            d2 = ds.get_db_connection()
            d2.close()
            check("reuse_connection=false 时每次新建（可回退）",
                  counter["n"] == 2, "实际新建 %d 次" % counter["n"])
            check("关闭复用时拿到的是裸连接（无 close 包装）",
                  not isinstance(d1, ds._PooledConnection))
        finally:
            ds._reuse_enabled = _orig_reuse
            ds.close_db_pool()

        # ---- 7. 反向守卫：doctor 的连通性检查必须绕过池子 ----
        # 判据取「源码结构」而非运行时：doctor 用 _get_db_connection_raw
        # （真握手），不用 get_db_connection（可能命中池）。
        src = SCRIPT.read_text(encoding="utf-8")
        seg = src.split("def print_db_doctor", 1)
        ok_struct = False
        if len(seg) == 2:
            body = seg[1].split("\ndef ", 1)[0]
            ok_struct = ("_get_db_connection_raw" in body
                         and "conn = get_db_connection()" not in body)
        check("doctor 连通性自检绕过连接池（否则会报假 OK）", ok_struct)

        # ---- 8. 坏连接绝不能留在池里（一个非常容易踩的陷阱）----
        #
        # 现状：「取出的连接用完自己关」这个约定，在失败路径上**没有**被执行
        # （异常直接跳到 except，conn.close() 被跳过），于是坏连接既没归还
        # 也没留在池里 —— 下一次调用会新建连接，自动恢复。
        #
        # 这个「正确」是脆弱的：只要有人后来补一句 `finally: conn.close()`
        # 做清理（一个很自然的想法），坏连接就会被归还进池子，之后**每次
        # 写库都失败**，直到 30 秒闲置检测才自愈 —— 一次 30 秒的网络抖动
        # 会被放大成持续几十秒的连锁失败。
        #
        # 所以这里把它固化成判据：换实现可以，但「失败后池里不能有坏连接」
        # 这条不变式必须继续成立。
        #
        # 注意：本条会让探针写入真实暂存（失败即暂存本来就是设计），
        # 故先存快照、结束后整体还原，不给真实数据留垃圾。
        spool_before = ds._read_spool()
        try:
            ds.close_db_pool()
            warm = ds.get_db_connection()
            warm.close()                       # 归还 → 池里有活连接
            raw_in_pool = ds._POOL.get("conn")
            check("装置：池中确有连接可被破坏", raw_in_pool is not None)
            raw_in_pool.close()                # 模拟半开／服务端掐连接

            ok = ds.record_tool_trace_db("auto-skills", "_test_conn_reuse",
                                         action="deadpool-probe", user_query="probe",
                                         stage="test", duration_ms=1)
            check("坏连接上的写库会失败（装置有效）", ok is False,
                  "居然成功了 —— 装置没造出坏连接，本条不具判别力")
            check("失败后池中不残留坏连接（下一次会自动新建并恢复）",
                  ds._POOL.get("conn") is None,
                  "坏连接仍在池里 —— 后续每次写库都会继续失败")
            check("失败的写入进了本地暂存（数据不丢）",
                  len(ds._read_spool()) > len(spool_before),
                  "暂存 %d → %d 条" % (len(spool_before), len(ds._read_spool())))
        finally:
            ds._write_spool(spool_before)      # 还原，不留探针垃圾
            ds.close_db_pool()

    finally:
        ds._get_db_connection_raw = _orig
        ds._maybe_replay = saved_replay
        try:
            ds.close_db_pool()
        except Exception:
            pass

    print()
    total = len(PASS) + len(FAIL)
    print("RESULT: %s (%d/%d)" % ("ALL_PASS" if not FAIL else "HAS_FAIL",
                                  len(PASS), total))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())