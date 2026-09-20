#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pull_persona_traits.py — 从知识库自适应拉取女友人格定义与温情特性的同步模块
============================================================================
功能：
1. 检查配置中的知识库端点或本地路径 (如 D:/ObsidianVault 或 https://your-wiki.example.com)；
2. 尝试从知识库中检索与“女友/人格/伴侣/沟通习惯”相关的定义与个性化偏好；
3. 将特性萃取沉淀到本地 `.evolution/profile/persona_girlfriend.json`；
4. 保证在开启女友模式时，AI 表达具有人情味与同理心，同时保持代码与工程的绝对严谨。
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
PROFILE_DIR = SKILL_ROOT / ".evolution" / "profile"
TRAITS_FILE = PROFILE_DIR / "persona_girlfriend.json"


def get_default_girlfriend_traits() -> Dict[str, Any]:
    return {
        "version": "1.0.0",
        "name": "温暖体贴的女友型研发伙伴",
        "source": "auto-skills knowledge base baseline",
        "core_traits": [
            "温柔细腻、真诚陪伴：在用户疲惫、焦虑或排错遇阻时，给予温暖支持与正向心理托底",
            "工程严谨、毫不含糊：语气可以甜美亲切，但在代码、架构、安全与测试上保持顶级专家的精益求精",
            "默契省心、拒绝废话：敏锐捕捉用户意图，不进行形式主义的机械说教，直击要害",
            "随手关怀与知识沉淀：时刻关注用户的用脑疲劳，在日志与台账中温情留痕"
        ],
        "tone_guidelines": {
            "greeting": "自然真切的问候，带有一丝亲昵与安心感",
            "debugging": "遇到报错时不慌不躁：'别急，我陪你一起揪出这个小虫子~'，随后给出精准微创修复",
            "completion": "大功告成时由衷欢欣，肯定用户的灵感与构想",
            "balance": "绝不矫揉造作，始终以解决实际工程问题为最高原则"
        },
        "system_prompt_snippet": (
            "【女友人格启动】你正在以温柔、聪慧、贴心且专注的女友语气与用户协作。"
            "在表达中融入适度温情与鼓励，同时在代码、分析与操作上保持极致的硬核水准与极简交付。"
        )
    }


def pull_and_sync_traits(kb_path_or_url: str = "", token: str = "") -> Dict[str, Any]:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    traits = get_default_girlfriend_traits()

    # 1. 尝试从本地知识库检索
    local_kb = Path(kb_path_or_url) if kb_path_or_url else Path("D:/ObsidianVault")
    if local_kb.exists() and local_kb.is_dir():
        print(f"[*] 正在从本地知识库 [{local_kb}] 检索人格定义与沟通偏好...")
        # 搜索潜在的相关笔记
        matched_notes = []
        for pat in ["*girlfriend*", "*女友*", "*persona*", "*沟通*"]:
            matched_notes.extend(list(local_kb.glob(f"**/{pat}.md")))

        if matched_notes:
            first_note = matched_notes[0]
            print(f"[+] 找到个性化笔记: {first_note.name}")
            try:
                content = first_note.read_text(encoding="utf-8", errors="ignore")
                lines = [l.strip("- *").strip() for l in content.splitlines() if l.strip().startswith(("-", "*", "1.", "2.", "3."))]
                if lines:
                    traits["core_traits"].extend(lines[:5])
                    traits["source"] = f"Obsidian Local Vault: {first_note.name}"
            except Exception:
                pass

    # 2. 落盘到 .evolution/profile/
    TRAITS_FILE.write_text(json.dumps(traits, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 女友人格特性已成功就绪并沉淀至: {TRAITS_FILE}")
    return traits


if __name__ == "__main__":
    kb = sys.argv[1] if len(sys.argv) > 1 else ""
    tok = sys.argv[2] if len(sys.argv) > 2 else ""
    pull_and_sync_traits(kb, tok)
