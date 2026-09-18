#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_router.py — auto-skills 智能化自适应工作流调度引擎 (v2.0 升级版)
====================================================================
核心改进：
1. 【自适应多根路径解析 (Multi-Root Fallback Resolution)】：
   - 彻底终结 missing_members 错误！
   - 优先级 1: 本身内置 tools/<skill>/SKILL.md (100% 独立自洽)
   - 优先级 2: 父级工作区同级目录 ../<skill>/SKILL.md
   - 优先级 3: ~/.codex/skills/<skill>/SKILL.md
   - 优先级 4: ~/.agents/skills/<skill>/SKILL.md
   - 优先级 5: ~/.dsh/skills/<skill>/SKILL.md
   - 优先级 6: ~/.workbuddy-ai/skills/<skill>/SKILL.md
2. 【SDLC 研发全生命周期阶段感知 (Lifecycle Phase Routing)】：
   - clarify (需求澄清与极限施压): using-superpowers -> grill-me / brainstorming
   - design (架构设计与规范对齐): brainstorming -> codebase-onboarding
   - implement (极简高质代码实施): ponytail (支持 lite/full/ultra 档位)
   - acquire (能力供应链补齐): find-skills (即装) / skill-discovery (评估) / skillnet (材料沉淀)
   - manage (多环境工具纳管与修链): skills-manager-cli (skm 联动)
   - handoff (跨 Agent 协作交接与汇报): team-handoff / nm-skills
   - persona (用户指令门控表达层): talk-like-girlfriend (仅显式口令触发)
3. 【冲突仲裁与执行计划拓扑生成】：
   - 输出有序 execution plan，支持 CLI 查看与 JSON 自动化流水线集成。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SELF_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SELF_DIR.parent
INTERNAL_TOOLS = SKILL_ROOT / "tools"

USER_HOME = Path.home()
CANDIDATE_ROOTS = [
    INTERNAL_TOOLS,
    SKILL_ROOT.parent,
    USER_HOME / ".codex" / "skills",
    USER_HOME / ".agents" / "skills",
    USER_HOME / ".dsh" / "skills",
    USER_HOME / ".workbuddy-ai" / "skills",
]

# 成员定义：(id, 说明, 类别, 激活模式, 匹配正则, 推荐阶段)
MEMBERS = [
    ("using-superpowers", "动手前先扫描并激活适用技能（基线第0步）",
     "process", "baseline", None, "pre-flight"),
     
    ("grill-me", "苏格拉底式极限需求施压与方案可行性质询",
     "clarify", "match",
     r"grill.?me|压力测试|可行性质询|方案质询|严苛审查|审视设计|找出漏洞|找破绽|反复推敲|深挖需求",
     "clarify"),

    ("brainstorming", "创造性任务意图/需求/设计硬门禁对话（获批前不实施）",
     "process", "match",
     r"new.?feature|add.{0,12}(function|component|capability|功能|组件|能力)"
     r"|build( me)? |create|design|implement|scaffold|refactor|architect"
     r"|做一?个|搭建|开发|实现|设计一?个|新增|写一?个(程序|工具|脚本|网站|应用|组件|模块)"
     r"|功能开发|创造性|方案设计",
     "design"),

    ("codebase-onboarding", "接手陌生仓库系统侦察，输出架构上手指南与映射",
     "understand", "match",
     r"unfamiliar|onboard|codebase.{0,10}(tour|map|understand|overview)"
     r"|first time.{0,15}repo|understand.{0,10}(codebase|project|repo)"
     r"|陌生|不熟悉|第一次看|梳理.{0,6}(项目|代码|架构)|项目架构|代码导览"
     r"|这个项目怎么|读懂|读代码|生成.?claude\.md",
     "understand"),

    ("ponytail", "极简代码实现（YAGNI原则、标准库优先、不加无谓依赖）",
     "coding", "match",
     r"\bcode\b|coding|write.{0,10}(function|script|program|代码|函数|脚本)"
     r"|fix.{0,6}bug|debug|implement|refactor|dependency|dependencies|library"
     r"|写代码|改代码|编码|重构|修bug|调试代码|选.{0,4}依赖|最简实现|yagni|ponytail",
     "implement"),

    ("find-skills", "通过 npx skills (skills.sh) 快速检索并立即安装技能",
     "acquire", "match",
     r"how do i do|is there a skill|find.{0,4}a? ?skill|install.{0,6}skill"
     r"|npx skills|有没有.{0,4}skill|找.{0,4}skill|安装.{0,4}skill|技能.{0,4}安装"
     r"|扩展能力|想要.{0,6}能力",
     "acquire"),

    ("skill-discovery", "社区开源技能深度评估、对比与推荐（skills.sh / SkillNet）",
     "acquire", "match",
     r"skill-discovery|evaluate.{0,10}skill|compare.{0,10}skill|community skill"
     r"|评估.{0,4}(skill|技能)|对比.{0,4}(skill|技能)|推荐.{0,4}(skill|技能)"
     r"|搜索.{0,4}社区|skills?\.sh|skillnet 找",
     "acquire"),

    ("skillnet", "SkillNet 技能供应链：将仓库/文档/日志/轨迹萃取沉淀为技能",
     "acquire", "match",
     r"\bskillnet\b|turn.{0,12}(repo|pdf|docx?|pptx?|log|trajectory).{0,12}skill"
     r"|create.{0,6}skill|assess.{0,6}skill|skill library|技能供应链"
     r"|把.{0,10}(文档|仓库|日志|资料).{0,6}(变成|做成|生成).{0,4}skill",
     "acquire"),

    ("skills-manager-cli", "驱动 skm 完成多工具技能纳管、跨端软链同步与诊断修复",
     "manage", "match",
     r"\bskm\b|enable.{0,6}skill|disable.{0,6}skill|symlink|symbolic link"
     r"|doctor|adopt|启用.{0,4}skill|禁用.{0,4}skill|符号链接|同步.{0,4}skill"
     r"|skill.{0,4}(没显示|找不到|缺失)|跨工具",
     "manage"),

    ("team-handoff", "多 Agent / 多环境无损任务交接协议与复盘检查点",
     "handoff", "match",
     r"handoff|team.?handoff|交接|换会话|换agent|给下一个|交接文档|任务移交",
     "handoff"),

    ("talk-like-girlfriend", "口令门控女友人格层（仅影响表达语气，不改变技术实质）",
     "persona", "explicit",
     r"/gf(\s+off)?|girlfriend.?mode|talk like (my )?girlfriend|be my girlfriend"
     r"|女友模式|女朋友.{0,2}(语气|模式|说话)|当我女朋友",
     "persona"),
]

# 阶段执行优先级 (数值越低越先执行)
STAGE_ORDER = {
    "pre-flight": 0,
    "manage": 1,
    "acquire": 2,
    "understand": 3,
    "clarify": 4,
    "design": 5,
    "implement": 6,
    "handoff": 7,
    "persona": 9
}

PERSONA_OFF = re.compile(r"/gf\s+off|normal mode|be serious|退出.{0,2}(女友|人格)|正常模式", re.I)


def resolve_member_path(name: str) -> Tuple[Optional[Path], str]:
    """
    智能多根自适应寻址：解析成员 SKILL.md 的实际存在路径与来源标记
    """
    for root in CANDIDATE_ROOTS:
        target = root / name / "SKILL.md"
        if target.exists():
            origin = "internal_tools" if root == INTERNAL_TOOLS else "external_hub"
            return target, origin
    return None, "missing"


def build_smart_plan(query: str) -> Dict[str, Any]:
    """
    分析任务输入，生成生命周期有序计划
    """
    q = query
    persona_off = bool(PERSONA_OFF.search(q))
    selected = []

    for name, label, cat, mode, pat, stage in MEMBERS:
        why = None
        if mode == "baseline":
            why = "流程基座：动手前先全盘扫描可用技能，杜绝盲目实施"
        elif mode == "explicit":
            m = re.search(pat, q, re.I) if pat else None
            if not m:
                continue
            if persona_off:
                why = "用户明确要求退出人格模式 (/gf off)"
            else:
                why = f"显式口令触发: '{m.group(0)}'"
        else:
            m = re.search(pat, q, re.I) if pat else None
            if not m:
                continue
            why = f"命中任务特征: '{m.group(0)}'"

        path_obj, origin = resolve_member_path(name)
        selected.append({
            "skill": name,
            "label": label,
            "category": cat,
            "stage": stage,
            "mode": mode,
            "why": why,
            "installed": path_obj is not None,
            "origin": origin,
            "path": str(path_obj) if path_obj else None
        })

    # 按生命周期阶段排序
    selected.sort(key=lambda s: (-1 if s["mode"] == "baseline" else STAGE_ORDER.get(s["stage"], 8)))
    for i, s in enumerate(selected):
        s["order"] = i

    # 确定主要调度成员
    non_base = [s for s in selected if s["mode"] != "baseline"]
    primary = non_base[0]["skill"] if non_base else "using-superpowers"

    # 供应链与冲突诊断
    notes = []
    acquire = [s["skill"] for s in selected if s["category"] == "acquire"]
    if len(acquire) > 1:
        notes.append("检测到多个获取通道：快速安装 -> find-skills；对比评估 -> skill-discovery；材料沉淀 -> skillnet")

    if any(s["skill"] == "talk-like-girlfriend" for s in selected):
        if persona_off:
            notes.append("已确认退出女友人格，恢复严谨工程风格")
        else:
            notes.append("女友人格已激活（仅覆盖表达语气，代码逻辑严密遵守 ponytail）")

    missing = [s["skill"] for s in selected if not s["installed"]]
    if missing:
        notes.append(f"发现未安装成员: {missing}，可通过 tools/ 下收拢组件或 skm 纳管补全")

    return {
        "query": q,
        "pipeline": [
            {
                "order": s["order"],
                "skill": s["skill"],
                "stage": s["stage"],
                "role": s["label"],
                "why": s["why"],
                "origin": s["origin"],
                "path": s["path"]
            }
            for s in selected
        ],
        "primary_focus": primary,
        "persona_off": persona_off,
        "missing_members": missing,
        "advisory_notes": notes,
        "execution_rule": "严格按照 pipeline 顺序依序执行各成员技能规范，各成员 SKILL.md 为单一事实源。"
    }


def cmd_list():
    """
    列出全部收编成员及其在当前系统中的自适应解析位置
    """
    report = {
        "auto_skills_root": str(SKILL_ROOT),
        "internal_tools_root": str(INTERNAL_TOOLS),
        "total_members": len(MEMBERS),
        "members": []
    }
    for name, label, cat, mode, _, stage in MEMBERS:
        path_obj, origin = resolve_member_path(name)
        report["members"].append({
            "skill": name,
            "label": label,
            "category": cat,
            "stage": stage,
            "activation": mode,
            "installed": path_obj is not None,
            "origin": origin,
            "resolved_path": str(path_obj) if path_obj else None
        })
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description="auto-skills 智能化自适应工作流调度引擎")
    ap.add_argument("query", nargs="*", help="任务描述文本")
    ap.add_argument("--list", action="store_true", help="列出所有收编成员与其自适应解析状态")
    args = ap.parse_args()

    if args.list:
        sys.exit(cmd_list())

    if not args.query:
        ap.error("请提供任务描述或传入 --list 查看支持的成员技能")

    plan = build_smart_plan(" ".join(args.query))
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
