#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hk_channel.py —— 到远端主机的自愈通道（直连 ↔ 国内跳板自动切换）。

要解决的问题：远端主机在境外时，本机「没有外网」的时段里直连必然失败；
而国内跳板机在本机断外网时仍可达，且跳板自己有外网、可以转到远端主机。
于是需要一条**不依赖本机外网**的备用路径。

所以策略是「直连优先、跳板兜底」：直连探测通过就走直连（快数倍）；直连失败
（断外网 / 境外链路抖动）自动改走跳板。两个通道的可达性结论都缓存下来，
避免每次调用都付一遍探测成本。

设计要点（与具体是哪两台机器无关）：
  · 主机名一律从环境变量来，**脚本内不写死任何真实主机**——真实值放
    `.evolution/config.yaml`（已被 .gitignore）或部署时的环境变量。
    这样本脚本可以随仓库公开，不泄露使用者的基础设施信息。
  · 跳板别名（形如 remote-via-jump）必须先写进 ~/.ssh/config
    （HostName + ProxyJump + IdentityFile）。脚本不负责写它——ssh 配置属于
    机器状态，由会话或安装脚本管理，这里只消费。
  · 两条路都探测不通时**抛异常**，而不是静默选一个连不上的通道
    （静默失败是这个仓库踩过的坑）。

用法（其他脚本 / 命令行）：
  python hk_channel.py --probe              # 打印当前选中的通道与延迟
  python hk_channel.py run "uname -r"       # 在远端主机上执行一条命令
  python hk_channel.py scp 本机路径 远端路径   # 推文件到远端
  python hk_channel.py scp --pull 远端路径 本机路径  # 从远端拉文件

被其他脚本调用：
  from hk_channel import hk_run, hk_scp, pick_host
  rc, out = hk_run("echo hi")

环境变量（测试隔离 / 部署注入）：
  HK_DIRECT_HOST  直连别名（默认 remote-host，占位符）
  HK_JUMP_HOST    跳板别名（默认 remote-via-jump，占位符）
  HK_SSH_BIN      ssh 可执行（默认 ssh）
  HK_SCP_BIN      scp 可执行（默认 scp）
  HK_STATE_FILE   通道缓存文件（默认 <auto-skills>/.evolution/hk-channel-state.json）
  HK_PROBE_TIMEOUT 直连探测超时秒（默认 8）
  HK_DIRECT_FAIL_THRESHOLD 直连连续失败几次后优先走跳板（默认 1）
  HK_STATE_TTL    通道缓存有效期秒（默认 1800）
  HK_FORCE        强制通道（direct / jump），测试与排障用
"""
import json
import os
import pathlib
import subprocess
import sys
import time

def _host_alias(cfg_key: str, env_name: str, placeholder: str) -> str:
    """解析远端主机别名，三级回退：**私有层配置 → 环境变量 → 占位符**。

    为什么要有配置入口（2026-10-02 补）：这两个别名原先**只**来自环境变量，
    而仓库里没有任何脚本或配置去设置它们 —— 实测本机用户级/机器级环境变量
    均为空、无 .env、无相关计划任务，于是通道实际上**是死的**：
    每次调用都去连占位符名字 `remote-host`，必然失败。
    这与项目里其它链路（数据库/网关/知识库/通知）都有正规配置入口不一致，
    是唯一一条漏掉的。

    真实别名属本机信息，只放私有层（`.evolution/config.yaml`，不进公开库）；
    环境变量仍然优先于配置，便于临时覆盖与测试隔离；
    两级都没有时才用占位符（保持"脚本内不写死真实主机"这条设计约束）。
    """
    try:
        import config_manager
        v = config_manager.get_value("hk_channel.%s" % cfg_key, "")
        if v and str(v).strip():
            return str(v).strip()
    except Exception:
        pass                      # 单文件拷贝出去时也要能跑
    v = (os.environ.get(env_name) or "").strip()
    return v or placeholder


DIRECT_HOST = _host_alias("direct_host", "HK_DIRECT_HOST", "remote-host")
JUMP_HOST = _host_alias("jump_host", "HK_JUMP_HOST", "remote-via-jump")
SSH_BIN = os.environ.get("HK_SSH_BIN", "ssh")
SCP_BIN = os.environ.get("HK_SCP_BIN", "scp")
PROBE_TIMEOUT = int(os.environ.get("HK_PROBE_TIMEOUT", "8"))
STATE_FILE = pathlib.Path(os.environ.get(
    "HK_STATE_FILE",
    pathlib.Path(__file__).resolve().parent.parent / ".evolution" / "hk-channel-state.json"))
# 直连连续失败到这个次数就先走跳板（而不是每次都白等一遍探测超时）
DIRECT_FAIL_THRESHOLD = int(os.environ.get("HK_DIRECT_FAIL_THRESHOLD", "1"))
STATE_TTL = int(os.environ.get("HK_STATE_TTL", "1800"))


def _run(args, timeout):
    try:
        r = subprocess.run(args, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return 255, str(e)


def probe(host):
    """ssh 探测一台主机：echo OK 且退出码 0 才算可达。"""
    rc, out = _run([SSH_BIN, "-o", "BatchMode=yes",
                    "-o", "ConnectTimeout=%d" % PROBE_TIMEOUT,
                    "-o", "StrictHostKeyChecking=no", host, "echo HK_OK"],
                   timeout=PROBE_TIMEOUT + 10)
    return rc == 0 and "HK_OK" in out


def _load_state():
    try:
        d = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if time.time() - d.get("ts", 0) <= STATE_TTL:
            return d
    except (OSError, ValueError):
        pass
    return {}


def _save_state(d):
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # 状态文件写不进去只影响缓存，不影响通道本身


def pick_host(prefer=None):
    """返回 (host, how)，how ∈ {direct, jump}。

    HK_FORCE 优先；否则按缓存与直连失败计数：
      · 缓存里 jump 可用且直连失败计数 ≥ 阈值 → 直接跳板（不重复探测直连）
      · 否则先探测直连，通 → 直连；不通 → 探测跳板
    跳板也探测不过时抛 RuntimeError——调用方把错误交给上层，而不是静默选一个
    根本连不上的通道（静默失败是这个仓库踩过的坑）。
    """
    forced = os.environ.get("HK_FORCE")
    if forced:
        host = DIRECT_HOST if forced == "direct" else JUMP_HOST
        if not probe(host):
            raise RuntimeError("HK_FORCE=%s 但 %s 探测失败" % (forced, host))
        return host, forced

    st = _load_state()
    fails = int(st.get("direct_fails", 0))
    if prefer is None and fails >= DIRECT_FAIL_THRESHOLD and st.get("last_ok") == JUMP_HOST:
        if probe(JUMP_HOST):
            return JUMP_HOST, "jump"
    if probe(DIRECT_HOST):
        if fails:
            _save_state({"ts": time.time(), "direct_fails": 0, "last_ok": DIRECT_HOST})
        return DIRECT_HOST, "direct"
    # 直连失败：记数、切跳板
    st["direct_fails"] = fails + 1
    st["ts"] = time.time()
    if probe(JUMP_HOST):
        st["last_ok"] = JUMP_HOST
        _save_state(st)
        return JUMP_HOST, "jump"
    _save_state(st)
    raise RuntimeError("直连(%s)与跳板(%s)都不可达——本机没有外网且跳板机也连不上"
                       % (DIRECT_HOST, JUMP_HOST))


def hk_run(cmd, timeout=60):
    """在远端主机上执行 cmd，返回 (rc, 输出)。自动选通道。"""
    host, how = pick_host()
    rc, out = _run([SSH_BIN, "-o", "BatchMode=yes", host, cmd], timeout=timeout)
    return rc, ("[%s/%s]\n" % (host, how)) + out


def hk_scp(src, dst, pull=False, timeout=300):
    """推/拉文件。pull=True 表示从远端拉回本机。"""
    host, how = pick_host()
    if pull:
        args = [SCP_BIN, "-o", "BatchMode=yes", "%s:%s" % (host, src), dst]
    else:
        args = [SCP_BIN, "-o", "BatchMode=yes", src, "%s:%s" % (host, dst)]
    rc, out = _run(args, timeout=timeout)
    return rc, ("[%s/%s]\n" % (host, how)) + out


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--probe":
        try:
            host, how = pick_host()
            print("channel=%s host=%s" % (how, host))
            return 0
        except RuntimeError as e:
            print("FAIL: %s" % e)
            return 1
    if argv[0] == "run" and len(argv) > 1:
        rc, out = hk_run(argv[1])
        sys.stdout.write(out)
        return rc
    if argv[0] == "scp":
        rest = argv[1:]
        pull = "--pull" in rest
        rest = [a for a in rest if a != "--pull"]
        if len(rest) != 2:
            print("用法: hk_channel.py scp [--pull] 源 目标")
            return 2
        rc, out = hk_scp(rest[0], rest[1], pull=pull)
        sys.stdout.write(out)
        return rc
    print("未知子命令: %s" % " ".join(argv))
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
