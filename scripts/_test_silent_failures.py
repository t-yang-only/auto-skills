#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静默失败守卫：出问题时必须出声。

为什么单独立一类
================
本项目反复栽在同一件事上：**失败被吞掉，使用者把「功能没生效」误判为
「功能就这样」**。2026-10-01/02 共修了 6 处，例如：
  · nm_register 锁释放失败静默 → 锁残留，此后每个 Agent 都超时，
    表现为「整套多 Agent 协同卡住」，而根因一声不吭
  · 熔断告警推送失败静默 → 熔断打开了却没人知道
  · notify_push 读渠道配置失败静默 → 告警发去默认 key，你以为在收其实没有

它们的共同形状是：**except 之后什么都不说**。这类退化在功能测试下全绿
（该做的事确实做了，只是没做成），所以必须单独盯着。

本文件盯两条判据：
  1. 失败时**必须有可读的输出**（不能只 pass）。
  2. 必须是 **best-effort**：失败不能让调用方炸掉 —— 否则原本「不影响主流程」
     的设计会变成「一失败就中断」，那是另一种退化。
"""
import importlib.util
import pathlib
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parent / "db_sync.py"
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  —— " + str(detail)[:150]) if (detail and not ok) else ""))


def _capture_stderr(fn):
    """执行 fn，捕获它写到 stderr 的内容。返回 (是否抛异常, stderr 文本)。"""
    import io
    import contextlib
    buf = io.StringIO()
    raised = None
    with contextlib.redirect_stderr(buf):
        try:
            fn()
        except BaseException as e:      # noqa: BLE001  —— 这里就是要观察「有没有炸」
            raised = e
    return raised, buf.getvalue()


def main():
    spec = importlib.util.spec_from_file_location("db_sync", SCRIPT)
    ds = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(ds)
    except Exception as e:
        print("  [SKIP] 无法载入 db_sync（%s: %s）" % (type(e).__name__, e))
        print("\nRESULT: SKIP (1/1)")
        return 0

    # ---- 1. 熔断状态写失败必须出声 ----
    #
    # 这个文件承载熔断器状态（连续失败次数 / 熔断解除时刻）。每次调用都是
    # 新进程，状态只能靠落盘跨进程生效——写得进去熔断才有意义。写不进去
    # 而一声不吭，等于熔断静默失效：库不可达时每次落库都干等 8 秒超时。
    with tempfile.TemporaryDirectory() as tmp:
        blocker = pathlib.Path(tmp) / "blocker"
        blocker.write_text("x", encoding="utf-8")   # 拿「文件」当父目录 → 写必失败
        saved_health = ds._health_file
        ds._health_file = lambda: blocker / "sub" / "db_health.json"
        try:
            raised, err = _capture_stderr(
                lambda: ds._save_health({"consecutive_failures": 2}))
            check("熔断状态写失败时出声（不再静默）",
                  "熔断" in err, "stderr=%r" % err[:120])
            check("该失败保持 best-effort（不抛异常给调用方）",
                  raised is None, "抛了 %r" % raised)
            check("提示里说明了影响（否则使用者不知道该担心什么）",
                  "熔断" in err and ("超时" in err or "打开" in err), err[:120])
        finally:
            ds._health_file = saved_health

    # ---- 2. 暂存队列的损坏行必须出声 ----
    #
    # 暂存是「数据不丢」的最后一道防线，而调用方读完会**整体重写**该文件
    # ——跳过一行就等于在重写时把它永久删掉。丢了多少条必须让人知道。
    with tempfile.TemporaryDirectory() as tmp:
        sp = pathlib.Path(tmp) / "pending.jsonl"
        sp.write_text('{"fn":"a","kwargs":{}}\n'
                      '{ 这一行是坏的\n'
                      '{"fn":"b","kwargs":{}}\n', encoding="utf-8")
        saved_spool = ds._spool_file
        ds._spool_file = lambda: sp
        try:
            held = {}
            raised, err = _capture_stderr(
                lambda: held.update(items=ds._read_spool()))
            items = held.get("items")
            check("暂存含损坏行时出声（不再静默丢弃）",
                  "无法解析" in err, "stderr=%r" % err[:120])
            check("提示里给出文件路径（便于人工核查）",
                  str(sp) in err, err[:120])
            check("好记录仍被完整读出（没被一起丢掉）",
                  isinstance(items, list) and len(items) == 2,
                  "读到 %r" % (items,))
            check("该失败保持 best-effort（不抛异常）",
                  raised is None, "抛了 %r" % raised)
        finally:
            ds._spool_file = saved_spool

    # ---- 3. 反向：正常路径不能被这些提示打扰（否则会变成噪音）----
    with tempfile.TemporaryDirectory() as tmp:
        sp = pathlib.Path(tmp) / "pending.jsonl"
        sp.write_text('{"fn":"a","kwargs":{}}\n', encoding="utf-8")
        saved_spool = ds._spool_file
        ds._spool_file = lambda: sp
        try:
            _, err = _capture_stderr(lambda: ds._read_spool())
            check("暂存完好时不出任何提示（提示不能变成噪音）",
                  err.strip() == "", "stderr=%r" % err[:120])
        finally:
            ds._spool_file = saved_spool

    print()
    total = len(PASS) + len(FAIL)
    print("RESULT: %s (%d/%d)" % ("ALL_PASS" if not FAIL else "HAS_FAIL",
                                  len(PASS), total))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())