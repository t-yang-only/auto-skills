#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_test_hk_link_live.py —— hk_link_live 的纯本地自检（mock pm2 与 gateway）。

不真连任何远端：把 check_local_pm2 与 check_gateway_node 的返回值 mock 掉，
测通 4 种组合：
  · 两端 OK → OVERALL OK
  · pm2 FAIL → OVERALL FAIL
  · gateway FAIL → OVERALL FAIL
  · 两端都 FAIL → OVERALL FAIL

也覆盖一个真用场景：调用 hk_link_live.py --push-serverchan 后，hk_run 被
调了一次（用 mock），保证告警路径不抛异常。
"""
import importlib.util
import json
import pathlib
import sys

LINK = pathlib.Path(__file__).with_name("hk_link_live.py")
CHANNEL = pathlib.Path(__file__).with_name("hk_channel.py")

FAIL = []
TOTAL = []


def check(name, cond, detail=""):
    TOTAL.append(bool(cond))
    if cond:
        print("  [PASS] %s" % name)
    else:
        FAIL.append(name)
        print("  [FAIL] %s\n        %s" % (name, str(detail)[:600]))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_main(args, local_ok, gw_ok, local_detail="", gw_detail="", run_called=False):
    import sys as _sys
    # 让"hk_channel"作为模块名注册到 sys.modules（脚本 main 里 `from hk_channel import hk_run` 用）
    if "hk_channel" not in _sys.modules:
        ch = _load("hk_channel", CHANNEL)
        _sys.modules["hk_channel"] = ch
    ch = _sys.modules["hk_channel"]
    link = _load("hk_link_live", LINK)
    # 注意：link 模块自己 `from hk_channel import hk_run` 已在加载时绑定。
    # 它下面再 import 时拿到的是 sys.modules['hk_channel']——正是 ch。
    # 因此只要 ch.hk_run 被改写，main() 里调的就是 fake_run。
    orig_local = link.check_local_pm2
    orig_gw = link.check_gateway_node
    orig_run = ch.hk_run
    link.check_local_pm2 = lambda: (local_ok, local_detail or ("ok" if local_ok else "down"))
    link.check_gateway_node = lambda: (gw_ok, gw_detail or ("online" if gw_ok else "offline"))
    called = {"n": 0}
    def fake_run(*a, **k):
        called["n"] += 1
        return 0, "PUSHED\n"
    ch.hk_run = fake_run
    import io, contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = link.main(args)
    finally:
        link.check_local_pm2 = orig_local
        link.check_gateway_node = orig_gw
        ch.hk_run = orig_run
    return rc, buf.getvalue(), called["n"]


def main():
    # T1 两端 OK
    rc, out, n = run_main([], local_ok=True, gw_ok=True)
    check("T1 两端 OK → OVERALL OK rc=0", rc == 0 and "OVERALL: OK" in out and n == 0, out)
    # T2 pm2 FAIL
    rc, out, n = run_main([], local_ok=False, gw_ok=True, local_detail="pm2 down")
    check("T2 pm2 FAIL → OVERALL FAIL", rc == 1 and "OVERALL: FAIL" in out, out)
    # T3 gateway FAIL
    rc, out, n = run_main([], local_ok=True, gw_ok=False, gw_detail="节点不在")
    check("T3 gateway FAIL → OVERALL FAIL", rc == 1 and "OVERALL: FAIL" in out, out)
    # T4 两端 FAIL + --push-serverchan（harness：不应抛）
    rc, out, n = run_main(["--push-serverchan"], local_ok=False, gw_ok=False)
    check("T4 两端 FAIL + --push-serverchan → rc=1 且尝试推送",
          rc == 1 and n >= 1 and "PUSHED" in out, out)

    # T5 parse_health：真实形态（hk_run 前缀 + 多行缩进 JSON）必须解得出
    # ——这条是补的：前四条测试把 check_gateway_node 整个 mock 掉了，
    # 真实跑时才发现「只取最后一个 { 行」解析不了多行 JSON。
    # 节点名用占位符：测试fixture 不该包含真实主机名（本仓库会公开）。
    mod5 = _load("hk_link_live", LINK)
    real_out = ("[host/direct]\n"
                "{\n"
                '  "ok": true,\n'
                '  "nodes": [\n'
                '    "node-alpha",\n'
                '    "node-beta"\n'
                "  ],\n"
                '  "watchers": 0\n'
                "}\n")
    d = mod5.parse_health(real_out)
    check("T5 parse_health 解多行 JSON（含 [host/mode] 前缀）",
          isinstance(d, dict) and d.get("nodes") == ["node-alpha", "node-beta"], d)
    check("T5b parse_health 对非 JSON 返回 None",
          mod5.parse_health("[host/direct]\ncurl: not found\n") is None, "应为 None")

    print("\n%s" % (("PASS %d/%d" % (len(TOTAL) - len(FAIL), len(TOTAL))) if not FAIL
                     else "FAILED: " + ", ".join(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())