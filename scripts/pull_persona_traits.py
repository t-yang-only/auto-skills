#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pull_persona_traits.py — 从知识库自适应拉取女友人格定义与温情特性的同步模块
============================================================================
功能：
1. 解析要读的知识库位置——**唯一权威来源是 `.evolution/obsidian_sync/config.json`
   的 `vault_path`**（由 `obsidian_bridge.py --set-vault` 写入），其次是几个常见
   目录候选。早期文档曾写“检查配置中的知识库端点”，但配置里的
   `persona.talk_like_girlfriend.kb_source_url_or_path` / `kb_api_token`
   **从来没有被任何代码读过**（全仓与全机范围内零消费者），已于 2026-10-02 删除，
   以免留下“配了却不生效”的假开关；
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


def _cfg_str(key: str, default: str = "") -> str:
    """惰性读配置；读不到返回 default（保持本文件可独立运行）。"""
    try:
        import config_manager
        v = config_manager.get_value(key, default)
        return str(v) if v not in (None, "") else default
    except Exception:
        return default


def _resolve_under_root(rel: str, fallback: Path) -> Path:
    """把配置里的路径解析到技能根下；空值或异常一律用 fallback。"""
    try:
        if rel:
            p = Path(str(rel))
            return p if p.is_absolute() else (SKILL_ROOT / p)
    except Exception:
        pass
    return fallback


# 特性缓存文件。**以前这里是硬编码**，而配置里有
# `persona.talk_like_girlfriend.traits_cache_file` 却没有任何代码读它 ——
# 也就是「在配置里改缓存位置」从来不生效（2026-10-02 接线修掉）。
# 缺省值与原硬编码一致，不填配置的安装行为不变。
TRAITS_FILE = _resolve_under_root(
    _cfg_str("persona.talk_like_girlfriend.traits_cache_file"),
    PROFILE_DIR / "persona_girlfriend.json")
SYNC_CFG = SKILL_ROOT / ".evolution" / "obsidian_sync" / "config.json"

# 知识库路径一律动态解析，绝不硬编码某个人的磁盘布局。
# 顺序：显式传入 > .evolution/obsidian_sync/config.json 的 vault_path > 常见候选目录。
DEFAULT_CANDIDATES = [
    Path.home() / "Documents" / "Obsidian Vault",
    Path.home() / "Obsidian",
    Path.home() / "Documents" / "ObsidianVault",
]


def resolve_kb_path(explicit: str = "") -> Path | None:
    """按 显式传入 > 已保存配置 > 候选目录 的顺序解析本地知识库路径；找不到返回 None。"""
    if explicit:
        return Path(explicit)
    try:
        if SYNC_CFG.exists():
            saved = str(json.loads(SYNC_CFG.read_text(encoding="utf-8")).get("vault_path") or "").strip()
            if saved:
                return Path(saved)
    except Exception:
        pass
    for cand in DEFAULT_CANDIDATES:
        if cand.is_dir():
            return cand
    return None


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
    local_kb = resolve_kb_path(kb_path_or_url)
    if local_kb is None:
        print("[*] 未配置本地知识库路径，本次只使用内置人格基线。")
        print("    设置方法: python scripts/obsidian_bridge.py --set-vault '<你的知识库路径>'")
    elif local_kb.exists() and local_kb.is_dir():
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
    argv = sys.argv[1:]
    # -h/--help 必须**短路**：这个脚本原先把 `--help` 当成"知识库路径"参数，
    # 于是"看一眼用法"会真的跑一次拉取、并**覆写**特性缓存文件。
    # 实测踩过：审计 CLI 时可调用性时，`--help` 触发了真实的拉取。
    # 这与此前修过的「写操作没有标记」是同一类问题：探索不该有副作用。
    if "-h" in argv or "--help" in argv:
        print(
            "pull_persona_traits.py —— 从知识库拉取女友人格特性并沉淀\n"
            "\n"
            "用法：\n"
            "  python pull_persona_traits.py [知识库路径] [令牌]\n"
            "\n"
            "两个参数都可省略。省略时按下列顺序解析知识库位置（详见文件头注释）：\n"
            "  1. 命令行第一个参数\n"
            "  2. `.evolution/obsidian_sync/config.json` 的 vault_path（**权威来源**）\n"
            "  3. 几个常见候选目录\n"
            "\n"
            "产物：`.evolution/profile/persona_girlfriend.json`\n"
            "（路径可由 `persona.talk_like_girlfriend.traits_cache_file` 覆盖）\n"
            "\n"
            "-h/--help 只打印本说明：**不拉取、不写任何文件**。\n")
        sys.exit(0)
    kb = argv[0] if len(argv) > 0 else ""
    tok = argv[1] if len(argv) > 1 else ""
    pull_and_sync_traits(kb, tok)
