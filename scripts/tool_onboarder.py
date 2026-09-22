#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tool_onboarder.py — 新增工具与技能自动化纳管、双轨归类与私有 Git 同步引擎 (v3.0)
================================================================================
核心功能：
1. 【双轨归类收拢】：
   - `--target custom` (默认)：用户自行安装或动态生成的个性化技能，统一收拢到
     `.evolution/custom_skills/<tool_name>/` 专属私有目录下，绝不上报公开仓库；
   - `--target public`：官方或项目共享工具，收拢到 `tools/<tool_name>/` 目录下；
2. 【自适应元数据萃取】：解析技能的 `SKILL.md`（YAML frontmatter），自动萃取名称、功能说明与类别；
3. 【双轨台账维护】：
   - 公共工具维护 `tools/registry.json`
   - 私有自定义工具维护 `.evolution/custom_skills/registry.json`
4. 【自动沉淀与私有 Git 联动推送 (Private Git Sync)】：
   - 纳入私有技能后，自动调用 `sync_evolution.py` 执行 Git commit；
   - 若用户配置了私有远端 Git 仓库，自动 push 到私有云端库，实现多机协同进化。

用法示例：
    # 1. 纳管一个自安装或动态生成的技能至个人私有库，并自动触发私有 Git 提交推送
    python scripts/tool_onboarder.py --add "C:/path/to/my-agent-skill"

    # 2. 扫描所有工具并刷新台账 (同时刷新公共与私有)
    python scripts/tool_onboarder.py --scan

    # 3. 查看当前已登记的工具与私有技能清单
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
PUBLIC_TOOLS_DIR = SKILL_ROOT / "tools"
PUBLIC_REGISTRY_FILE = PUBLIC_TOOLS_DIR / "registry.json"

EVOLUTION_DIR = SKILL_ROOT / ".evolution"
CUSTOM_SKILLS_DIR = EVOLUTION_DIR / "custom_skills"
CUSTOM_REGISTRY_FILE = CUSTOM_SKILLS_DIR / "registry.json"


SKILL_TEMPLATE = Path(__file__).resolve().parent.parent / "template" / "SKILL.md"


def _write_skill_skeleton(skill_md_path: Path, name: str, source: Path, scope_desc: str) -> None:
    """按 template/SKILL.md 生成待完善骨架。

    绝不写入 "Auto-onboarded skill <name>" 这类看似完成、实则无信息的占位描述——
    description 是 agent 判断「何时加载本技能」的唯一依据，占位描述等于让技能不可被发现。
    """
    if SKILL_TEMPLATE.exists():
        body = SKILL_TEMPLATE.read_text(encoding="utf-8")
        body = (body.replace("{{NAME}}", name)
                    .replace("{{SOURCE}}", str(source))
                    .replace("{{SCOPE}}", scope_desc))
    else:
        body = (
            "---\nname: %s\n"
            "description: >-\n  TODO（必填）：说明本技能做什么、何时使用。当前为自动纳管占位。\n"
            "---\n\n# %s\n\n> 自动纳管于 %s，正文待完善。\n" % (name, name, scope_desc)
        )
    skill_md_path.write_text(body, encoding="utf-8")


def parse_skill_metadata(skill_md_path: Path) -> Dict[str, str]:
    """
    解析 SKILL.md 中的 YAML frontmatter
    """
    meta = {"name": skill_md_path.parent.name, "description": "无描述"}
    if not skill_md_path.exists():
        return meta

    try:
        content = skill_md_path.read_text(encoding="utf-8-sig", errors="ignore")  # utf-8-sig 自动剥离 BOM
        fm_match = re.match(r"^\ufeff?---\s*\n(.*?)\n---", content, re.DOTALL)
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


def infer_category(name: str) -> str:
    name_lower = name.lower()
    if any(w in name_lower for w in ("test", "debug", "ci", "review", "security", "pentest", "playwright", "verif", "audit", "diagnos")):
        return "verify"
    elif any(w in name_lower for w in ("find", "discover", "skillnet")):
        return "acquire"
    elif any(w in name_lower for w in ("ponytail", "cli", "jupyter", "tdd", "ppt", "slide")):
        return "implement"
    elif any(w in name_lower for w in ("brainstorm", "grill", "markdown")):
        return "design"
    elif any(w in name_lower for w in ("onboard", "codebase")):
        return "understand"
    elif any(w in name_lower for w in ("closeout", "handoff", "memory", "nm-")):
        return "handoff"
    elif any(w in name_lower for w in ("girlfriend", "caveman", "echo")):
        return "persona"
    return "general"


def scan_dir(base_dir: Path, registry_file: Path, scope_name: str) -> Dict[str, Any]:
    base_dir.mkdir(parents=True, exist_ok=True)
    registry = {
        "version": "2.0.0",
        "scope": scope_name,
        "tools_count": 0,
        "tools": {}
    }

    subdirs = sorted([d for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))])
    for d in subdirs:
        skill_md = d / "SKILL.md"
        meta = parse_skill_metadata(skill_md) if skill_md.exists() else {"name": d.name, "description": f"目录 {d.name}"}
        cat = infer_category(d.name)

        registry["tools"][d.name] = {
            "name": meta.get("name", d.name),
            "description": meta.get("description", ""),
            "category": cat,
            "path": d.relative_to(SKILL_ROOT).as_posix() if SKILL_ROOT in d.parents else d.name,
            "has_skill_md": skill_md.exists()
        }

    registry["tools_count"] = len(registry["tools"])
    registry_file.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return registry


def scan_and_refresh_all() -> Dict[str, Any]:
    """全量刷新公共工具与私有技能台账"""
    pub = scan_dir(PUBLIC_TOOLS_DIR, PUBLIC_REGISTRY_FILE, "public_tools")
    priv = scan_dir(CUSTOM_SKILLS_DIR, CUSTOM_REGISTRY_FILE, "custom_skills")
    print(f"[OK] 工具台账已刷新: 公共工具 {pub['tools_count']} 个，私有技能 {priv['tools_count']} 个")
    return {"public": pub, "custom": priv}


def add_external_tool(
    source_path: str,
    tool_name: Optional[str] = None,
    category: str = "general",
    target: str = "custom",
    auto_push_private: bool = True
) -> bool:
    """
    将外部工具/自安装技能拷贝收拢到对应文件夹 (默认 custom 存入 .evolution/custom_skills/) 并自动同步私有 Git
    """
    src = Path(source_path).resolve()
    if not src.exists() or not src.is_dir():
        print(f"[ERROR] 目标路径不存在或不是目录: {source_path}")
        return False

    name = tool_name or src.name
    if target == "public":
        target_dir = PUBLIC_TOOLS_DIR / name
        scope_desc = "公共工具区 (tools/)"
    else:
        CUSTOM_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        target_dir = CUSTOM_SKILLS_DIR / name
        scope_desc = "用户私有进化区 (.evolution/custom_skills/)"

    if target_dir.exists():
        print(f"[!] 目标已存在，正在覆盖更新: {target_dir}")
        shutil.rmtree(target_dir, ignore_errors=True)

    print(f"[*] 正在将【{name}】收拢至 {scope_desc}: {target_dir} ...")
    shutil.copytree(src, target_dir, ignore=shutil.ignore_patterns(".git", "__pycache__", ".vscode", "node_modules"))

    # 检查 SKILL.md
    skill_md = target_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"[!] 检测到缺失 SKILL.md，按 template/SKILL.md 生成待完善骨架...")
        _write_skill_skeleton(skill_md, name, src, scope_desc)

    # 刷新台账
    scan_and_refresh_all()
    print(f"[OK] 技能【{name}】已成功归类并登记入库！")

    # 若为用户私有技能，自动触发个人私有 Git 仓库提交与推送！
    if target == "custom" and auto_push_private:
        print("[*] 正在触发用户个人私有进化仓库自动同步与推送...")
        try:
            from sync_evolution import sync_private_evolution
            sync_private_evolution(message=f"feat: onboard custom skill [{name}]", notify=True)
        except Exception as e:
            print(f"[!] 私有 Git 同步提示: {e}")

    return True


def main():
    parser = argparse.ArgumentParser(description="auto-skills 新增工具纳管、双轨归类与私有 Git 自动同步引擎 (v3.0)")
    parser.add_argument("--scan", action="store_true", help="扫描公共 tools/ 与私有 custom_skills/ 重新生成台账")
    parser.add_argument("--add", help="要收拢纳管的外部工具/技能路径")
    parser.add_argument("--name", help="指定技能名称 (可选，缺省取目录名)")
    parser.add_argument("--category", default="general", help="技能类别 (verify/implement/design/acquire 等)")
    parser.add_argument("--target", choices=["custom", "public"], default="custom", help="归类目标：custom=用户私有进化区(默认)，public=公共内置区")
    parser.add_argument("--no-push", action="store_true", help="私有技能纳管后不自动触发私有 Git 推送")
    parser.add_argument("--list", action="store_true", help="列出当前所有已登记工具与私有技能")

    args = parser.parse_args()

    if args.add:
        success = add_external_tool(
            source_path=args.add,
            tool_name=args.name,
            category=args.category,
            target=args.target,
            auto_push_private=not args.no_push
        )
        sys.exit(0 if success else 1)

    if args.list:
        if not PUBLIC_REGISTRY_FILE.exists() or not CUSTOM_REGISTRY_FILE.exists():
            scan_and_refresh_all()
        pub_data = json.loads(PUBLIC_REGISTRY_FILE.read_text(encoding="utf-8")) if PUBLIC_REGISTRY_FILE.exists() else {}
        priv_data = json.loads(CUSTOM_REGISTRY_FILE.read_text(encoding="utf-8")) if CUSTOM_REGISTRY_FILE.exists() else {}
        combined = {
            "public_tools": pub_data.get("tools", {}),
            "custom_private_skills": priv_data.get("tools", {})
        }
        print(json.dumps(combined, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 缺省执行 scan
    scan_and_refresh_all()


if __name__ == "__main__":
    main()
