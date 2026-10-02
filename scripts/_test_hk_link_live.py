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


def run_main(args, local_state="online", gw_state="ok",
             local_detail="", gw_detail="", run_called=False):
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
    link.check_local_pm2 = lambda: (local_state, local_detail or local_state)
    link.check_gateway_node = lambda: (gw_state, gw_detail or gw_state)
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
    rc, out, n = run_main([], local_state="online", gw_state="ok")
    check("T1 两端 OK → OVERALL OK rc=0", rc == 0 and "OVERALL: OK" in out and n == 0, out)
    # T2 pm2 **明确**回答不在线
    rc, out, n = run_main([], local_state="offline", gw_state="ok",
                          local_detail="pm2 status=stopped")
    check("T2 pm2 明确 offline → OVERALL FAIL", rc == 1 and "OVERALL: FAIL" in out, out)
    # T3 gateway **明确**失败
    rc, out, n = run_main([], local_state="online", gw_state="fail", gw_detail="节点不在")
    check("T3 gateway 明确 fail → OVERALL FAIL", rc == 1 and "OVERALL: FAIL" in out, out)
    # T4 两端 FAIL + --push-serverchan（harness：不应抛）
    rc, out, n = run_main(["--push-serverchan"], local_state="offline", gw_state="fail")
    check("T4 两端 FAIL + --push-serverchan → rc=1 且尝试推送",
          rc == 1 and n >= 1 and "PUSHED" in out, out)

    # ── T5/T6：三态语义（2026-10-02 新增）──
    # 这两条守的是本次修复的核心：**「问不到」不等于「坏了」**。
    # 旧版把 LOCAL_PM2 做成布尔，从受限 shell 调 pm2 报 EPERM 时会误报 FAIL；
    # 而没配主机别名时 GATEWAY_NODE 也会误报 FAIL —— 本脚本的职责正是在
    # 失联时推送告警，于是会推出**假告警**。实测踩过。
    rc, out, n = run_main([], local_state="unknown", gw_state="ok")
    check("T5 pm2 问不到(unknown) + gateway OK → OVERALL OK（旧版会误报 FAIL）",
          rc == 0 and "OVERALL: OK" in out and "UNKNOWN" in out, out)

    rc, out, n = run_main([], local_state="unknown", gw_state="unknown")
    check("T6 两项都 unknown → OVERALL UNKNOWN 且 rc=0（不误报、不假推送）",
          rc == 0 and "OVERALL: UNKNOWN" in out and n == 0, out)

    # T7 --help 必须短路：不跑检查、不推送（探索不该有副作用）
    rc, out, n = run_main(["--help"], local_state="offline", gw_state="fail")
    check("T7 --help 短路 → rc=0 且没有跑检查/没推送",
          rc == 0 and n == 0 and "OVERALL" not in out and "用法" in out, out)

    # ── T8：别名守卫（2026-10-02 新增）──
    # check_gateway_node 的「未配置」分支必须看 hk_channel 的**解析结果**，
    # 不能只看环境变量 —— 否则把别名配在私有层（hk_channel.direct_host）
    # 也会被判成"没配"，而通道其实完全可用。实测踩过。
    mod8 = _load("hk_link_live", LINK)
    ch8 = _load("hk_channel", CHANNEL)
    # ⚠️ 必须把 ch8 注册进 sys.modules：`check_gateway_node` 里是
    # `import hk_channel as mod`，取的是 sys.modules 里那个实例。
    # 不注册的话，patch 的是另一个副本 → 它照跑**真实探测**（实测踩过：
    # 断言里出现真实节点名，说明根本没走 mock）。
    import sys as _sys8
    _prev_mod = _sys8.modules.get("hk_channel")
    _sys8.modules["hk_channel"] = ch8
    import os as _os
    _sd, _sj = ch8.DIRECT_HOST, ch8.JUMP_HOST
    _se = {k: _os.environ.pop(k, None) for k in ("HK_DIRECT_HOST", "HK_JUMP_HOST")}
    _sr = (ch8.pick_host, ch8.hk_run)
    try:
        # 重定向到隔离副本，避免真去解析本机的 SSH 配置
        _fake_health = ('{"ok": true, "nodes": ["node-alpha", "node-beta"]}')

        def _fake_run(_cmd):
            return 0, _fake_health

        ch8.pick_host = lambda: ("fake-alias", "direct")
        ch8.hk_run = _fake_run

        # ① 两个别名都是占位符 → 必须报 unknown（不能误判为链路故障）
        ch8.DIRECT_HOST, ch8.JUMP_HOST = "remote-host", "remote-via-jump"
        _st, _d = mod8.check_gateway_node()
        check("T8 别名为占位符 → unknown（不误判成链路故障）",
              _st == "unknown", "%s / %s" % (_st, _d))

        # ② 别名来自配置（非占位符）→ 不能短路成 unknown，要真的去判
        ch8.DIRECT_HOST, ch8.JUMP_HOST = "configured-alias", "remote-via-jump"
        _st2, _d2 = mod8.check_gateway_node()
        check("T8b 别名来自配置 → 不再短路成 unknown（真去判定）",
              _st2 != "unknown", "%s / %s" % (_st2, _d2))
    finally:
        ch8.pick_host, ch8.hk_run = _sr
        ch8.DIRECT_HOST, ch8.JUMP_HOST = _sd, _sj
        for _k, _v in _se.items():
            if _v is not None:
                _os.environ[_k] = _v
        if _prev_mod is None:
            _sys8.modules.pop("hk_channel", None)
        else:
            _sys8.modules["hk_channel"] = _prev_mod

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