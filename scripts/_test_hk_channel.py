#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_test_hk_channel.py —— hk_channel.py 回归测试（monkeypatch subprocess，纯纯本地）。

无需假 sh 脚本（Windows 下 sh 不可执行），直接 mock hk_channel 内部的 _run()
与 probe()，测通所有逻辑分支。
"""
import json
import os
import pathlib
import sys
import tempfile

import hk_channel as mod

FAIL = []
TOTAL = []


def check(name, cond, detail=""):
    TOTAL.append(bool(cond))
    if cond:
        print("  [PASS] %s" % name)
    else:
        FAIL.append(name)
        print("  [FAIL] %s\n        %s" % (name, str(detail)[:600]))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        state = pathlib.Path(tmp) / "state.json"
        orig_state_file = mod.STATE_FILE
        orig_probe = mod.probe
        orig_run = mod._run
        mod.STATE_FILE = state

        try:
            # T1 直连通 → 选直连（快路径）
            mod.probe = lambda h: h == mod.DIRECT_HOST
            if "HK_FORCE" in os.environ:
                del os.environ["HK_FORCE"]
            host, how = mod.pick_host()
            check("T1 直连通 → 选直连", host == mod.DIRECT_HOST and how == "direct",
                  (host, how))

            # T2 直连失败、跳板通 → 切跳板
            mod.probe = lambda h: h == mod.JUMP_HOST
            host, how = mod.pick_host()
            check("T2 直连挂跳板通 → 切跳板", host == mod.JUMP_HOST and how == "jump",
                  (host, how))

            # T3 都挂 → 抛 RuntimeError（绝不静默选不可达通道）
            mod.probe = lambda h: False
            err = None
            try:
                mod.pick_host()
            except RuntimeError as e:
                err = str(e)
            check("T3 都挂 → 抛 RuntimeError", err is not None and "直连" in err, err)

            # T4 HK_FORCE=direct 但直连挂 → 抛错（即便跳板通）
            os.environ["HK_FORCE"] = "direct"
            mod.probe = lambda h: h == mod.JUMP_HOST
            err = None
            try:
                mod.pick_host()
            except RuntimeError as e:
                err = str(e)
            check("T4 HK_FORCE=direct + 直连挂 → 抛错",
                  err is not None and "HK_FORCE" in err, err)

            # T5 HK_FORCE=jump 且跳板通 → 选跳板
            os.environ["HK_FORCE"] = "jump"
            mod.probe = lambda h: h == mod.JUMP_HOST
            host, how = mod.pick_host()
            check("T5 HK_FORCE=jump + 跳板通 → 选跳板",
                  host == mod.JUMP_HOST and how == "jump", (host, how))
            del os.environ["HK_FORCE"]

            # T6 缓存：直连失败被记下，缓存命中走跳板
            # 状态重置：模拟直连挂、跳板通
            if state.is_file():
                state.unlink()
            mod.probe = lambda h: h == mod.JUMP_HOST
            mod.pick_host()
            st = json.loads(state.read_text(encoding="utf-8"))
            check("T6 缓存记录：direct_fails >= 1 且 last_ok=JUMP",
                  int(st.get("direct_fails", 0)) >= 1 and st.get("last_ok") == mod.JUMP_HOST,
                  st)

            # T7 hk_run 输出前缀
            mod.probe = lambda h: h == mod.DIRECT_HOST
            mod._run = lambda args, timeout: (0, "MOCK_OUT\n")
            rc, out = mod.hk_run("echo test")
            check("T7 hk_run 输出含前缀 [host/direct]",
                  rc == 0 and "[%s/direct]" % mod.DIRECT_HOST in out and "MOCK_OUT" in out,
                  out)

            # T8 hk_scp push / pull 的参数格式
            calls = []
            mod._run = lambda args, timeout: (calls.append(args), (0, "SCP_OK\n"))[1]
            mod.hk_scp("local.txt", "/remote/txt")
            check("T8a hk_scp push: src 是本地 dst 带 host:",
                  len(calls) == 1 and "%s:/remote/txt" % mod.DIRECT_HOST in calls[0],
                  calls)
            calls.clear()
            mod.hk_scp("/remote/txt", "local.txt", pull=True)
            check("T8b hk_scp pull: src 带 host: dst 是本地",
                  len(calls) == 1 and "%s:/remote/txt" % mod.DIRECT_HOST in calls[0],
                  calls)

        finally:
            mod.STATE_FILE = orig_state_file
            mod.probe = orig_probe
            mod._run = orig_run
            if "HK_FORCE" in os.environ:
                del os.environ["HK_FORCE"]

    print("\n%s" % (("PASS %d/%d" % (len(TOTAL) - len(FAIL), len(TOTAL))) if not FAIL
                     else "FAILED: " + ", ".join(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
