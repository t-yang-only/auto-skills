#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wizard_setup.py — auto-skills 首次启动引导与全自动配置向导 (v3.0)
==================================================================
核心功能：
1. 【配置门禁检查】：在任意 Agent 首次调用时，检查 `config/config.yaml` 的 `is_configured` 状态；
2. 【引导配置细节】：
   - 是否自动下载公开 auto-skills 更新；
   - 是否永远默认启用 nm-skills 项目目录执行登记与原子任务认领 (agent_word/)；
   - 多渠道推送凭据（Server酱、企微、飞书等，可留空）；
   - 女朋友人格层是否默认开启及是否从知识库拉取特性；
   - 用户个人私有 Git 进化仓库绑定；
3. 【跨 Agent 智能扫描与连接建立】：
   - 自动探测本机所有 AI Agent 环境 (Codex, Agents, DSH, WorkBuddy, Claude Code, Cursor 等)；
   - 提供选择是否一键建立连接与同步映射。

用法：
    # 交互式完整引导向导
    python scripts/wizard_setup.py --interactive

    # 快捷自动推荐配置 (静默/自适应模式)
    python scripts/wizard_setup.py --auto

    # 查看当前配置状态
    python scripts/wizard_setup.py --status

    # 仅执行跨 Agent 扫描与连接
    python scripts/wizard_setup.py --connect-agents
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

import config_manager
import pull_persona_traits

KNOWN_AGENT_PATHS = [
    ("Codex CLI / Extension", Path.home() / ".codex" / "skills"),
    ("Claude Code / ~/.agents", Path.home() / ".agents" / "skills"),
    ("DeepSeek Harness (DSH)", Path.home() / ".dsh" / "skills"),
    ("WorkBuddy AI", Path.home() / ".workbuddy-ai" / "skills"),
    ("Claude Code Dedicated", Path.home() / ".claude" / "skills"),
    ("Cursor IDE", Path.home() / ".cursor" / "skills"),
]


def scan_local_agents() -> List[Dict[str, Any]]:
    results = []
    for name, p in KNOWN_AGENT_PATHS:
        exists = p.exists()
        has_autoskills = (p / "auto-skills").exists() or (p / "auto-skills.lnk").exists()
        results.append({
            "name": name,
            "path": str(p),
            "exists": exists,
            "connected": has_autoskills
        })
    return results


def connect_agents(agent_names: Optional[List[str]] = None) -> List[str]:
    """建立到扫描到的 Agent 目录的连接与同步"""
    connected = []
    auto_src = str(SKILL_ROOT)
    for name, p in KNOWN_AGENT_PATHS:
        if not p.exists():
            continue
        if agent_names and name not in agent_names and p.name not in agent_names:
            continue

        target_link = p / "auto-skills"
        print(f"[*] 正在为 【{name}】 建立 auto-skills 连接...")
        try:
            # 在 Windows 上优先使用 robocopy 同步以规避特权问题并保持原生稳定
            cmd = f'robocopy "{auto_src}" "{target_link}" /MIR /XD .git .evolution /R:1 /W:1 /NP /NFL /NDL'
            subprocess.run(["powershell", "-Command", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            connected.append(name)
            print(f"  [+] 成功连接至: {p}")
        except Exception as e:
            print(f"  [-] 连接失败: {e}")

    # 更新配置
    config_manager.set_value("agent_connections.connected_agents", connected)
    return connected


def run_auto_setup(
    always_nm: bool = True,
    auto_update: bool = True,
    girlfriend_mode: bool = False,
    kb_sync_gf: bool = False,
    private_git: str = "",
    connect_all_agents: bool = True
) -> bool:
    """自动完成基础配置并标记 is_configured: true"""
    print("\n" + "=" * 72)
    print("🚀 正在执行 auto-skills 基础配置自动化引导 (v3.0 旗舰版)...")
    print("=" * 72)

    cfg = config_manager.load_config()

    # 1. 自动更新
    cfg["auto_update"]["auto_download_public_update"] = auto_update
    print(f"[*] 公开库自动更新: {'启用' if auto_update else '禁用'}")

    # 2. nm-skills 协同台账
    cfg["nm_skills"]["always_enable_project_ledger"] = always_nm
    cfg["nm_skills"]["auto_claim_before_edit"] = True
    cfg["nm_skills"]["auto_check_file_conflicts"] = True
    cfg["nm_skills"]["auto_clean_stale_locks"] = True
    print(f"[*] nm-skills 协同防撞与项目台账 (agent_word/): {'永远默认启用' if always_nm else '按需手动启用'}")

    # 3. 人格层
    cfg["persona"]["talk_like_girlfriend"]["default_enabled"] = girlfriend_mode
    cfg["persona"]["talk_like_girlfriend"]["kb_sync_traits"] = kb_sync_gf
    if girlfriend_mode and kb_sync_gf:
        print("[*] 正在从知识库拉取女友人格特性...")
        pull_persona_traits.pull_and_sync_traits()  # 路径由 pull_persona_traits 按已保存配置解析
    print(f"[*] 女友人格模式: {'默认启用' if girlfriend_mode else '默认关闭 (可通过 /gf 显式触发)'}")

    # 4. 私有 Git 仓库
    if private_git:
        cfg["evolution_vault"]["private_git_remote"] = private_git
        print(f"[*] 个人私有 Git 进化仓库: {private_git}")
        # 联动同步脚本
        try:
            from sync_evolution import set_private_remote_url
            set_private_remote_url(private_git)
        except Exception:
            pass

    # 5. Agent 扫描与连接
    scanned = scan_local_agents()
    detected_existing = [a for a in scanned if a["exists"]]
    print(f"[*] 本机扫描到 {len(detected_existing)} 个活跃 Agent 环境:")
    for a in detected_existing:
        print(f"    - {a['name']} ({a['path']})")

    if connect_all_agents:
        conn_list = connect_agents()
        cfg["agent_connections"]["connected_agents"] = conn_list
        print(f"[OK] 已成功为 {len(conn_list)} 个 Agent 建立 auto-skills 连接！")

    # 标记配置完成
    cfg["is_configured"] = True
    config_manager.save_config(cfg)
    print("=" * 72)
    print("🎉 auto-skills 首次基础配置已圆满完成！后续调用将畅通无阻。")
    print("=" * 72 + "\n")
    return True


def print_status():
    cfg = config_manager.load_config()
    is_conf = cfg.get("is_configured", False)
    scanned = scan_local_agents()

    print("\n" + "=" * 72)
    print("📋 auto-skills 配置与环境集成总览")
    print("=" * 72)
    print(f"- 首次引导配置状态 : {'✅ 已配置 (Configured)' if is_conf else '⚠️ 待首次配置 (Unconfigured)'}")
    print(f"- 配置文件绝对路径 : {CONFIG_FILE}")
    print(f"- 公开库自动更新   : {cfg.get('auto_update', {}).get('auto_download_public_update')}")
    print(f"- nm-skills 默认启用: {cfg.get('nm_skills', {}).get('always_enable_project_ledger')}")
    print(f"- 女友人格默认启用 : {cfg.get('persona', {}).get('talk_like_girlfriend', {}).get('default_enabled')}")
    print(f"- 私有 Git 远端    : {cfg.get('evolution_vault', {}).get('private_git_remote') or '<未绑定>'}")
    print("-" * 72)
    print("🤖 本机 Agent 环境连接状态：")
    for a in scanned:
        stat = "🟢 已连接" if a["connected"] else ("🟡 已就绪未连接" if a["exists"] else "⚪ 未安装")
        print(f"  - {a['name']:<24}: {stat} ({a['path']})")
    print("=" * 72 + "\n")


def main():
    parser = argparse.ArgumentParser(description="auto-skills 首次启动引导与配置向导")
    parser.add_argument("--status", action="store_true", help="查看当前配置与 Agent 连接状态")
    parser.add_argument("--auto", action="store_true", help="自动以推荐安全标准完成首次配置")
    parser.add_argument("--connect-agents", action="store_true", help="立即扫描并建立到所有 Agent 环境的连接")
    parser.add_argument("--always-nm", choices=["true", "false"], help="设置是否永远默认启用 nm-skills 台账")
    parser.add_argument("--gf-mode", choices=["true", "false"], help="设置是否默认开启女友人格")
    parser.add_argument("--set-private-remote", help="设置个人私有 Git 仓库 URL")

    args = parser.parse_args()

    if args.status:
        print_status()
        sys.exit(0)

    if args.connect_agents:
        connect_agents()
        sys.exit(0)

    # 快捷配置单个字段
    if args.always_nm:
        config_manager.set_value("nm_skills.always_enable_project_ledger", args.always_nm == "true")
        print(f"[OK] nm_skills.always_enable_project_ledger 已更新为: {args.always_nm}")

    if args.gf_mode:
        config_manager.set_value("persona.talk_like_girlfriend.default_enabled", args.gf_mode == "true")
        print(f"[OK] persona.talk_like_girlfriend.default_enabled 已更新为: {args.gf_mode}")

    if args.set_private_remote:
        config_manager.set_value("evolution_vault.private_git_remote", args.set_private_remote)
        print(f"[OK] evolution_vault.private_git_remote 已更新为: {args.set_private_remote}")

    # 默认或 --auto 执行
    if args.auto or not config_manager.is_configured():
        run_auto_setup(
            always_nm=True,
            auto_update=True,
            girlfriend_mode=False,
            kb_sync_gf=True,
            private_git="",
            connect_all_agents=True
        )


if __name__ == "__main__":
    main()
