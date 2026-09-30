#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hk_link_live.py —— 端到端自检：Hermes → agent-gateway → 本地节点链路是否通。

设计动机：2026-09-24 实测发现「Hermes 处理完意见请求 → 本地会话唤醒」这条链路
静默失联了 5 天（最近一次成功的 wake 是 2026-09-19，最近 5 天全部 wake.failed），
没有任何守卫生效——agent-gateway 把 failed 写在 events.jsonl，没有人来读。
根因是本地节点进程配置里写死了已停用的代理（AGW_PROXY），而用户 2026-09-23
已禁用该代理，节点 WS 重连被 ECONNREFUSED 反复打断。

最小可行检测（两层）：
  ① 本机端节点进程是否活（pm2 status）
  ② 远端 agent-gateway 在线节点清单里是否有本机节点名

用法：
  python hk_link_live.py                # 静态检测（两个条件都满足才 OK）
  python hk_link_live.py --push-serverchan  # 不通过时主动推 ServerChan
"""
import json
import os
import pathlib
import subprocess
import sys

LOCAL_NODE_NAME = os.environ.get("HK_LINK_NODE_NAME", "win-t-yang")
LOCAL_PM2_APP = os.environ.get("HK_LINK_PM2_APP", "agent-node-win")
GATEWAY_HEALTH = os.environ.get(
    "HK_LINK_GATEWAY_HEALTH_CURL", "curl -s http://127.0.0.1:18800/health")


def _pm2_list_json(pm2_bin):
    """兼容多种 pm2 调用：jlist / list / list --json。"""
    candidates = [[pm2_bin, "jlist"], [pm2_bin, "list"], [pm2_bin, "list", "--json"]]
    last = None
    for args in candidates:
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=10,
                               encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired) as e:
            last = "exec " + " ".join(args) + ": " + str(e)
            continue
        out = (r.stdout or "").strip()
        if r.returncode == 0 and out.startswith("["):
            try:
                return json.loads(out)
            except ValueError:
                last = "parse: " + out[:200]
        else:
            last = "rc=" + str(r.returncode) + ": " + (r.stderr or r.stdout)[:200]
    raise RuntimeError(last or "pm2 jlist/list 全失败")


def check_local_pm2():
    pm2_cmds = ["pm2",
                os.path.expandvars(r"%AppData%\npm\pm2.cmd"),
                os.path.expanduser("~/AppData/Roaming/npm/pm2.cmd")]
    last_err = None
    for pm2 in pm2_cmds:
        try:
            arr = _pm2_list_json(pm2)
        except FileNotFoundError as e:
            last_err = str(e)
            continue
        except Exception as e:
            last_err = str(e)
            continue
        for p in arr:
            if p.get("name") != LOCAL_PM2_APP:
                continue
            status = p.get("pm2_env", {}).get("status")
            return status == "online", "pm2 status=" + str(status)
        return False, "未找到 " + LOCAL_PM2_APP + " 进程"
    return False, "找不到 pm2: " + str(last_err)


def parse_health(out):
    """从 hk_run 的输出里解出 health JSON。

    hk_run 会带一行 `[host/mode]` 前缀，而 health 的 JSON 是**多行缩进**的——
    不能只取「最后一个以 { 开头的行」（那会取到 JSON 内部的某一行，parse 失败）。
    正确做法：跳过前缀，从第一个以 `{` 开头的行开始拼到结尾。
    """
    lines = out.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("{"):
            start = i
            break
    if start is None:
        return None
    try:
        return json.loads("\n".join(lines[start:]))
    except ValueError:
        return None


def check_gateway_node():
    """通过自愈通道读 agent-gateway 健康端点，看 nodes 里有没有目标节点。"""
    import hk_channel as mod
    host, _ = mod.pick_host()
    rc, out = mod.hk_run(GATEWAY_HEALTH)
    if rc != 0:
        return False, "health 端点 rc=" + str(rc) + ": " + out[:200]
    d = parse_health(out)
    if d is None:
        return False, "health 解析失败：" + out[:200]
    nodes = d.get("nodes") or []
    if LOCAL_NODE_NAME not in nodes:
        return False, "节点清单=" + str(nodes) + "（缺少 " + LOCAL_NODE_NAME + "）"
    return True, "在线节点=" + str(nodes)


def main(argv):
    push = "--push-serverchan" in argv
    local_ok, local_detail = check_local_pm2()
    try:
        gw_ok, gw_detail = check_gateway_node()
    except Exception as e:
        gw_ok, gw_detail = False, f"远端探测失败：{e}"

    print("LOCAL_PM2:", "OK" if local_ok else "FAIL", local_detail)
    print("GATEWAY_NODE:", "OK" if gw_ok else "FAIL", gw_detail)
    overall = local_ok and gw_ok
    print("OVERALL:", "OK" if overall else "FAIL")
    if not overall and push:
        try:
            from hk_channel import hk_run
            # 告警标题里的链路名从环境变量来，不写死真实主机名——
            # 本脚本随仓库公开，标题会原样出现在使用者的微信/Server酱 里。
            link_label = os.environ.get("HK_LINK_LABEL", "远端主机")
            msg = "HK link 链路失联。L=" + local_detail + ", GW=" + gw_detail
            rc, outp = hk_run(
                "bash /usr/local/bin/serverchan-push.sh "
                "'⚠️ 本机↔" + link_label + " 链路失联' '" + msg[:300] + "'")
            # 推送结果必须回显：静默的告警通路等于没有告警通路（这个脚本
            # 本身就是为"链路静默失联 5 天没人发现"写的，不能重犯）。
            print("PUSH:", "OK" if rc == 0 else "FAIL", outp.strip()[:200])
        except Exception as e:
            print("PUSH_ERR:", e)
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))