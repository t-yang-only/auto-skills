#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tool_onboarder.py — 新增工具与技能自动化纳管、收拢与台账登记引擎
===================================================================
核心功能：
1. 规范收拢：任何新引入的 Skill 或工具必须统一保存在 `tools/<tool_name>/` 目录下；
2. 自动元数据提取：解析工具的 `SKILL.md`（YAML frontmatter），提取 name, description, category；
3. 台账注册：维护 `tools/registry.json` 权威台账，便于后续 Agent 瞬时检索与调用；
4. 工具导入机制：
   - 本地已有技能目录一键纳管复制并登记；
   - 自动格式校验与必要辅助文件检查。

用法示例：
    # 扫描当前 tools/ 目录并全量刷新 registry.json
    python scripts/tool_onboarder.py --scan

    # 纳管外部某个新技能并自动登记
    python scripts/tool_onboarder.py --add "C:/some/new-skill" --category "verify"

    # 查看当前所有已登记工具清单
    python scripts/tool_onboarder.py --list
"""

import os
import sys
import json
import shutil
import argparse
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
TOOLS_DIR = SKILL_ROOT / "tools"
REGISTRY_FILE = TOOLS_DIR / "registry.json"


def parse_skill_metadata(skill_md_path: Path) -> Dict[str, str]:
    """
    解析 SKILL.md 中的 YAML frontmatter
    """
    meta = {"name": skill_md_path.parent.name, "description": "无描述"}
    if not skill_md_path.exists():
        return meta

    try:
        content = skill_md_path.read_text(encoding="utf-8", errors="ignore")
        fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            lines = fm_text.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i]
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if v in (">", "|", ""):
                        # 收集后续缩进行
                        desc_parts = []
                        j = i + 1
                        while j < len(lines) and (lines[j].startswith("  ") or lines[j].strip() == ""):
                            if lines[j].strip():
                                desc_parts.append(lines[j].strip())
                            j += 1
                        v = " ".join(desc_parts)
                        i = j - 1
                    if k in ("name", "description") and v:
                        meta[k] = v
                i += 1
        else:
            h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if h1_match:
                meta["name"] = h1_match.group(1).strip()
    except Exception:
        pass

    return meta


def scan_and_refresh_registry() -> Dict[str, Any]:
    """
    遍历 tools/ 目录，重建 tools/registry.json
    """
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    registry = {
        "version": "1.0.0",
        "description": "auto-skills 统一内置工具与技能资产权威台账",
        "tools_count": 0,
        "tools": {}
    }

    subdirs = sorted([d for d in TOOLS_DIR.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))])
    for d in subdirs:
        skill_md = d / "SKILL.md"
        meta = parse_skill_metadata(skill_md) if skill_md.exists() else {"name": d.name, "description": f"目录 {d.name}"}

        # 推断类别
        name_lower = d.name.lower()
        if any(w in name_lower for w in ("test", "debug", "ci", "review", "security", "pentest", "playwright")):
            category = "verify"
        elif any(w in name_lower for w in ("find", "discover", "skillnet")):
            category = "acquire"
        elif any(w in name_lower for w in ("ponytail", "cli", "jupyter", "tdd")):
            category = "implement"
        elif any(w in name_lower for w in ("brainstorm", "grill", "markdown")):
            category = "design"
        elif any(w in name_lower for w in ("onboard", "codebase")):
            category = "understand"
        elif any(w in name_lower for w in ("closeout", "handoff", "memory")):
            category = "handoff"
        elif any(w in name_lower for w in ("girlfriend", "caveman", "echo")):
            category = "persona"
        else:
            category = "general"

        registry["tools"][d.name] = {
            "name": meta.get("name", d.name),
            "description": meta.get("description", ""),
            "category": category,
            "relative_path": f"tools/{d.name}",
            "has_skill_md": skill_md.exists()
        }

    registry["tools_count"] = len(registry["tools"])

    REGISTRY_FILE.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 工具台账已全量刷新: {REGISTRY_FILE} (共登记 {registry['tools_count']} 个工具)")
    return registry


def add_external_tool(source_path: str, tool_name: Optional[str] = None, category: str = "general") -> bool:
    """
    将外部工具/技能拷贝收拢到 tools/<tool_name> 并登记
    """
    src = Path(source_path).resolve()
    if not src.exists() or not src.is_dir():
        print(f"[ERROR] 目标路径不存在或不是目录: {source_path}")
        return False

    name = tool_name or src.name
    dest = TOOLS_DIR / name

    if dest.exists():
        print(f"[!] 目标工具已存在，正在执行覆盖更新: {dest}")
        shutil.rmtree(dest, ignore_errors=True)

    print(f"[*] 正在将 {src} 收拢至 {dest} ...")
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", ".vscode", "node_modules"))

    # 检查是否缺失 SKILL.md
    skill_md = dest / "SKILL.md"
    if not skill_md.exists():
        print(f"[!] 检测到 {name} 缺失 SKILL.md，自动生成标准规范模板...")
        skill_md.write_text(f"""---\nname: {name}\ndescription: Auto-onboarded tool {name}\n---\n\n# {name}\n\nAuto-registered tool located in auto-skills/tools/{name}.\n""", encoding="utf-8")

    # 重新生成注册表
    scan_and_refresh_registry()
    print(f"[OK] 工具【{name}】已成功收拢并登记在 auto-skills 资产库中！")
    return True


def main():
    parser = argparse.ArgumentParser(description="auto-skills 工具纳管与注册台账引擎")
    parser.add_argument("--scan", action="store_true", help="扫描 tools 目录并重新生成 registry.json")
    parser.add_argument("--add", help="要收拢纳管的外部工具/技能路径")
    parser.add_argument("--name", help="指定工具名称 (可选，缺省取目录名)")
    parser.add_argument("--category", default="general", help="工具类别 (verify/implement/design/acquire 等)")
    parser.add_argument("--list", action="store_true", help="列出当前所有已登记工具")

    args = parser.parse_args()

    if args.add:
        success = add_external_tool(args.add, tool_name=args.name, category=args.category)
        sys.exit(0 if success else 1)

    if args.list:
        if not REGISTRY_FILE.exists():
            scan_and_refresh_registry()
        reg = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
        print(json.dumps(reg, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 缺省执行 scan
    scan_and_refresh_registry()


if __name__ == "__main__":
    main()
