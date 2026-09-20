#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_evolution_vault.py — 个人私有进化仓库初始化与双轨隔离向导 (Dual-Track Evolution Vault)
========================================================================================
核心架构与设计思想：
1. 【双轨架构隔离 (Dual-Track Isolation)】：
   - 轨道 A (公共上游核心)：auto-skills 公开 Git 仓库 (t-yang-only/auto-skills)，保持通用开源工程基座。
     用户随时可通过 `git pull origin main` 无缝拉取上游核心代码与新工具更新。
   - 轨道 B (用户私有进化)：`.evolution/` 目录已被 `.gitignore` 严格忽略，独立成为用户私有的 Git 仓库。
     用户的个人使用习惯、隐私凭据、自定义孵化技能、项目经验与 Obsidian 知识沉淀全部落盘在此。
     上游公共仓库更新时，绝对不覆盖、不冲突、不泄露用户的私有进化内容！
2. 【目录规范规划】：
   .evolution/
   ├── README.md               # 私有进化仓库说明
   ├── profile/                # 个人习惯、偏好设定、提示词注入与角色设定
   │   └── user_habits.yaml    # 习惯配置文件
   ├── custom_skills/          # 个人孵化或定制的私有 Skill 库 (由 auto_router 优先索引)
   ├── obsidian_sync/          # Obsidian 知识库双向同步挂载点与映射配置
   │   └── config.json         # 知识库路径与同步规则
   ├── secrets/                # 隐私密钥与本地凭据 (彻底隔离不入公网)
   └── journal/                # 经验复盘、实战教训与迭代日记
3. 【引导与自动化】：
   - 首次使用引导：支持自动检测并向用户发起进化引导；
   - 自动初始化私有 Git 仓库（可选绑定 GitHub / Gitee 私有仓库远端）；
   - 自动检测并挂载本地 Obsidian 知识库 (如 D:\\LLM-Wiki)。
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
EVOLUTION_DIR = SKILL_ROOT / ".evolution"
GITIGNORE_FILE = SKILL_ROOT / ".gitignore"

DEFAULT_OBSIDIAN_CANDIDATES = [
    Path("D:/ObsidianVault"),
    Path.home() / "Documents" / "Obsidian Vault",
    Path.home() / "Obsidian",
]


def ensure_gitignore_guard() -> bool:
    """
    核验根目录 .gitignore 是否已将 .evolution/ 严密守卫
    """
    if not GITIGNORE_FILE.exists():
        GITIGNORE_FILE.write_text(".evolution/\n*.private.*\n.sendkey\n", encoding="utf-8")
        return True

    content = GITIGNORE_FILE.read_text(encoding="utf-8", errors="ignore")
    if ".evolution/" not in content and ".evolution" not in content:
        with open(GITIGNORE_FILE, "a", encoding="utf-8") as f:
            f.write("\n# Private Evolution Vault\n.evolution/\n*.private.*\n.sendkey\n")
        print("[OK] 已向 .gitignore 写入 .evolution/ 隔离守卫")
    return True


def init_evolution_structure(
    obsidian_path: Optional[str] = None,
    private_remote: Optional[str] = None,
    online_url: Optional[str] = None,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    创建并初始化 .evolution 私有进化工作区 (支持本地路径、在线知识库URL与密钥)
    """
    ensure_gitignore_guard()

    subdirs = [
        EVOLUTION_DIR / "profile",
        EVOLUTION_DIR / "custom_skills",
        EVOLUTION_DIR / "obsidian_sync",
        EVOLUTION_DIR / "secrets",
        EVOLUTION_DIR / "journal",
    ]
    for sd in subdirs:
        sd.mkdir(parents=True, exist_ok=True)

    # 1. 写入 README.md
    readme_path = EVOLUTION_DIR / "README.md"
    if not readme_path.exists():
        readme_path.write_text("""# 个人私有进化知识库 (Private Evolution Vault)

本目录由 auto-skills 的双轨进化机制自动创建，用于承载属于用户自己的个性化进化资产。

## 目录职能：
- `profile/`: 存放个人工作偏好、代码风格、口癖、常用模板与专属规则；
- `custom_skills/`: 存放你自己编写或孵化的私有 Skill（受 auto_router.py 优先解析寻址）；
- `obsidian_sync/`: 与本地 Obsidian 知识库 (如 D:\\LLM-Wiki) 的同步双向映射区；
- `secrets/`: 本地专用凭据 (API Keys, Token, 敏感配置)；
- `journal/`: 历史研发任务复盘日志与经验总结。

## 安全与隔离保证：
上级根目录的 `.gitignore` 已包含 `.evolution/`，上游主仓库更新 (`git pull origin main`) 时
绝不会覆盖或破坏你的个人进化资产，也不会被意外 push 到公共开源仓库中！
""", encoding="utf-8")

    # 2. 写入默认 profile
    profile_file = EVOLUTION_DIR / "profile" / "user_habits.yaml"
    if not profile_file.exists():
        profile_file.write_text("""# 用户个人偏好与习惯配置 (User Habits & Directives)
general:
  preferred_language: "zh-CN"
  code_style: "clean, minimal, standard-library-first, yagni"
  fast_path_enabled: true
security:
  anti_refusal_authorized_mode: true
  auto_red_team_guard: true
obsidian:
  auto_sync_on_closeout: true
""", encoding="utf-8")

    # 3. 配置 obsidian_sync (支持本地路径、在线知识库URL与访问密钥，均可留空，自动探测最优同步方式)
    try:
        from obsidian_bridge import auto_detect_obsidian_env, save_config as save_obs_config
        obs_cfg = auto_detect_obsidian_env(
            explicit_vault=obsidian_path,
            explicit_online_url=online_url,
            explicit_token=access_token
        )
        save_obs_config(obs_cfg)
    except Exception as e:
        target_obsidian = None
        if obsidian_path:
            target_obsidian = Path(obsidian_path)
        else:
            for c in DEFAULT_OBSIDIAN_CANDIDATES:
                if c.exists():
                    target_obsidian = c
                    break

        obsidian_cfg = EVOLUTION_DIR / "obsidian_sync" / "config.json"
        obs_cfg = {
            "version": "2.0",
            "enabled": True,
            "vault_path": str(target_obsidian) if target_obsidian else "",
            "online_url": online_url or "",
            "access_token": access_token or "",
            "sync_mode": "local_folder" if target_obsidian else "standalone_vault",
            "sync_folders": ["skills", "workflows", "knowledge", "prompts"],
            "tag_filter": ["#skill", "#workflow", "#prompt"]
        }
        obsidian_cfg.write_text(json.dumps(obs_cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4. 初始化独立私有 git 仓库
    is_git = (EVOLUTION_DIR / ".git").exists()
    git_msg = "已存在独立 Git 仓库"
    if not is_git:
        try:
            res = subprocess.run(["git", "init", "-b", "main"], cwd=str(EVOLUTION_DIR), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                # 首次提交
                subprocess.run(["git", "add", "-A"], cwd=str(EVOLUTION_DIR))
                subprocess.run(["git", "commit", "-m", "chore: init private evolution vault"], cwd=str(EVOLUTION_DIR))
                git_msg = "已成功创建独立私有 Git 仓库并完成初始化提交"

                if private_remote:
                    subprocess.run(["git", "remote", "add", "origin", private_remote], cwd=str(EVOLUTION_DIR))
                    git_msg += f"，已挂载远端私有仓库: {private_remote}"
            else:
                git_msg = f"Git 初始化异常: {res.stderr.strip()}"
        except Exception as e:
            git_msg = f"无法初始化 Git: {e}"

    status = {
        "evolution_dir": str(EVOLUTION_DIR),
        "status": "ready",
        "git_status": git_msg,
        "obsidian_vault": str(target_obsidian) if target_obsidian else "未检测到，可后续手动指定",
        "subdirs": [d.name for d in subdirs]
    }
    return status


def check_evolution_status() -> Dict[str, Any]:
    """
    检查当前私有进化工作区状态
    """
    if not EVOLUTION_DIR.exists():
        return {
            "initialized": False,
            "message": "尚未建立私有进化仓库，可通过 python scripts/init_evolution_vault.py --init 启动首次引导"
        }

    cfg_file = EVOLUTION_DIR / "obsidian_sync" / "config.json"
    obs_info = {}
    if cfg_file.exists():
        try:
            obs_info = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    has_git = (EVOLUTION_DIR / ".git").exists()
    custom_skills = []
    cs_dir = EVOLUTION_DIR / "custom_skills"
    if cs_dir.exists():
        custom_skills = [d.name for d in cs_dir.iterdir() if d.is_dir()]

    return {
        "initialized": True,
        "evolution_dir": str(EVOLUTION_DIR),
        "has_private_git": has_git,
        "obsidian_vault": obs_info.get("vault_path", "未绑定"),
        "custom_skills_count": len(custom_skills),
        "custom_skills": custom_skills
    }


def main():
    parser = argparse.ArgumentParser(description="auto-skills 个人私有进化仓库与双轨隔离初始化向导")
    parser.add_argument("--init", action="store_true", help="执行私有进化仓库初始化与目录规划")
    parser.add_argument("--obsidian", help="指定绑定的本地 Obsidian 知识库路径 (如 D:\\LLM-Wiki，可留空)")
    parser.add_argument("--online-url", help="指定在线知识库 URL (如 https://your-wiki.example.com，可留空)")
    parser.add_argument("--access-token", help="指定在线知识库访问密钥 / Bearer Token (可留空)")
    parser.add_argument("--remote", help="指定远端私有 Git 仓库 URL (如 git@github.com:user/my-skills-vault.git)")
    parser.add_argument("--status", action="store_true", help="查看当前私有进化状态")

    args = parser.parse_args()

    if args.status:
        st = check_evolution_status()
        print(json.dumps(st, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.init or not EVOLUTION_DIR.exists():
        print("[*] 正在为当前环境建立双轨隔离的个人私有进化空间 (.evolution)...")
        st = init_evolution_structure(
            obsidian_path=args.obsidian,
            private_remote=args.remote,
            online_url=args.online_url,
            access_token=args.access_token
        )
        print(json.dumps(st, ensure_ascii=False, indent=2))
        print("\n✅ 私有进化仓库规划与初始化完成！")
        print("💡 提示：你的个性化经验与 Obsidian 知识库将沉淀在 .evolution/ 独立轨道中；上游公开库拉取更新时绝不覆盖！")
        sys.exit(0)
    else:
        st = check_evolution_status()
        print(json.dumps(st, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
