#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto-skills · 意见请求客户端（Agent 专用）

Agent 遇到必须由人拍板的岔路时用这个提问；人答复后可通过 check 取回结论。

身份自动采集（这是硬要求——Hermes 靠它找回提问者）：
    harness / session / project 三项必须齐全，能自动探测就自动探测，
    探测不到就必须由调用方显式传入，绝不允许留空。

用法：
    python scripts/opinion_request.py whoami
    python scripts/opinion_request.py ask --title "..." --question "..." \
        --option "A:说明" --option "B:说明" [--context "..."] [--urgency high] \
        [--harness codex] [--session xxx] [--project D:\\foo]
    python scripts/opinion_request.py list [--all]
    python scripts/opinion_request.py check OR-20260919-001

铁律：写入知识库的任何文字都带 [HARNESS ...] 身份行；不带前缀的即「人」说的。
"""
import argparse, json, os, sys, urllib.request, urllib.error, uuid

# Windows 控制台默认 cp936，不强制 UTF-8 的话中文输出会变乱码
for _s in ('stdout', 'stderr'):
    try:
        getattr(sys, _s).reconfigure(encoding='utf-8')
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _parse_gateway_block(path: str) -> dict:
    """行级解析某个 config.yaml 的 agent_gateway 段（仅作降级兜底用）。"""
    out = {}
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return out
    in_gw = False
    for line in open(p, encoding="utf-8"):
        if line.strip().startswith("agent_gateway:"):
            in_gw = True
            continue
        if not in_gw:
            continue
        if line and not line[0].isspace():
            break
        s = line.strip()
        if ":" not in s:
            continue
        k, v = s.split(":", 1)
        out[k.strip()] = v.strip()
    return out


def load_cfg():
    """读取 Agent 网关配置（**分层**：基础层 + `.evolution` 覆盖层）。

    ⚠️ 这里原本是**自己的行解析器，只读 `config/config.yaml`**，完全不看
    `.evolution/config.yaml`。后果：把 `agent_gateway` 写进覆盖层
    （也就是这个 skill 推荐的"真实值只放覆盖层"做法）**根本不生效** ——
    实测踩到：把 `token_file` 改到私有层后，本函数仍去
    `config/gateway.token` 找令牌，报「未找到令牌」。

    这正是本项目反复要杜绝的「配置里写了但没人读」，也是「同一个配置
    两个读取方各读一层」的典型：`db_sync` 走 config_manager（读两层），
    本文件走行解析（只读一层），于是同一份配置对两个模块含义不同。

    现在统一走 config_manager；导入不到时退回行解析器，保证单文件
    拷贝出去仍能独立运行。
    """
    cfg = {"url": "https://agent.example.com",
           "token_file": ".evolution/secrets/gateway.token",
           "timeout_seconds": 30}
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import config_manager
        gw = dict(config_manager.get_value("agent_gateway", {}) or {})
    except Exception as e:
        print("[!] 读取分层配置失败，退回只读基础层：（%s: %s）"
              % (type(e).__name__, e), file=sys.stderr)
        gw = _parse_gateway_block(os.path.join("config", "config.yaml"))

    for k, v in gw.items():
        if v in (None, ""):
            continue          # 空值不覆盖默认，避免"配了空"把可用的默认打掉
        if k == "timeout_seconds":
            try:
                cfg[k] = int(v)
            except (TypeError, ValueError):
                print("[!] agent_gateway.timeout_seconds 不是整数，按默认 %d 处理"
                      % cfg["timeout_seconds"], file=sys.stderr)
        else:
            cfg[k] = str(v)

    tk = os.path.join(ROOT, cfg["token_file"])
    cfg["token"] = open(tk, encoding="utf-8").read().strip() if os.path.exists(tk) else ""
    # 真实网关地址放在私有层（.evolution/secrets/），不在公开库里 ——
    # 让 config/config.yaml 能保持可公开的占位符（该 skill 会推 GitHub）。
    # 按「新位置 → 旧位置」顺序找：老安装把凭据留在 config/ 下，
    # 升级后必须仍然能用，否则会静默变成"地址没配"。
    for _rel in (os.path.join(".evolution", "secrets", "gateway.url"),
                 os.path.join("config", "gateway.url")):
        try:
            _gu = os.path.join(ROOT, _rel)
            if os.path.isfile(_gu):
                _v = open(_gu, encoding="utf-8").read().strip()
                if _v:
                    cfg["url"] = _v
                    break
        except Exception:
            continue

    return cfg


def detect_identity(args):
    """harness / session / project 三项，能探测就探测，探测不到且未显式给出则报错。"""
    env = os.environ
    harness = args.harness or env.get("AGW_HARNESS") or env.get("AUTO_SKILLS_HARNESS")
    if not harness:
        for var, name in (("CLAUDECODE", "claude-code"), ("CLAUDE_CODE_ENTRYPOINT", "claude-code"),
                          ("CODEX_SANDBOX", "codex"), ("CODEX_HOME", "codex"),
                          ("CURSOR_TRACE_ID", "cursor"), ("GEMINI_CLI", "gemini"),
                          ("PI_SESSION", "pi"), ("GROK_SESSION", "grok"),
                          ("DSH_SESSION_ID", "dsh"), ("HERMES_HOME", "hermes")):
            if env.get(var):
                harness = name
                break
    session = (args.session or env.get("AGW_SESSION") or env.get("DSH_SESSION_ID")
               or env.get("CLAUDE_SESSION_ID") or env.get("CODEX_SESSION_ID")
               or env.get("CURSOR_TRACE_ID") or env.get("GEMINI_SESSION_ID"))
    project = args.project or env.get("AGW_PROJECT") or os.getcwd()
    missing = [k for k, v in (("harness", harness), ("session", session), ("project", project)) if not v]
    if missing:
        sys.exit("[opinion_request] 缺少身份项：%s\n"
                 "  必须显式传入，例如：--harness codex --session <你的会话ID> --project D:\\foo\n"
                 "  这是硬要求：Hermes 靠这三项找回提问者。" % ", ".join(missing))
    if not session:
        session = "auto-" + uuid.uuid4().hex[:12]
    return harness, session, project


def api(cfg, method, path, payload=None):
    url = cfg["url"].rstrip("/") + path
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + cfg["token"])
    if data:
        req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, timeout=cfg.get("timeout_seconds", 30)) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        sys.exit("[opinion_request] HTTP %s: %s" % (e.code, body))
    except Exception as e:
        sys.exit("[opinion_request] 请求失败: %s" % e)


def cmd_whoami(cfg, a):
    h, s, p = detect_identity(a)
    print(json.dumps({"harness": h, "session": s, "project": p,
                      "gateway": cfg["url"], "token_loaded": bool(cfg["token"])},
                     ensure_ascii=False, indent=2))


def cmd_ask(cfg, a):
    h, s, p = detect_identity(a)
    opts = []
    for o in a.option:
        if ":" in o:
            lbl, desc = o.split(":", 1)
            opts.append({"label": lbl.strip(), "desc": desc.strip()})
        else:
            opts.append({"label": o.strip(), "desc": ""})
    if len(opts) < 2:
        sys.exit("[opinion_request] 至少给 2 个选项（--option \"A:说明\"）")
    res = api(cfg, "POST", "/opinions", {
        "title": a.title, "question": a.question, "context": a.context or a.question,
        "options": opts, "harness": h, "session": s, "project": p,
        "urgency": a.urgency or cfg.get("default_urgency", "normal"),
        "node": os.environ.get("AGW_NAME", "-")
    })
    print("已提问：%s" % res.get("id"))
    print("  单子：%s" % res.get("file"))
    print("  身份：%s | %s | %s" % (h, s, p))
    print("  人来答后，用 `opinion_request.py check %s` 取回结论。" % res.get("id"))


def cmd_list(cfg, a):
    d = api(cfg, "GET", "/opinions")
    for key, label in (("pending", "待回答"), ("answered", "已回答")):
        items = d.get(key) or []
        print("%s（%d）：" % (label, len(items)))
        for it in items:
            if not a.all and key == "answered" and it.get("status") == "已消费":
                continue
            mark = ("已选: " + ",".join(it["chosen"])) if it.get("chosen") else ""
            print("  %s  %s  [%s]  %s" % (it["id"], it.get("harness", "?"), it.get("status", "?"), mark))


def cmd_check(cfg, a):
    d = api(cfg, "GET", "/opinions")
    for it in (d.get("answered") or []) + (d.get("pending") or []):
        if it["id"] == a.id:
            print(json.dumps(it, ensure_ascii=False, indent=2))
            return
    sys.exit("[opinion_request] 没找到 %s" % a.id)


def main():
    ap = argparse.ArgumentParser(description="auto-skills 意见请求客户端")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("whoami", "ask", "list", "check"):
        p = sub.add_parser(name)
        p.add_argument("--harness"); p.add_argument("--session"); p.add_argument("--project")
        if name == "ask":
            p.add_argument("--title", required=True); p.add_argument("--question", required=True)
            p.add_argument("--option", action="append", default=[])
            p.add_argument("--context"); p.add_argument("--urgency", choices=["low", "normal", "high"])
        if name == "list":
            p.add_argument("--all", action="store_true")
        if name == "check":
            p.add_argument("id")
    a = ap.parse_args()
    cfg = load_cfg()
    if not cfg["token"]:
        sys.exit("[opinion_request] 未找到令牌：%s" % os.path.join(ROOT, cfg["token_file"]))
    {"whoami": cmd_whoami, "ask": cmd_ask, "list": cmd_list, "check": cmd_check}[a.cmd](cfg, a)


if __name__ == "__main__":
    main()