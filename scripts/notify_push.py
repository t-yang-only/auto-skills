#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notify_push.py — 多渠道消息同步与任务自动化推送总控中心 (Multi-Channel Sync Hub)
================================================================================
首次支持多渠道聚合消息同步，支持客户/用户自由按需配置多种主流推送平台：

1. 【支持的消息推送渠道 (Supported Channels)】：
   - [serverchan] Server酱 Turbo 版 (微信推送 / 移动端)
   - [wecom] 企业微信群机器人 (WeCom Group Webhook - Markdown)
   - [feishu] 飞书群机器人 (Feishu / Lark Webhook - 富文本/卡片)
   - [dingtalk] 钉钉群机器人 (DingTalk Webhook - 支持加签安全密钥)
   - [pushplus] PushPlus 推送加 (微信模版消息)
   - [telegram] Telegram Bot (TG群组/频道通知)
   - [bark] Bark (iOS 极客专用即时弹窗推送)
   - [custom] 自定义通用 HTTP Webhook (接收任意 POST JSON)

2. 【客户自配置与隐私隔离 (Customer-Driven Configuration)】：
   - 配置优先存储于 `.evolution/secrets/notify_channels.json` (已被 .gitignore 严密隔离)
   - 回退存储于全局 `~/.config/auto-skills/notify_channels.json`
   - 首次开箱零配置：默认预置 Server酱 Turbo 稳定通道
   - 提供丰富的 CLI 配置与交互向导：
     * `python scripts/notify_push.py --config-list` : 查看所有渠道配置及启用状态
     * `python scripts/notify_push.py --config-set <channel> <param>` : 配置指定渠道参数
     * `python scripts/notify_push.py --enable <channel>` / `--disable <channel>` : 启停开关
     * `python scripts/notify_push.py --test [channel]` : 联通性测试（单渠道或全部广播）
     * `python scripts/notify_push.py --wizard` : 交互式首次配置向导

3. 【并发/聚合广播 (Multi-Channel Broadcast)】：
   - 任务完成时，自动将结构化 Markdown 任务卡片并行推送至所有已启用的渠道；
   - 输出清晰的逐渠道投递回执 (PASS/FAIL)，单渠道网络故障绝不阻断其他渠道投递。
"""

import os
import sys
import json
import time
import hmac
import hashlib
import base64
import argparse
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent

# 配置文件寻址优先级：.evolution/secrets -> ~/.config/auto-skills -> .sendkey
CONFIG_LOCATIONS = [
    SKILL_ROOT / ".evolution" / "secrets" / "notify_channels.json",
    Path.home() / ".config" / "auto-skills" / "notify_channels.json",
    SKILL_ROOT / ".sendkey"
]

DEFAULT_SERVERCHAN_KEY = "SCT280861TA-2aWLS0PNUXewsTX4DrUBffTt"


def get_active_config_path() -> Path:
    """获取主要写入的配置文件路径（优先放在 .evolution/secrets 中）"""
    primary = SKILL_ROOT / ".evolution" / "secrets" / "notify_channels.json"
    if not primary.parent.exists():
        primary.parent.mkdir(parents=True, exist_ok=True)
    return primary


def resolve_sendkey(explicit_key: Optional[str] = None) -> str:
    """解析有效的 Server酱 SendKey (兼容旧调用)"""
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()
    cfg = load_channels_config()
    sc = cfg.get("channels", {}).get("serverchan", {})
    k = sc.get("sendkey", "").strip()
    return k or DEFAULT_SERVERCHAN_KEY


def load_channels_config() -> Dict[str, Any]:
    """读取所有渠道配置，包含智能回退与默认值"""
    # 查找已有配置
    for p in CONFIG_LOCATIONS:
        if p.exists() and p.is_file():
            try:
                if p.name.endswith(".json"):
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if "channels" in data:
                        return data
                elif p.name == ".sendkey":
                    k = p.read_text(encoding="utf-8").strip()
                    if k:
                        return create_default_config(serverchan_key=k)
            except Exception:
                pass

    # 若未找到任何配置，创建默认配置
    default_cfg = create_default_config(serverchan_key=DEFAULT_SERVERCHAN_KEY)
    try:
        cfg_path = get_active_config_path()
        cfg_path.write_text(json.dumps(default_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return default_cfg


def create_default_config(serverchan_key: str = DEFAULT_SERVERCHAN_KEY) -> Dict[str, Any]:
    """创建开箱即用的多渠道结构模板"""
    return {
        "version": "2.0",
        "description": "auto-skills 多渠道消息同步配置",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "channels": {
            "serverchan": {
                "name": "Server酱 Turbo (微信推送)",
                "enabled": True,
                "sendkey": serverchan_key,
                "channel_type": "sct"
            },
            "wecom": {
                "name": "企业微信群机器人 (WeCom)",
                "enabled": False,
                "webhook_url": ""
            },
            "feishu": {
                "name": "飞书群机器人 (Feishu/Lark)",
                "enabled": False,
                "webhook_url": ""
            },
            "dingtalk": {
                "name": "钉钉群机器人 (DingTalk)",
                "enabled": False,
                "webhook_url": "",
                "secret": ""
            },
            "pushplus": {
                "name": "PushPlus (推送加)",
                "enabled": False,
                "token": ""
            },
            "telegram": {
                "name": "Telegram 机器人",
                "enabled": False,
                "bot_token": "",
                "chat_id": ""
            },
            "bark": {
                "name": "Bark (iOS 即时推送)",
                "enabled": False,
                "device_key": "",
                "server_url": "https://api.day.app"
            },
            "custom": {
                "name": "自定义 HTTP Webhook",
                "enabled": False,
                "url": "",
                "headers": {}
            }
        }
    }


def save_channels_config(cfg: Dict[str, Any]) -> bool:
    """保存配置到安全的私有进化区"""
    try:
        cfg["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target = get_active_config_path()
        target.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[ERROR] 保存多渠道配置失败: {e}")
        return False


def mask_secret(val: str) -> str:
    """脱敏展示密钥"""
    if not val:
        return "<未配置>"
    if len(val) <= 8:
        return "***"
    return f"{val[:4]}...{val[-4:]}"


# ==============================================================================
# 各渠道底层通信适配器 (纯标准库，零外部依赖)
# ==============================================================================

def http_post_json(url: str, payload: dict, headers: dict = None, timeout: int = 15) -> Tuple[bool, str]:
    """标准 HTTP POST JSON 请求"""
    req_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "AutoSkills-MultiChannelHub/2.0"
    }
    if headers:
        req_headers.update(headers)

    try:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST", headers=req_headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_text = resp.read().decode("utf-8", errors="replace")
            return True, resp_text
    except Exception as e:
        return False, str(e)


def send_to_serverchan(cfg: dict, title: str, desp: str, tags: str = "任务通知") -> Tuple[bool, str]:
    sendkey = cfg.get("sendkey", "").strip()
    if not sendkey:
        return False, "未配置 Server酱 SendKey"
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    payload = {"title": title[:100], "desp": desp, "tags": tags}
    try:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("code") == 0:
                return True, "推送成功 (Server酱)"
            return False, f"Server酱返回错误: {res.get('message', res)}"
    except Exception as e:
        return False, str(e)


def send_to_wecom(cfg: dict, title: str, desp: str) -> Tuple[bool, str]:
    url = cfg.get("webhook_url", "").strip()
    if not url:
        return False, "未配置企业微信 Webhook 地址"
    markdown_content = f"### {title}\n{desp}"
    payload = {
        "msgtype": "markdown",
        "markdown": {"content": markdown_content}
    }
    ok, res = http_post_json(url, payload)
    if ok:
        try:
            r = json.loads(res)
            if r.get("errcode") == 0:
                return True, "企业微信机器人推送成功"
            return False, f"企业微信错误: {r.get('errmsg')}"
        except Exception:
            return True, "企业微信已发送"
    return False, res


def send_to_feishu(cfg: dict, title: str, desp: str) -> Tuple[bool, str]:
    url = cfg.get("webhook_url", "").strip()
    if not url:
        return False, "未配置飞书 Webhook 地址"
    payload = {
        "msg_type": "text",
        "content": {
            "text": f"【{title}】\n\n{desp}"
        }
    }
    ok, res = http_post_json(url, payload)
    if ok:
        try:
            r = json.loads(res)
            if r.get("code") == 0 or r.get("StatusCode") == 0:
                return True, "飞书群机器人推送成功"
            return False, f"飞书返回错误: {r.get('msg', res)}"
        except Exception:
            return True, "飞书已发送"
    return False, res


def send_to_dingtalk(cfg: dict, title: str, desp: str) -> Tuple[bool, str]:
    url = cfg.get("webhook_url", "").strip()
    secret = cfg.get("secret", "").strip()
    if not url:
        return False, "未配置钉钉 Webhook 地址"

    target_url = url
    if secret:
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode("utf-8")
        string_to_sign = f"{timestamp}\n{secret}"
        string_to_sign_enc = string_to_sign.encode("utf-8")
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        sep = "&" if "?" in url else "?"
        target_url = f"{url}{sep}timestamp={timestamp}&sign={sign}"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"### {title}\n\n{desp}"
        }
    }
    ok, res = http_post_json(target_url, payload)
    if ok:
        try:
            r = json.loads(res)
            if r.get("errcode") == 0:
                return True, "钉钉机器人推送成功"
            return False, f"钉钉返回错误: {r.get('errmsg')}"
        except Exception:
            return True, "钉钉已发送"
    return False, res


def send_to_pushplus(cfg: dict, title: str, desp: str) -> Tuple[bool, str]:
    token = cfg.get("token", "").strip()
    if not token:
        return False, "未配置 PushPlus Token"
    url = "http://www.pushplus.plus/send"
    payload = {
        "token": token,
        "title": title,
        "content": desp,
        "template": "markdown"
    }
    ok, res = http_post_json(url, payload)
    if ok:
        try:
            r = json.loads(res)
            if r.get("code") == 200:
                return True, "PushPlus 推送成功"
            return False, f"PushPlus 返回: {r.get('msg')}"
        except Exception:
            return True, "PushPlus 已发送"
    return False, res


def send_to_telegram(cfg: dict, title: str, desp: str) -> Tuple[bool, str]:
    bot_token = cfg.get("bot_token", "").strip()
    chat_id = cfg.get("chat_id", "").strip()
    if not bot_token or not chat_id:
        return False, "未配置 Telegram bot_token 或 chat_id"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"*{title}*\n\n{desp}",
        "parse_mode": "Markdown"
    }
    ok, res = http_post_json(url, payload)
    if ok:
        try:
            r = json.loads(res)
            if r.get("ok"):
                return True, "Telegram 推送成功"
            return False, f"TG 错误: {r.get('description')}"
        except Exception:
            return True, "Telegram 已发送"
    return False, res


def send_to_bark(cfg: dict, title: str, desp: str) -> Tuple[bool, str]:
    key = cfg.get("device_key", "").strip()
    server = cfg.get("server_url", "https://api.day.app").rstrip("/")
    if not key:
        return False, "未配置 Bark Device Key"
    url = f"{server}/{key}/"
    payload = {
        "title": title,
        "body": desp,
        "group": "auto-skills",
        "icon": "https://img.icons8.com/fluency/96/rocket.png"
    }
    ok, res = http_post_json(url, payload)
    if ok:
        return True, "Bark 推送成功"
    return False, res


def send_to_custom(cfg: dict, title: str, desp: str) -> Tuple[bool, str]:
    url = cfg.get("url", "").strip()
    if not url:
        return False, "未配置自定义 Webhook URL"
    payload = {
        "event": "task_complete",
        "timestamp": datetime.now().isoformat(),
        "title": title,
        "content": desp
    }
    headers = cfg.get("headers", {})
    ok, res = http_post_json(url, payload, headers=headers)
    if ok:
        return True, "自定义 Webhook 触发成功"
    return False, res


# 渠道分发映射表
DISPATCH_MAP = {
    "serverchan": send_to_serverchan,
    "wecom": send_to_wecom,
    "feishu": send_to_feishu,
    "dingtalk": send_to_dingtalk,
    "pushplus": send_to_pushplus,
    "telegram": send_to_telegram,
    "bark": send_to_bark,
    "custom": send_to_custom
}


# ==============================================================================
# 多渠道聚合广播调度器
# ==============================================================================

def broadcast_message(title: str, desp: str, tags: str = "任务完成|报告", target_channel: Optional[str] = None) -> Dict[str, Any]:
    """
    向所有启用的渠道（或指定渠道）并发/聚合广播消息
    """
    cfg = load_channels_config()
    channels = cfg.get("channels", {})
    report = {
        "title": title,
        "broadcast_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_active_channels": 0,
        "success_count": 0,
        "failed_count": 0,
        "details": {}
    }

    targets = [target_channel] if target_channel else list(channels.keys())

    for ch_name in targets:
        ch_cfg = channels.get(ch_name)
        if not ch_cfg:
            continue
        if not target_channel and not ch_cfg.get("enabled", False):
            continue

        report["total_active_channels"] += 1
        fn = DISPATCH_MAP.get(ch_name)
        if not fn:
            report["details"][ch_name] = {"success": False, "message": "不支持的渠道类型"}
            report["failed_count"] += 1
            continue

        try:
            if ch_name == "serverchan":
                ok, msg = fn(ch_cfg, title, desp, tags=tags)
            else:
                ok, msg = fn(ch_cfg, title, desp)

            report["details"][ch_name] = {"success": ok, "message": msg, "name": ch_cfg.get("name", ch_name)}
            if ok:
                report["success_count"] += 1
                print(f"  [+] 【{ch_cfg.get('name', ch_name)}】同步成功")
            else:
                report["failed_count"] += 1
                print(f"  [-] 【{ch_cfg.get('name', ch_name)}】同步失败: {msg}")
        except Exception as e:
            report["details"][ch_name] = {"success": False, "message": str(e), "name": ch_cfg.get("name", ch_name)}
            report["failed_count"] += 1
            print(f"  [!] 【{ch_cfg.get('name', ch_name)}】发生异常: {e}")

    return report


def notify_task_complete(
    task_name: str,
    project_name: str = "auto-skills",
    summary: str = "",
    deliverables: Optional[list] = None,
    git_commit: Optional[str] = None,
    sendkey: Optional[str] = None,
    tags: str = "任务完成|报告"
) -> Dict[str, Any]:
    """
    提供给外部脚本调用的统一入口（向下兼容原有调用，同时自动广播给所有已配置的多渠道）
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f"【完成】{project_name}: {task_name}"

    lines = [
        f"## ✅ 【{project_name}】大型研发任务执行完成",
        f"- **任务名称**：{task_name}",
        f"- **执行状态**：`SUCCESS`",
        f"- **完成时间**：{now_str}",
    ]
    if git_commit:
        lines.append(f"- **Git 提交**：`{git_commit}`")
    if summary:
        lines.append(f"\n### 📝 任务成果总结\n{summary}")
    if deliverables:
        lines.append("\n### 📦 核心交付物清单")
        for item in deliverables:
            lines.append(f"- {item}")
    lines.append("\n---\n*由 auto-skills 多渠道聚合消息同步中心自动化广播*")
    desp = "\n".join(lines)

    # 临时覆盖 Server酱 key (兼容旧参数)
    if sendkey:
        cfg = load_channels_config()
        if "serverchan" in cfg.get("channels", {}):
            cfg["channels"]["serverchan"]["sendkey"] = sendkey
            save_channels_config(cfg)

    print(f"[*] 正在为项目【{project_name}】执行多渠道消息聚合广播...")
    return broadcast_message(title=title, desp=desp, tags=tags)


# ==============================================================================
# CLI 配置与管理功能
# ==============================================================================

def print_config_list():
    cfg = load_channels_config()
    channels = cfg.get("channels", {})
    print("\n" + "=" * 70)
    print("📡 auto-skills 多渠道消息同步配置一览表")
    print(f"   配置文件路径: {get_active_config_path()}")
    print("=" * 70)
    print(f"{'渠道标识':<12} | {'渠道显示名':<22} | {'状态':<8} | {'主要凭据/地址'}")
    print("-" * 70)

    for cid, cinfo in channels.items():
        state = "🟢 启用" if cinfo.get("enabled", False) else "⚪ 禁用"
        name = cinfo.get("name", cid)

        param = ""
        if cid == "serverchan":
            param = mask_secret(cinfo.get("sendkey", ""))
        elif cid in ("wecom", "feishu", "dingtalk"):
            param = mask_secret(cinfo.get("webhook_url", ""))
            if cid == "dingtalk" and cinfo.get("secret"):
                param += " (带安全签名)"
        elif cid == "pushplus":
            param = mask_secret(cinfo.get("token", ""))
        elif cid == "telegram":
            param = f"bot:{mask_secret(cinfo.get('bot_token', ''))} | chat:{cinfo.get('chat_id', '')}"
        elif cid == "bark":
            param = f"key:{mask_secret(cinfo.get('device_key', ''))}"
        elif cid == "custom":
            param = cinfo.get("url", "<未配置>")

        print(f"{cid:<12} | {name:<20} | {state:<6} | {param}")
    print("=" * 70)
    print("💡 快捷命令指南：")
    print("  - 启停渠道: python scripts/notify_push.py --enable wecom / --disable serverchan")
    print("  - 配置参数: python scripts/notify_push.py --config-set wecom 'https://qyapi.weixin.qq.com/...'")
    print("  - 联通测试: python scripts/notify_push.py --test [渠道名]\n")


def set_channel_config(channel: str, val: str, extra: Optional[str] = None):
    cfg = load_channels_config()
    channels = cfg.get("channels", {})
    if channel not in channels:
        print(f"[ERROR] 不支持的渠道标识: {channel} (支持: {list(channels.keys())})")
        return False

    c = channels[channel]
    if channel == "serverchan":
        c["sendkey"] = val
    elif channel in ("wecom", "feishu"):
        c["webhook_url"] = val
    elif channel == "dingtalk":
        c["webhook_url"] = val
        if extra:
            c["secret"] = extra
    elif channel == "pushplus":
        c["token"] = val
    elif channel == "telegram":
        c["bot_token"] = val
        if extra:
            c["chat_id"] = extra
    elif channel == "bark":
        c["device_key"] = val
    elif channel == "custom":
        c["url"] = val

    c["enabled"] = True  # 配置后自动启用
    save_channels_config(cfg)
    print(f"[OK] 渠道【{channel}】配置已更新并已自动启用！")
    return True


def toggle_channel(channel: str, enable: bool):
    cfg = load_channels_config()
    channels = cfg.get("channels", {})
    if channel not in channels:
        print(f"[ERROR] 未知渠道标识: {channel}")
        return False
    channels[channel]["enabled"] = enable
    save_channels_config(cfg)
    status_str = "启用" if enable else "禁用"
    print(f"[OK] 渠道【{channel}】已切换为: {status_str}")
    return True


def main():
    parser = argparse.ArgumentParser(description="多渠道消息同步与任务自动化推送总控中心")
    parser.add_argument("-t", "--title", default="大型任务执行完毕", help="通知标题")
    parser.add_argument("-d", "--desp", default="", help="通知正文 (支持 Markdown)")
    parser.add_argument("-p", "--project", default="auto-skills", help="项目名称")
    parser.add_argument("--tags", default="任务完成|报告", help="Server酱分类标签")
    parser.add_argument("-k", "--sendkey", default=None, help="临时指定 Server酱 SendKey")
    parser.add_argument("--channel", help="只推送给指定渠道 (缺省广播至全部启用的渠道)")

    # 配置选项
    parser.add_argument("--config-list", action="store_true", help="列出所有渠道配置状态")
    parser.add_argument("--config-set", nargs="+", help="配置渠道: --config-set <channel> <param> [extra]")
    parser.add_argument("--enable", help="启用指定渠道 (如 wecom, feishu, dingtalk, serverchan)")
    parser.add_argument("--disable", help="禁用指定渠道")
    parser.add_argument("--test", nargs="?", const="all", help="测试消息联通性 (--test 或 --test wecom)")

    args = parser.parse_args()

    if args.config_list:
        print_config_list()
        sys.exit(0)

    if args.config_set:
        ch = args.config_set[0]
        val = args.config_set[1] if len(args.config_set) > 1 else ""
        extra = args.config_set[2] if len(args.config_set) > 2 else None
        set_channel_config(ch, val, extra)
        sys.exit(0)

    if args.enable:
        toggle_channel(args.enable, True)
        sys.exit(0)

    if args.disable:
        toggle_channel(args.disable, False)
        sys.exit(0)

    if args.test:
        target = None if args.test == "all" else args.test
        print(f"[*] 正在发起消息同步联通性自检测试 (目标: {target or '全部已启用渠道'})...")
        res = broadcast_message(
            title="【自检】auto-skills 多渠道消息同步测试",
            desp=f"这是一条来自 auto-skills 消息同步中心的广播自检消息。\n\n- 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n- 状态：Normal",
            tags="自检|测试",
            target_channel=target
        )
        print(f"[+] 自检完成：成功 {res['success_count']} 个，失败 {res['failed_count']} 个")
        sys.exit(0 if res["failed_count"] == 0 else 1)

    # 普通推送
    if not args.desp:
        args.desp = f"任务【{args.title}】自动化流水线已执行完毕，各项指标检查通过。"

    broadcast_message(title=args.title, desp=args.desp, tags=args.tags, target_channel=args.channel)


if __name__ == "__main__":
    main()
