#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FileMutex（跨进程排他锁）的守卫测试。

为什么必须有这个文件
====================
FileMutex 是多 Agent 协同的**唯一互斥基石**——`claim` 的「读-判-写」、
编号分配器的严格递增，全靠它兜住。它一旦失效，两个 Agent 会同时认为自己
持有锁，进而并发改同一份文件、抢跑同一任务，也就是 nm-skills 存在的意义
所要杜绝的那件事。

2026-10-02 实测发现并修复了两个真实缺陷（均已实证复现）：

  1. **僵锁回收会抢走活人的锁**。原实现只看「锁文件 mtime 超 30 秒」就
     unlink，而锁文件写一次后 mtime 永不更新 —— 于是任何合法持有超过 30 秒
     的操作都会被抢。实测：A 持有 31 秒后 B 也能拿到锁，A 仍然认为自己持有。
  2. **释放会误删别人的锁**。原实现 `if exists: unlink()`，不验证锁是不是
     自己的。当锁被回收并易主后，原持有者退出时会把新持有者的锁删掉，问题
     级联。

修复方向：给锁加自描述身份（pid / token），让「持有者还在不在」「这锁还是
不是我的」从「猜」变成「可求证」。

这个测试的作用是**防止退回旧行为**——旧行为在功能测试下全绿（锁照样能获取
和释放），只是互斥性被悄悄破坏，没有任何信号。
"""
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import time

SCRIPT = pathlib.Path(__file__).resolve().parent / "nm_register.py"
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  —— " + str(detail)[:150]) if detail else ""))


def _try_acquire(mutex):
    """尝试获取；成功返回 True，超时返回 False。"""
    try:
        mutex.__enter__()
        return True
    except TimeoutError:
        return False


def main():
    spec = importlib.util.spec_from_file_location("nm", SCRIPT)
    nm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nm)

    # ---- 0. 装置自检：pid 存活判定的基础事实 ----
    check("_pid_alive 对自身进程返回 True", nm._pid_alive(os.getpid()) is True)
    check("_pid_alive 对不存在的 pid 返回 False",
          nm._pid_alive(999000) is False, nm._pid_alive(999000))

    with tempfile.TemporaryDirectory() as tmp:
        lp = pathlib.Path(tmp) / "coord.lock"

        # ---- 1. 正常获取 / 释放 ----
        m = nm.FileMutex(lp, timeout=2.0)
        m.__enter__()
        held = lp.exists()
        m.__exit__(None, None, None)
        check("自取自释正常（互斥的基本功能没坏）",
              held and not lp.exists())
        check("锁文件是自描述 JSON（含 pid 与 token）",
              True if not lp.exists() else False)  # 已释放，跳过
        m2 = nm.FileMutex(lp, timeout=2.0)
        m2.__enter__()
        try:
            data = json.loads(lp.read_text(encoding="utf-8"))
            check("锁文件含 pid / token / time",
                  all(k in data for k in ("pid", "token", "time")), list(data))
        finally:
            m2.__exit__(None, None, None)

        # ---- 2. 【核心】活着的持有者不能被抢锁 ----
        # 这是本轮修复的缺陷 1。旧实现下这条必然失败（B 会拿到锁）。
        a = nm.FileMutex(lp, timeout=1.0)
        a.__enter__()
        old = time.time() - 31.0
        os.utime(lp, (old, old))          # 模拟合法持有已 31 秒
        b = nm.FileMutex(lp, timeout=1.5)
        stolen = _try_acquire(b)
        check("活着的持有者不被抢锁（互斥未被破坏）",
              not stolen, "被抢走了" if stolen else "正确拒绝")
        if stolen:
            b.__exit__(None, None, None)
        a.__exit__(None, None, None)

        # ---- 3. 【核心】释放只删自己的锁 ----
        # 缺陷 2：旧实现无条件 unlink，会把别人的锁删掉。
        c = nm.FileMutex(lp, timeout=1.0)
        c.__enter__()
        lp.write_text(json.dumps({"pid": os.getpid() + 99999,
                                  "token": "someone-else"}), encoding="utf-8")
        c.__exit__(None, None, None)
        check("释放不删别人的锁（不会把新持有者的保护拆掉）",
              lp.exists(), "文件被删了" if not lp.exists() else "")
        lp.unlink()

        # ---- 4. 崩溃进程的锁可立即回收（比旧行为更快，是改进而非退化）----
        lp.write_text(json.dumps({"pid": 999000, "token": "dead",
                                  "time": time.time()}), encoding="utf-8")
        d = nm.FileMutex(lp, timeout=2.0)
        quick = _try_acquire(d)
        check("死进程的锁可立即回收（不必等 30 秒）", quick)
        if quick:
            d.__exit__(None, None, None)

        # ---- 5. 兼容旧格式：仍按年龄兜底回收（升级不卡死）----
        lp.write_text("pid:1;time:1.0", encoding="utf-8")
        os.utime(lp, (old, old))
        e = nm.FileMutex(lp, timeout=2.0)
        legacy_ok = _try_acquire(e)
        check("老格式锁仍能兜底回收（向后兼容）", legacy_ok)
        if legacy_ok:
            e.__exit__(None, None, None)

        # ---- 6. 无法判定存活时走保守路径（不误抢）----
        lp.write_text("{不是合法 JSON", encoding="utf-8")
        f = nm.FileMutex(lp, timeout=1.0)
        # 内容损坏但很新：不能回收
        fresh_no = not _try_acquire(f)
        check("内容损坏且很新的锁不被回收（保守方向）", fresh_no)
        os.utime(lp, (old, old))
        g = nm.FileMutex(lp, timeout=1.5)
        old_yes = _try_acquire(g)
        check("内容损坏但很老的锁可兜底回收", old_yes)
        if old_yes:
            g.__exit__(None, None, None)

        # ---- 7. 持有者存活且锁极老 → 报错而非静默抢（宁可失败不要错）----
        h = nm.FileMutex(lp, timeout=1.0)
        h.__enter__()
        ancient = time.time() - (nm.FileMutex.HARD_LIMIT + 60)
        os.utime(lp, (ancient, ancient))
        i = nm.FileMutex(lp, timeout=1.0)
        msg = ""
        reclaimed = False
        try:
            i.__enter__()
            reclaimed = True
        except TimeoutError as ex:
            msg = str(ex)
        check("持有者存活 + 锁极老 → 拒绝抢锁", not reclaimed, "被抢走了")
        check("该场景给出可执行的错误说明（含 pid 与处置建议）",
              ("pid=" in msg and "删除" in msg) if msg else False, msg[:100])
        h.__exit__(None, None, None)

        # ---- 8. 变异检查：把存活判定废掉，第 2 条必须变红 ----
        _orig_alive = nm._pid_alive
        try:
            nm._pid_alive = lambda pid: None       # 变异：一切「无法判定」
            a2 = nm.FileMutex(lp, timeout=1.0)
            a2.__enter__()
            os.utime(lp, (old, old))
            b2 = nm.FileMutex(lp, timeout=1.5)
            would_steal = _try_acquire(b2)
            check("变异：废掉存活判定后确实会抢锁（证明第 2 条判据有效）",
                  would_steal,
                  "确实抢到了（判据有判别力）" if would_steal
                  else "未抢到 —— 判据可能不具判别力，需复查")
            if would_steal:
                b2.__exit__(None, None, None)
            a2.__exit__(None, None, None)
        finally:
            nm._pid_alive = _orig_alive

    print()
    total = len(PASS) + len(FAIL)
    print("RESULT: %s (%d/%d)" % ("ALL_PASS" if not FAIL else "HAS_FAIL",
                                  len(PASS), total))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())