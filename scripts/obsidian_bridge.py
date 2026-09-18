#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
obsidian_bridge.py — Obsidian 知识库双向互通与技能进化同步桥梁
==============================================================
功能说明：
1. 【知识库读取与填入 (Import)】：
   - 从绑定的 Obsidian 知识库 (如 D:\\LLM-Wiki) 中读取指定文件夹 (如 skills/, prompts/, workflows/, knowledge/)
   - 将带有 `#skill` 或特定前缀的笔记无缝转化为 auto-skills 的自定义技能 (.evolution/custom_skills/<name>/SKILL.md)
2. 【技能经验导出沉淀至知识库 (Export)】：
   - 将已沉淀的优质工程技能或实战经验以标准 Markdown 形式写入 Obsidian 知识库中；
   - 自动生成符合 Obsidian 双链规范的 [[Wikilinks]] 与标签分类；
3. 【双向增量同步 (Sync)】：
   - 检查 Obsidian 笔记修改时间与本地进化区时间戳，进行双向比对同步；
   - 保护用户隐私：仅在 .evolution/ 与 Obsidian 之间流动，绝不上报公开仓库。
"""

import os
import sys
import json
import shutil
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

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


def load_config() -> Dict[str, Any]:
    if not CFG_PATH.exists():
        return {
            "enabled": False,
            "vault_path": "D:/LLM-Wiki" if Path("D:/LLM-Wiki").exists() else "",
            "sync_folders": ["skills", "workflows", "knowledge"],
            "tag_filter": ["#skill", "#workflow"]
        }
    try:
        return json.loads(CFG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"enabled": False, "vault_path": ""}


def import_skills_from_obsidian(vault_path: Optional[str] = None) -> List[str]:
    """
    从 Obsidian 知识库中检索 #skill 笔记并导入为私有 custom_skills
    """
    cfg = load_config()
    target_vault = Path(vault_path or cfg.get("vault_path", ""))
    if not target_vault.exists():
        print(f"[ERROR] Obsidian 知识库路径不存在: {target_vault}")
        return []

    CUSTOM_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    imported = []

    print(f"[*] 正在扫描 Obsidian 知识库: {target_vault} ...")
    for md_file in target_vault.rglob("*.md"):
        # 排除隐藏目录（如 .obsidian, .git）
        if any(part.startswith(".") for part in md_file.parts):
            continue

        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            # 检查是否有 #skill 标签或路径在 skills 目录下
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

                # 提取描述
                first_line = "Obsidian 导入技能: " + md_file.stem
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
                print(f"  [+] 成功导入笔记为私有 Skill: {skill_name} (来自 {md_file.name})")
        except Exception as e:
            print(f"  [!] 解析笔记 {md_file.name} 失败: {e}")

    print(f"[OK] 导入完成！共计导入 {len(imported)} 个私有技能至 .evolution/custom_skills/")
    return imported


def export_skill_to_obsidian(skill_name: str, target_subfolder: str = "skills", vault_path: Optional[str] = None) -> bool:
    """
    将指定的本地技能导出为 Obsidian 知识库笔记
    """
    cfg = load_config()
    target_vault = Path(vault_path or cfg.get("vault_path", ""))
    if not target_vault.exists():
        print(f"[ERROR] Obsidian 知识库路径不存在: {target_vault}")
        return False

    # 寻找技能：先看 tools/ 再看 custom_skills/
    skill_file = None
    for d in [SKILL_ROOT / "tools" / skill_name, CUSTOM_SKILLS_DIR / skill_name]:
        sf = d / "SKILL.md"
        if sf.exists():
            skill_file = sf
            break

    if not skill_file:
        print(f"[ERROR] 未找到技能【{skill_name}】的 SKILL.md")
        return False

    out_dir = target_vault / target_subfolder
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{skill_name}.md"

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
    out_file.write_text(obsidian_note, encoding="utf-8")
    print(f"[OK] 技能【{skill_name}】已成功沉淀至 Obsidian 笔记: {out_file}")
    return True


def sync_evolution_journal_to_obsidian(vault_path: Optional[str] = None) -> int:
    """
    将 .evolution/journal 中的任务复盘日记同步到 Obsidian 的 journal 目录
    """
    cfg = load_config()
    target_vault = Path(vault_path or cfg.get("vault_path", ""))
    if not target_vault.exists():
        return 0

    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    target_journal_dir = target_vault / "journal"
    target_journal_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for jf in JOURNAL_DIR.glob("*.md"):
        dest = target_journal_dir / jf.name
        shutil.copy2(jf, dest)
        count += 1

    if count > 0:
        print(f"[OK] 已将 {count} 篇进化日志同步至 Obsidian: {target_journal_dir}")
    return count


def main():
    parser = argparse.ArgumentParser(description="auto-skills 与 Obsidian 知识库双向桥梁")
    parser.add_argument("--import-all", action="store_true", help="从 Obsidian 扫描并导入 #skill 笔记")
    parser.add_argument("--export", help="指定要导出至 Obsidian 的 Skill 名称")
    parser.add_argument("--sync-journal", action="store_true", help="将进化复盘日志同步至 Obsidian")
    parser.add_argument("--vault", help="临时覆盖 Obsidian 知识库根目录路径")

    args = parser.parse_args()

    if args.import_all:
        import_skills_from_obsidian(vault_path=args.vault)
        sys.exit(0)

    if args.export:
        export_skill_to_obsidian(args.export, vault_path=args.vault)
        sys.exit(0)

    if args.sync_journal:
        sync_evolution_journal_to_obsidian(vault_path=args.vault)
        sys.exit(0)

    # 缺省打印当前桥接状态
    cfg = load_config()
    print(json.dumps(cfg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
