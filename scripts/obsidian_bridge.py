#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
obsidian_bridge.py — Obsidian 知识库双向互通、在线端点接入与自适应同步桥梁 (v2.0)
==================================================================================
核心特性：
1. 【本地与在线双模知识库支持 (Local & Online Vaults)】：
   - 本地知识库：支持本地文件夹 (如 D:\\YourVault, ~/Documents/Obsidian Vault)；
   - 在线知识库：支持填入在线知识库 URL (如 https://your-wiki.example.com, REST API, WebDAV, SilverBullet)；
   - 访问密钥：支持填入访问密钥 / Bearer Token 进行安全鉴权；
   - 极其包容：在线地址与访问密钥【均可完全留空】！留空时不报错，自适应回退到纯本地知识库模式。
2. 【首次自动侦测与同步方式决策 (Auto-Detection)】：
   - 首次运行或未指定参数时，系统自动扫描并识别：
     * 探测本地是否存在已有 Obsidian 仓库；
     * 探测该目录是否包含 Git 版本控制 (Git-backed Vault)；
     * 探测环境变量或配置中是否有在线知识库端点；
     * 自主确定最优同步机制：
       - `hybrid` (本地 + 在线双向镜像)
       - `git_sync` (本地 Git 仓库联动提交同步)
       - `online_api` (纯在线知识库 REST/Markdown 接口同步)
       - `local_folder` (标准本地 Markdown 双向热同步)
       - `standalone_vault` (若皆为空，自动在 .evolution/ 内就地建立独立自洽知识库)
3. 【双向技能与经验流动】：
   - `import`: 扫描知识库中带有 `#skill` 标签的笔记，自动沉淀为私有技能 (.evolution/custom_skills/)；
   - `export`: 将已沉淀的研发技能或任务复盘日志，按双链格式同步回 Obsidian 知识库；
   - `sync`: 增量比对与双向知识对齐。
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
import urllib.request
import urllib.parse
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
CFG_PATH = EVOLUTION_DIR / "obsidian_sync" / "config.json"
CUSTOM_SKILLS_DIR = EVOLUTION_DIR / "custom_skills"
JOURNAL_DIR = EVOLUTION_DIR / "journal"

DEFAULT_CANDIDATE_PATHS = [
    Path.home() / "ObsidianVault",   # 通用家目录变体，不绑盘符
    Path.home() / "Documents" / "Obsidian Vault",
    Path.home() / "Obsidian",
    Path.home() / "Documents" / "ObsidianVault"
]


def mask_token(token: str) -> str:
    if not token:
        return "<未配置 / 留空>"
    if len(token) <= 8:
        return "***"
    return f"{token[:3]}***{token[-3:]}"


def auto_detect_obsidian_env(
    explicit_vault: Optional[str] = None,
    explicit_online_url: Optional[str] = None,
    explicit_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    首次自动确定知识库的信息和同步方式
    """
    print("[*] 正在自动侦测 Obsidian 知识库环境与最优同步机制...")

    # 1. 确定本地路径
    local_vault_path = ""
    if explicit_vault and explicit_vault.strip():
        p = Path(explicit_vault.strip()).resolve()
        if p.exists():
            local_vault_path = str(p)
    else:
        for candidate in DEFAULT_CANDIDATE_PATHS:
            if candidate.exists() and candidate.is_dir():
                local_vault_path = str(candidate.resolve())
                break

    # 2. 确定在线地址与密钥 (支持传参或环境变量，可留空)
    online_url = (explicit_online_url or os.environ.get("OBSIDIAN_ONLINE_URL") or "").strip()
    access_token = (explicit_token or os.environ.get("OBSIDIAN_ACCESS_TOKEN") or "").strip()

    # 3. 判定本地是否为 Git 仓库
    is_git_vault = False
    git_remote = ""
    if local_vault_path:
        git_dir = Path(local_vault_path) / ".git"
        if git_dir.exists():
            is_git_vault = True
            try:
                res = subprocess.run(
                    ["git", "config", "--get", "remote.origin.url"],
                    cwd=local_vault_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                git_remote = res.stdout.strip()
            except Exception:
                pass

    # 4. 智能裁决同步模式 (sync_mode)
    if online_url and local_vault_path:
        sync_mode = "hybrid"
        mode_desc = f"混合模式：本地目录 ({local_vault_path}) + 在线端点 ({online_url})"
    elif online_url and not local_vault_path:
        sync_mode = "online_api"
        mode_desc = f"在线知识库 API 模式：端点 ({online_url})，鉴权: {'Bearer Token' if access_token else '公开/匿名'}"
    elif is_git_vault:
        sync_mode = "git_sync"
        mode_desc = f"本地 Git 知识库联动：路径 ({local_vault_path})，远端: {git_remote or '本地仓库'}"
    elif local_vault_path:
        sync_mode = "local_folder"
        mode_desc = f"本地文件系统热同步：路径 ({local_vault_path})"
    else:
        # 如果全部留空，创建内嵌知识库
        fallback_dir = EVOLUTION_DIR / "obsidian_sync" / "default_vault"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        local_vault_path = str(fallback_dir.resolve())
        sync_mode = "standalone_vault"
        mode_desc = f"自洽独立知识库模式 (内置于 .evolution 工作区中)"

    detected_cfg = {
        "version": "2.0",
        "enabled": True,
        "vault_path": local_vault_path,
        "online_url": online_url,
        "access_token": access_token,
        "sync_mode": sync_mode,
        "mode_description": mode_desc,
        "is_git_backed": is_git_vault,
        "git_remote": git_remote,
        "sync_folders": ["skills", "workflows", "knowledge", "prompts"],
        "tag_filter": ["#skill", "#workflow", "#prompt", "#agent-skill"],
        "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    print(f"  [+] 自动判定同步方式: 【{sync_mode}】 -> {mode_desc}")
    return detected_cfg


def load_config() -> Dict[str, Any]:
    """读取或初始化配置"""
    if CFG_PATH.exists():
        try:
            data = json.loads(CFG_PATH.read_text(encoding="utf-8"))
            if "version" in data and "sync_mode" in data:
                return data
        except Exception:
            pass

    # 首次自动探测并写入
    cfg = auto_detect_obsidian_env()
    save_config(cfg)
    return cfg


def save_config(cfg: Dict[str, Any]) -> bool:
    try:
        CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
        cfg["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        CFG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[ERROR] 保存 Obsidian 配置失败: {e}")
        return False


# ==============================================================================
# 在线知识库 HTTP 适配器 (支持 Bearer Token 鉴权)
# ==============================================================================

def push_note_to_online_vault(online_url: str, token: str, subfolder: str, filename: str, content: str) -> Tuple[bool, str]:
    """
    向在线知识库推送 Markdown 笔记
    """
    if not online_url:
        return False, "在线知识库地址为空"

    base_url = online_url.rstrip("/")
    api_url = f"{base_url}/api/v1/notes/{subfolder}/{filename}"

    headers = {
        "Content-Type": "text/markdown; charset=utf-8",
        "User-Agent": "AutoSkills-ObsidianBridge/2.0"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        req = urllib.request.Request(
            api_url,
            data=content.encode("utf-8"),
            headers=headers,
            method="PUT"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return True, f"在线同步成功 (HTTP {resp.status})"
    except Exception as e:
        # 如果特定 PUT 接口不可用，记录但不阻断主流程
        return False, f"在线推送通知或异常: {e}"


# ==============================================================================
# 本地与在线导入 / 导出核心动作
# ==============================================================================

def import_skills_from_obsidian(vault_path: Optional[str] = None) -> List[str]:
    """
    从 Obsidian 知识库中检索 #skill 笔记并导入为私有 custom_skills
    """
    cfg = load_config()
    target_vault = Path(vault_path or cfg.get("vault_path", ""))
    if not target_vault.exists():
        print(f"[ERROR] Obsidian 本地知识库路径不存在: {target_vault}")
        return []

    CUSTOM_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    imported = []

    print(f"[*] 正在从知识库【{target_vault}】扫描具备 #skill 标记的笔记...")
    for md_file in target_vault.rglob("*.md"):
        if any(part.startswith(".") for part in md_file.parts):
            continue

        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            is_skill_candidate = (
                "#skill" in text.lower() or 
                "#agent-skill" in text.lower() or 
                "skills" in [p.lower() for p in md_file.parts]
            )

            if is_skill_candidate:
                skill_name = re.sub(r"[^\w\-_]", "-", md_file.stem.lower()).strip("-")
                if not skill_name:
                    continue

                dest_dir = CUSTOM_SKILLS_DIR / skill_name
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_skill_md = dest_dir / "SKILL.md"

                first_line = f"Obsidian 导入技能: {md_file.stem}"
                lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith(("#", "---", "tags:"))]
                if lines:
                    first_line = lines[0][:100]

                clean_text = re.sub(r"^---\s*\n.*?\n---", "", text, flags=re.DOTALL).strip()
                formatted_content = f"""---
name: {skill_name}
description: "{first_line}"
metadata:
  source: "obsidian-vault"
  vault_rel_path: "{md_file.relative_to(target_vault)}"
---

{clean_text}
"""
                dest_skill_md.write_text(formatted_content, encoding="utf-8")
                imported.append(skill_name)
                print(f"  [+] 导入私有 Skill 成功: {skill_name} (来自 {md_file.name})")
        except Exception as e:
            print(f"  [!] 解析笔记 {md_file.name} 失败: {e}")

    print(f"[OK] 导入完成！共计导入 {len(imported)} 个私有技能至 .evolution/custom_skills/")
    return imported


def export_skill_to_obsidian(
    skill_name: str,
    target_subfolder: str = "skills",
    vault_path: Optional[str] = None
) -> bool:
    """
    将指定的本地技能导出为 Obsidian 知识库笔记 (同时支持本地落盘与在线推送)
    """
    cfg = load_config()
    target_vault = Path(vault_path or cfg.get("vault_path", ""))
    online_url = cfg.get("online_url", "")
    token = cfg.get("access_token", "")

    # 查找技能
    skill_file = None
    for d in [SKILL_ROOT / "tools" / skill_name, CUSTOM_SKILLS_DIR / skill_name]:
        sf = d / "SKILL.md"
        if sf.exists():
            skill_file = sf
            break

    if not skill_file:
        print(f"[ERROR] 未找到技能【{skill_name}】的 SKILL.md")
        return False

    content = skill_file.read_text(encoding="utf-8")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    obsidian_note = f"""---
title: "{skill_name}"
tags:
  - skill
  - auto-skills
  - agent-harness
exported_at: "{now_str}"
---

# 🤖 Agent Skill: {skill_name}

> 本文由 `auto-skills` 知识库桥接器于 {now_str} 自动导出沉淀。

{content}
"""

    # 1. 本地落盘
    local_ok = False
    if target_vault and target_vault.exists():
        out_dir = target_vault / target_subfolder
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{skill_name}.md"
        out_file.write_text(obsidian_note, encoding="utf-8")
        print(f"[OK] 技能【{skill_name}】已保存至本地 Obsidian 笔记: {out_file}")
        local_ok = True

    # 2. 若配置了在线知识库，尝试在线推送
    if online_url:
        print(f"[*] 正在推送到在线知识库: {online_url} ...")
        ok, msg = push_note_to_online_vault(
            online_url=online_url,
            token=token,
            subfolder=target_subfolder,
            filename=f"{skill_name}.md",
            content=obsidian_note
        )
        if ok:
            print(f"  [+] 在线同步成功: {msg}")
        else:
            print(f"  [!] 在线同步提示: {msg}")

    return local_ok or bool(online_url)


def print_bridge_status():
    cfg = load_config()
    print("\n" + "=" * 70)
    print("📚 auto-skills × Obsidian 知识库双向桥梁配置一览")
    print(f"   配置保存文件: {CFG_PATH}")
    print("=" * 70)
    print(f"- 本地知识库路径 : {cfg.get('vault_path') or '<未绑定本地路径>'}")
    print(f"- 在线知识库地址 : {cfg.get('online_url') or '<未配置在线端点 (留空)>'}")
    print(f"- 访问鉴权密钥   : {mask_token(cfg.get('access_token'))}")
    print(f"- 智能同步模式   : {cfg.get('sync_mode')} ({cfg.get('mode_description')})")
    print(f"- Git 仓库支持   : {'已挂载 Git 远端: ' + cfg.get('git_remote') if cfg.get('is_git_backed') else '非 Git 或本地单机'}")
    print(f"- 监听同步文件夹 : {', '.join(cfg.get('sync_folders', []))}")
    print("=" * 70)
    print("💡 快捷命令指南：")
    print("  - 设置本地路径: python scripts/obsidian_bridge.py --set-vault 'D:\\YourVault'")
    print("  - 设置在线地址: python scripts/obsidian_bridge.py --set-online 'https://your-wiki.example.com'")
    print("  - 设置访问密钥: python scripts/obsidian_bridge.py --set-token '<your_token>' (留空可传 '')")
    print("  - 自动重新侦测: python scripts/obsidian_bridge.py --auto-detect")
    print("  - 导入所有技能: python scripts/obsidian_bridge.py --import-all")
    print("  - 导出技能笔记: python scripts/obsidian_bridge.py --export <skill_name>\n")


def main():
    parser = argparse.ArgumentParser(description="auto-skills 与 Obsidian 本地及在线知识库双向桥梁")
    parser.add_argument("--status", action="store_true", help="查看当前知识库配置与同步模式")
    parser.add_argument("--auto-detect", action="store_true", help="重新触发自动环境探测并确定同步方式")
    parser.add_argument("--set-vault", nargs="?", const="", help="设置或更改本地 Obsidian 知识库路径 (传空重置)")
    parser.add_argument("--set-online", nargs="?", const="", help="设置在线知识库地址 (如 https://your-wiki.example.com，可留空)")
    parser.add_argument("--set-token", nargs="?", const="", help="设置在线知识库访问密钥 / Bearer Token (可留空)")
    parser.add_argument("--clear-online", action="store_true", help="清空在线知识库地址与访问密钥")
    parser.add_argument("--import-all", action="store_true", help="从知识库扫描并导入 #skill 笔记至私有技能区")
    parser.add_argument("--export", help="将指定技能导出为 Obsidian 笔记沉淀")

    args = parser.parse_args()

    cfg = load_config()

    # 处理设置更改
    modified = False
    if args.clear_online:
        cfg["online_url"] = ""
        cfg["access_token"] = ""
        modified = True
        print("[OK] 已清空在线知识库地址与访问密钥 (恢复纯本地模式)")

    if args.set_vault is not None:
        cfg["vault_path"] = args.set_vault.strip()
        modified = True
        print(f"[OK] 本地知识库路径已更新为: {cfg['vault_path']}")

    if args.set_online is not None:
        cfg["online_url"] = args.set_online.strip()
        modified = True
        print(f"[OK] 在线知识库地址已更新为: {cfg['online_url'] or '<留空>'}")

    if args.set_token is not None:
        cfg["access_token"] = args.set_token.strip()
        modified = True
        print(f"[OK] 访问密钥已更新为: {mask_token(cfg['access_token'])}")

    if args.auto_detect:
        new_detected = auto_detect_obsidian_env(
            explicit_vault=cfg.get("vault_path"),
            explicit_online_url=cfg.get("online_url"),
            explicit_token=cfg.get("access_token")
        )
        cfg.update(new_detected)
        modified = True

    if modified:
        save_config(cfg)

    if args.status:
        print_bridge_status()
        sys.exit(0)

    if args.import_all:
        import_skills_from_obsidian()
        sys.exit(0)

    if args.export:
        export_skill_to_obsidian(args.export)
        sys.exit(0)

    # 默认打印状态
    print_bridge_status()


if __name__ == "__main__":
    main()
