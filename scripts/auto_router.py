#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_router.py — auto-skills 智能化自适应工作流调度引擎 (v2.5 全能旗舰版)
====================================================================
聚合业内 25 大顶流开源通用 Agent Skills，覆盖端到端软件工程全生命周期：

1. 【pre-flight 前置准备与状态自愈】：
   - using-superpowers (基线第0步：全局技能可用性扫描)
   - skills-manager-cli (驱动 skm 跨端软链修复与技能纳管)
   - codex-memory-guard (跨轮任务边界保护与关键记忆落盘守卫)

2. 【acquire 技能供应链全链路】：
   - find-skills (通过 npx skills 即时检索安装社区新技能)
   - skill-discovery (社区多候选技能深度对比评估与选型推荐)
   - skillnet (将现有仓库代码/文档/日志/轨迹逆向沉淀为标准技能)

3. 【understand 系统侦查与认知】：
   - codebase-onboarding (接手陌生仓库架构侦察与上手指南输出)

4. 【clarify 需求极限施压与漏洞挖掘】：
   - grill-me (苏格拉底式极限压力质询与方案可行性质疑)

5. 【design 架构设计与可视化门禁】：
   - brainstorming (意图->需求->方案硬门禁对话，未获批准严禁实施)
   - markdown-viewer (Mermaid架构时序/流程图、Vega数据图表生成渲染)

6. 【implement 极简高质工程实施】：
   - test-driven-development (TDD 红绿重构铁律：先写失败测试再实施)
   - ponytail (YAGNI 极简编码哲学：标准库优先、严控无谓膨胀)
   - cli-creator (将 API/脚本/服务一键构建为工业级 CLI 工具)
   - jupyter-notebook (交互式数据科学、算法原型探索与 Notebook 脚手架)

7. 【verify 质量、排错与安全防线】：
   - systematic-debugging (4步系统性根因诊断环：复现->溯源->微创修复->防退化)
   - code-review (5轴代码严审：逻辑正确性/安全/架构/复杂度/可测性)
   - security-best-practices (语言框架特定漏洞扫描、注入防御与加固)
   - playwright (真实无头浏览器端到端 E2E 自动化测试与 UI 走查)
   - gh-fix-ci (GitHub Actions CI/CD 流水线报错诊断与自愈修复)

8. 【handoff & closeout 交付收尾与协同】：
   - codex-project-closeout (工程交付收尾报告与知识库交接)
   - team-handoff (多 Agent / 跨会话任务移交与复盘检查点)
   - memory-consolidate (长期记忆与项目知识梳理去重归档)

9. 【persona 表达层与效率图层】：
   - talk-like-girlfriend (/gf 显式口令门控女友人格，解耦底层逻辑)
   - caveman (/caveman 显式门控极简洞穴人模式，降低 65% token 消耗)
   - no-negative-echo (去除此地无银三百两式的纠错痕迹与负面废话)
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
    # 0. 前置基准
    ("using-superpowers", "动手前先全盘扫描并激活适用技能（基线第0步）",
     "process", "baseline", None, "pre-flight"),

    ("skills-manager-cli", "驱动 skm 完成多工具技能纳管、跨端软链同步与诊断修复",
     "manage", "match",
     r"\bskm\b|enable.{0,6}skill|disable.{0,6}skill|symlink|symbolic link"
     r"|doctor|adopt|启用.{0,4}skill|禁用.{0,4}skill|符号链接|同步.{0,4}skill"
     r"|skill.{0,4}(没显示|找不到|缺失)|跨工具",
     "manage"),

    ("codex-memory-guard", "跨轮任务边界防护、关键记忆写入与上下文压缩守卫",
     "memory", "match",
     r"memory.?guard|上下文压缩|边界防护|关键记忆|防遗忘|写入记忆|压缩保护",
     "manage"),

    # 1. 技能供应链
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

    # 2. 系统侦查
    ("codebase-onboarding", "接手陌生仓库系统侦察，输出架构上手指南与映射",
     "understand", "match",
     r"unfamiliar|onboard|codebase.{0,10}(tour|map|understand|overview)"
     r"|first time.{0,15}repo|understand.{0,10}(codebase|project|repo)"
     r"|陌生|不熟悉|第一次看|梳理.{0,6}(项目|代码|架构)|项目架构|代码导览"
     r"|这个项目怎么|读懂|读代码|生成.?claude\.md",
     "understand"),

    # 3. 需求施压
    ("grill-me", "苏格拉底式极限需求施压与方案可行性质询",
     "clarify", "match",
     r"grill.?me|压力测试|可行性质询|方案质询|严苛审查|审视设计|找出漏洞|找破绽|反复推敲|深挖需求",
     "clarify"),

    # 4. 设计门禁
    ("brainstorming", "创造性任务意图/需求/设计硬门禁对话（获批前不实施）",
     "process", "match",
     r"new.?feature|add.{0,12}(function|component|capability|功能|组件|能力)"
     r"|build( me)? |create|design|implement|scaffold|refactor|architect"
     r"|做一?个|搭建|开发|实现|设计一?个|新增|写一?个(程序|工具|脚本|网站|应用|组件|模块)"
     r"|功能开发|创造性|方案设计",
     "design"),

    ("markdown-viewer", "可视化架构图、Mermaid流程图、Vega数据图表生成与渲染",
     "visual", "match",
     r"mermaid|plantuml|vega|diagram|architecture.?chart|可视化图表|架构图|时序图|流程图|状态图"
     r"|画一?个(架构|流程|时序|系统)|图解|数据可视化",
     "design"),

    # 5. 实施构建 (TDD / YAGNI / CLI / Jupyter)
    ("test-driven-development", "TDD 红绿重构铁律：先写失败测试用例，再写业务实现",
     "coding", "match",
     r"\btdd\b|test.?driven|红绿|测试驱动|先写测试|单元测试优先|red.?green",
     "implement"),

    ("ponytail", "极简代码实现（YAGNI原则、标准库优先、不加无谓依赖）",
     "coding", "match",
     r"\bcode\b|coding|write.{0,10}(function|script|program|代码|函数|脚本)"
     r"|fix.{0,6}bug|debug|implement|refactor|dependency|dependencies|library"
     r"|写代码|改代码|编码|重构|修bug|调试代码|选.{0,4}依赖|最简实现|yagni|ponytail",
     "implement"),

    ("cli-creator", "将 API、现有脚本或服务快速构建为标准工业级可组合 CLI 工具",
     "tooling", "match",
     r"cli|command.?line|curl|sdk|wrapper|构建cli|命令行工具|生成cli|做成命令行|做成工具",
     "implement"),

    ("jupyter-notebook", "创建、脚手架与调试 Jupyter Notebook (.ipynb) 科研交互实验",
     "research", "match",
     r"jupyter|notebook|\.ipynb|数据探索|实验笔记|交互式探索",
     "implement"),

    # 6. 质量、排错与安全
    ("systematic-debugging", "4步系统性根因诊断环：复现->溯源->微创修复->防退化",
     "verify", "match",
     r"debug|troubleshoot|bug|trace|diagnose|error|exception|fail|crash"
     r"|排错|找bug|报错|崩溃|异常|系统性调试|根因|定位问题|修不好|排查",
     "verify"),

    ("code-review", "多维度代码严审：逻辑正确性、安全漏洞、复杂度与可测性",
     "verify", "match",
     r"code.?review|pr.?review|diff|审查代码|代码评审|代码走查|核对代码|走查|找茬",
     "verify"),

    ("security-best-practices", "语言与框架特定安全最佳实践审查、漏洞扫描与防御加固",
     "verify", "match",
     r"security|vulnerability|safe|injection|xss|csrf|sql.?injection|hardcoded|secret"
     r"|安全审查|漏洞|安全加固|安全检查|安全合规|密码泄露|注入漏洞",
     "verify"),

    ("playwright", "真实浏览器端到端自动化测试、表单录制、截图与数据爬取",
     "verify", "match",
     r"playwright|e2e|browser.?test|headless|ui.?test|web.?automation"
     r"|浏览器自动化|端到端测试|页面测试|UI自动化|自动化录制",
     "verify"),

    ("gh-fix-ci", "排查与自动修复 GitHub Actions CI/CD 流水线报错与检查失败",
     "verify", "match",
     r"gh-fix-ci|github.?action|ci.?fail|check.?fail|workflow.?fail|pr.?check"
     r"|ci失败|actions报错|工作流失败|检查挂了|修ci",
     "verify"),

    # 7. 收尾与交接
    ("codex-project-closeout", "工程交付收尾归档、交付物核验与知识库落盘",
     "closeout", "match",
     r"closeout|交付|收尾|完工|结项|归档任务|交付清单",
     "handoff"),

    ("team-handoff", "多 Agent / 多环境无损任务交接协议与复盘检查点",
     "handoff", "match",
     r"handoff|team.?handoff|交接|换会话|换agent|给下一个|交接文档|任务移交",
     "handoff"),

    ("memory-consolidate", "长期记忆梳理、合并去重、冲突裁决与项目事实归档",
     "memory", "match",
     r"consolidate|梳理记忆|整理记忆|记忆合并|去重记忆|记忆归档",
     "handoff"),

    # 8. 人格与表达层
    ("talk-like-girlfriend", "口令门控女友人格层（仅影响表达语气，不改变技术实质）",
     "persona", "explicit",
     r"/gf(\s+off)?|girlfriend.?mode|talk like (my )?girlfriend|be my girlfriend"
     r"|女友模式|女朋友.{0,2}(语气|模式|说话)|当我女朋友",
     "persona"),

    ("caveman", "极简洞穴人超紧凑表达模式（输出精简 65%，保持技术纯粹性）",
     "efficiency", "explicit",
     r"/caveman(\s+off)?|caveman.?mode|talk like caveman|less tokens|be brief"
     r"|少说废话|极简模式|精炼回答|洞穴人",
     "persona"),

    ("no-negative-echo", "消除此地无银三百两式的纠错痕迹与多余解释，保持干净交付",
     "cleanliness", "match",
     r"no-negative-echo|不要废话|别解释为什么错|直接给结果|消除痕迹",
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
    "verify": 7,
    "handoff": 8,
    "persona": 9
}

PERSONA_OFF = re.compile(r"/gf\s+off|/caveman\s+off|normal mode|be serious|退出.{0,2}(女友|洞穴人|人格)|正常模式", re.I)


def resolve_member_path(name: str) -> Tuple[Optional[Path], str]:
    for root in CANDIDATE_ROOTS:
        target = root / name / "SKILL.md"
        if target.exists():
            origin = "internal_tools" if root == INTERNAL_TOOLS else "external_hub"
            return target, origin
    return None, "missing"


def build_smart_plan(query: str) -> Dict[str, Any]:
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
                why = f"用户要求退出模式 ({m.group(0)})"
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

    non_base = [s for s in selected if s["mode"] != "baseline"]
    primary = non_base[0]["skill"] if non_base else "using-superpowers"

    notes = []
    acquire = [s["skill"] for s in selected if s["category"] == "acquire"]
    if len(acquire) > 1:
        notes.append("检测到多个获取通道：快速安装 -> find-skills；对比评估 -> skill-discovery；材料沉淀 -> skillnet")

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
    report = {
        "auto_skills_root": str(SKILL_ROOT),
        "internal_tools_root": str(INTERNAL_TOOLS),
        "total_bundled_members": len(MEMBERS),
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
    ap = argparse.ArgumentParser(description="auto-skills 智能化自适应工作流调度引擎 (v2.5 全能旗舰版)")
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
