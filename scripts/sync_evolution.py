#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_evolution.py — 用户个人私有进化仓库自动同步与 Git 推送引擎
================================================================
核心功能：
1. 【专属私有隔离 (Zero Leakage)】：
   - 专用于 `.evolution/` 独立私有 Git 仓库；
   - 与公开上游开源库完全隔离，任何个人偏好、私有密钥与动态自安装技能绝不外泄；
2. 【用户个人同步一键推送 (Private Git Sync)】：
   - 自动检测并初始化 `.evolution` 私有 Git 仓库；
   - 暂存新增与修改的自定义技能 (`custom_skills/`)、Obsidian 笔记同步数据、配置文件等；
   - 自动 commit，并在已配置 private_remote 时自动 push 到用户的私有 GitHub/GitLab 仓库；
3. 【多渠道通知联动】：
   - 同步完成后可自动通过 Server酱/企微/飞书等向用户微信或移动端发送同步回执。

用法示例：
    # 查看当前私有进化仓库状态与远端配置
    python scripts/sync_evolution.py --status

    # 设置远端私有 Git 仓库地址 (如 git@github.com:yourname/my-private-skills.git)
    python scripts/sync_evolution.py --set-remote "git@github.com:yourname/my-private-skills.git"

    # 执行一键同步与推送
    python scripts/sync_evolution.py -m "feat: add newly installed custom skill"
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
EVOLUTION_DIR = SKILL_ROOT / ".evolution"


def run_git_cmd(args: List[str], cwd: Path) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


def ensure_private_git_repo() -> bool:
    """确保 .evolution 拥有独立的 Git 仓库"""
    EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)
    git_dir = EVOLUTION_DIR / ".git"
    if not git_dir.exists():
        print("[*] 正在为个人私有进化空间初始化独立 Git 仓库...")
        code, out, err = run_git_cmd(["init", "-b", "main"], EVOLUTION_DIR)
        if code != 0:
            print(f"[ERROR] git init 失败: {err}")
            return False
        # 初始化 .gitignore
        ign = EVOLUTION_DIR / ".gitignore"
        if not ign.exists():
            ign.write_text("__pycache__/\n*.py[cod]\n*.tmp\n", encoding="utf-8")
        run_git_cmd(["add", "-A"], EVOLUTION_DIR)
        run_git_cmd(["commit", "-m", "chore: initialize user private evolution repository"], EVOLUTION_DIR)
        print("[OK] 独立私有 Git 仓库初始化完成！")
    return True


def get_private_remote_url() -> str:
    if not (EVOLUTION_DIR / ".git").exists():
        return ""
    code, out, _ = run_git_cmd(["config", "--get", "remote.origin.url"], EVOLUTION_DIR)
    return out if code == 0 else ""


def set_private_remote_url(url: str) -> bool:
    ensure_private_git_repo()
    url = url.strip()
    if not url:
        # 删除 remote
        run_git_cmd(["remote", "remove", "origin"], EVOLUTION_DIR)
        print("[OK] 已移除私有远端仓库绑定。")
        return True

    existing = get_private_remote_url()
    if existing:
        code, _, err = run_git_cmd(["remote", "set-url", "origin", url], EVOLUTION_DIR)
    else:
        code, _, err = run_git_cmd(["remote", "add", "origin", url], EVOLUTION_DIR)

    if code == 0:
        print(f"[OK] 成功设置个人私有远端 Git 仓库: {url}")
        return True
    else:
        print(f"[ERROR] 设置私有远端失败: {err}")
        return False


def sync_private_evolution(message: str = "chore: sync user private evolution assets", notify: bool = True) -> bool:
    """
    暂存、提交并推送到用户的私有 Git 仓库
    """
    ensure_private_git_repo()

    print(f"[*] 正在为用户私有进化空间 (.evolution) 执行自动同步与暂存...")
    run_git_cmd(["add", "-A"], EVOLUTION_DIR)

    # 检查是否有改动
    code, status_out, _ = run_git_cmd(["status", "-s"], EVOLUTION_DIR)
    has_changes = bool(status_out.strip())

    commit_sha = ""
    if has_changes:
        code, commit_out, err = run_git_cmd(["commit", "-m", message], EVOLUTION_DIR)
        if code != 0:
            print(f"[!] git commit 失败: {err}")
            return False
        # 提取 commit sha
        c_code, c_sha, _ = run_git_cmd(["rev-parse", "--short", "HEAD"], EVOLUTION_DIR)
        commit_sha = c_sha if c_code == 0 else "HEAD"
        print(f"[OK] 私有进化内容已提交: {message} ({commit_sha})")
    else:
        print("[*] 私有进化工作区整洁，无待提交改动。")
        c_code, c_sha, _ = run_git_cmd(["rev-parse", "--short", "HEAD"], EVOLUTION_DIR)
        commit_sha = c_sha if c_code == 0 else ""

    # 推送远端
    remote_url = get_private_remote_url()
    push_success = False
    if remote_url:
        print(f"[*] 正在推送到用户私有 Git 仓库 ({remote_url})...")
        code, push_out, push_err = run_git_cmd(["push", "-u", "origin", "main"], EVOLUTION_DIR)
        if code == 0:
            print(f"🎉 [OK] 成功推送至个人私有 Git 仓库！(Commit: {commit_sha})")
            push_success = True
        else:
            print(f"⚠️ [WARN] 私有远端推送提示: {push_err or push_out}")
            print("   💡 提示: 请确保已为私有远端配置好 SSH 密钥或凭据认证。")
    else:
        print("💡 [提示] 当前尚未配置私有远端 Git 地址 (可通过 --set-remote <url> 绑定)。本地私有版本已提交就绪。")

    # 消息通知
    if notify and has_changes:
        try:
            from notify_push import broadcast_message
            title = f"【私有进化同步】auto-skills 个人私有知识与技能已同步"
            desp = (
                f"## 🧬 个人私有进化仓库同步完成\n\n"
                f"- **提交说明**：{message}\n"
                f"- **Commit**：`{commit_sha}`\n"
                f"- **私有远端**：`{remote_url or '仅本地私有仓库 (未配远端)'}`\n"
                f"- **时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"*由 auto-skills 私有进化中枢自动化推送*"
            )
            broadcast_message(title=title, desp=desp, tags="私有同步|进化")
        except Exception:
            pass

    return True


def print_status():
    ensure_private_git_repo()
    remote = get_private_remote_url()
    code, head, _ = run_git_cmd(["rev-parse", "--short", "HEAD"], EVOLUTION_DIR)
    code, st, _ = run_git_cmd(["status", "-s"], EVOLUTION_DIR)

    cs_dir = EVOLUTION_DIR / "custom_skills"
    custom_skills = [d.name for d in cs_dir.iterdir() if d.is_dir() and not d.name.startswith(".")] if cs_dir.exists() else []

    print("\n" + "=" * 70)
    print("🧬 auto-skills 用户个人私有进化 Git 仓库状态")
    print("=" * 70)
    print(f"- 本地私有目录 : {EVOLUTION_DIR}")
    print(f"- 当前分支版本 : main ({head or '初始'})")
    print(f"- 私有远端仓库 : {remote or '<未配置私有远端 (仅本地跟踪)>'}")
    print(f"- 自定义技能数 : {len(custom_skills)} 个 ({', '.join(custom_skills) or '暂无'})")
    print(f"- 待暂存/改动  : {len(st.splitlines()) if st.strip() else 0} 处改动")
    print("=" * 70)
    print("💡 常用命令：")
    print("  - 绑定私有库: python scripts/sync_evolution.py --set-remote 'git@github.com:user/my-skills.git'")
    print("  - 一键提交推送: python scripts/sync_evolution.py -m '同步新增的私有技能与笔记'")
    print("  - 状态查验: python scripts/sync_evolution.py --status\n")


def main():
    parser = argparse.ArgumentParser(description="auto-skills 用户个人私有进化仓库自动同步与 Git 推送引擎")
    parser.add_argument("--status", action="store_true", help="查看私有进化仓库状态与远端配置")
    parser.add_argument("--set-remote", help="设置或更新私有 Git 远端仓库 URL (可传 '' 清除)")
    parser.add_argument("-m", "--message", default="chore: sync user private evolution assets", help="提交信息")
    parser.add_argument("--no-notify", action="store_true", help="不发送多渠道广播通知")

    args = parser.parse_args()

    if args.set_remote is not None:
        set_private_remote_url(args.set_remote)
        sys.exit(0)

    if args.status:
        print_status()
        sys.exit(0)

    # 默认执行同步
    sync_private_evolution(message=args.message, notify=not args.no_notify)


if __name__ == "__main__":
    main()
