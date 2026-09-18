#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_router.py — auto-skills 智能化自适应工作流调度引擎 (v3.0 旗舰双轨极速版)
=============================================================================
核心突破与架构升级：
1. 【动态任务复杂度分流与小任务极速模式 (Fast-Path / Token-Saving)】：
   - 自动判定任务复杂度：
     * FAST_PATH (微小任务)：纯问答、查状态、单行小修、简单概念、无架构影响。
       -> 自动跳过前置基座与冗长设计门禁，0子技能直答或单技能极简执行，节省 90%+ Token！
     * FULL_SDLC (中大型工程)：新功能开发、系统架构重构、安全攻防、复杂 Bug 诊断。
       -> 激活标准 9 阶段生命周期流水线，执行硬门禁把控。
   - 支持显式命令参数覆盖：`--mode auto|fast|full`。
2. 【合法授权安全攻防与防误拒守卫 (Authorized Pentest & Anti-Refusal)】：
   - 内置 `authorized-pentest-guard`，为授权渗透、CTF演练、漏洞PoC分析提供免误拒机制。
3. 【自适应多根路径解析与内置 tools/ 优先】：
   - 优先级 1: 本身内置 tools/<skill>/SKILL.md (100% 独立自洽)
   - 优先级 2: 私有进化区 .evolution/custom_skills/<skill>/SKILL.md
   - 优先级 3: ~/.codex/skills/<skill>/SKILL.md
   - 优先级 4: ~/.agents/skills/<skill>/SKILL.md
   - 优先级 5: ~/.dsh/skills/<skill>/SKILL.md
   - 优先级 6: ~/.workbuddy-ai/skills/<skill>/SKILL.md
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
PRIVATE_EVOLUTION_TOOLS = SKILL_ROOT / ".evolution" / "custom_skills"

USER_HOME = Path.home()
CANDIDATE_ROOTS = [
    INTERNAL_TOOLS,
    PRIVATE_EVOLUTION_TOOLS,
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

    ("nm-skills", "多 Agent 原子任务排他认领、工作台账与并发防撞协调 (v2.0)",
     "coordination", "match",
     r"nm-skills|\bnm\b|牛马|工作登记|agent台账|台账|任务认领|并发冲突|重复任务|排他锁|谁在做什么|agent_word",
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

    ("ppt-skill", "演示文稿工业级制作、存量美化重构、异形蒙版裁剪、智能生图与视觉走查",
     "presentation", "match",
     r"\bpptx?\b|powerpoint|slides?|keynote|演示文稿|幻灯片|做ppt|做演示|美化ppt|改ppt|ppt排版|生成ppt|重构ppt",
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

    ("authorized-pentest-guard", "授权攻防演练、渗透测试、漏洞PoC与防误拒技术守卫",
     "verify", "match",
     r"pentest|exploit|payload|bypass|overflow|privilege|ctf|渗透|攻防|漏洞验证|绕过|提权|逆向分析|反编译|红队|靶场",
     "verify"),

    ("hacker-skills", "统一安全工程总入口：渗透测试、逆向反编译、漏洞挖掘与CTF红队演练",
     "security", "match",
     r"\bhacker\b|渗透测试|逆向工程|逆向分析|反编译|固件安全|二进制安全|漏洞利用|红队演练",
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

# 轻量/微小任务判别特征
MICRO_TASK_PATTERNS = [
    r"^(查|看|找|列出|解释|说明|翻译|打印|echo|cat|ls|pwd|status|git status)",
    r"(怎么用|是什么|为什么|啥意思|如何配置|参数是什么)",
    r"(改一下(文案|注释|路径|常量|变量名|端口))",
    r"(只看|仅需|简单看一下|一句话|快速看下)"
]


def classify_task_tier(query: str, explicit_mode: str = "auto") -> Tuple[str, str]:
    """
    判断任务属于 FAST_PATH 还是 FULL_SDLC
    """
    if explicit_mode == "fast":
        return "FAST_PATH", "用户显式指定 --mode fast 极速通道"
    if explicit_mode == "full":
        return "FULL_SDLC", "用户显式指定 --mode full 全流程通道"

    q_strip = query.strip()
    # 规则 1: 文本长度非常简短且未包含复杂开发动词
    if len(q_strip) <= 18:
        if not re.search(r"开发|重构|架构|搭建|系统|渗透|红队|安全测试|全流程", q_strip):
            return "FAST_PATH", "短指令且无宏大架构动词，自动进入极速模式以节省 Token"

    # 规则 2: 命中轻量查询/单行微改特征
    for p in MICRO_TASK_PATTERNS:
        if re.search(p, q_strip, re.I):
            return "FAST_PATH", f"匹配轻量微小任务模式 '{p}'，跳过前置仪式直接直达"

    # 规则 3: 默认走向完整流程
    return "FULL_SDLC", "综合判定为中大型工程任务，拉起标准 SDLC 生命周期流水线"


def resolve_member_path(name: str) -> Tuple[Optional[Path], str]:
    for root in CANDIDATE_ROOTS:
        target = root / name / "SKILL.md"
        if target.exists():
            if root == INTERNAL_TOOLS:
                origin = "internal_tools"
            elif root == PRIVATE_EVOLUTION_TOOLS:
                origin = "private_evolution"
            else:
                origin = "external_hub"
            return target, origin
    return None, "missing"


def get_custom_private_members() -> List[Tuple[str, str, str, str, str, str]]:
    """
    动态扫描 .evolution/custom_skills/ 注册台账，加载用户个人自安装与私有技能
    """
    custom_reg = PRIVATE_EVOLUTION_TOOLS / "registry.json"
    if not custom_reg.exists():
        return []
    try:
        data = json.loads(custom_reg.read_text(encoding="utf-8"))
        res = []
        for name, info in data.get("tools", {}).items():
            label = info.get("description", f"私有自定义技能 {name}")[:50]
            cat = info.get("category", "implement")
            # 正则模式：匹配技能名称或常见别名
            kw = re.escape(name)
            res.append((name, f"【私有技能】{label}", cat, "match", kw, cat))
        return res
    except Exception:
        return []


def get_all_members() -> List[Tuple[str, str, str, str, str, str]]:
    return list(MEMBERS) + get_custom_private_members()


def build_smart_plan(query: str, mode: str = "auto") -> Dict[str, Any]:
    q = query
    persona_off = bool(PERSONA_OFF.search(q))
    tier, tier_reason = classify_task_tier(q, explicit_mode=mode)

    all_members = get_all_members()
    selected = []

    # 如果是 FAST_PATH：只匹配 1 个最关键的实施/回答技能（或空），绝对跳过 baseline (using-superpowers) 与 design 门禁！
    if tier == "FAST_PATH":
        # 寻找是否有强相关的单个专精技能（如 ponytail 或 cli）
        for name, label, cat, m_mode, pat, stage in all_members:
            if m_mode == "match" and pat:
                m = re.search(pat, q, re.I)
                if m:
                    path_obj, origin = resolve_member_path(name)
                    selected.append({
                        "skill": name,
                        "label": label,
                        "category": cat,
                        "stage": stage,
                        "mode": m_mode,
                        "why": f"极速直达: 命中 '{m.group(0)}'",
                        "installed": path_obj is not None,
                        "origin": origin,
                        "path": str(path_obj) if path_obj else None
                    })
                    break  # 极速模式最多选 1 个最匹配的技能，不再叠加

        return {
            "query": q,
            "task_tier": "FAST_PATH",
            "tier_reason": tier_reason,
            "token_saving_mode": True,
            "pipeline": [
                {
                    "order": i,
                    "skill": s["skill"],
                    "stage": s["stage"],
                    "role": s["label"],
                    "why": s["why"],
                    "origin": s["origin"],
                    "path": s["path"]
                }
                for i, s in enumerate(selected)
            ],
            "primary_focus": selected[0]["skill"] if selected else "direct_reply",
            "advisory_notes": [
                "⚡ 已启用极速模式 (Fast Path)：跳过 using-superpowers 前置扫描与设计门禁，直达实施或回答，节省 90%+ Token！"
            ],
            "execution_rule": "直接完成用户所需小任务，无需复杂的流程报告与形式化卡片。"
        }

    # FULL_SDLC 完整模式：
    for name, label, cat, m_mode, pat, stage in all_members:
        why = None
        if m_mode == "baseline":
            why = "流程基座：动手前先全盘扫描可用技能，杜绝盲目实施"
        elif m_mode == "explicit":
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
            "mode": m_mode,
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
        "task_tier": "FULL_SDLC",
        "tier_reason": tier_reason,
        "token_saving_mode": False,
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
    all_members = get_all_members()
    report = {
        "auto_skills_root": str(SKILL_ROOT),
        "internal_tools_root": str(INTERNAL_TOOLS),
        "private_evolution_root": str(PRIVATE_EVOLUTION_TOOLS),
        "total_bundled_members": len(all_members),
        "members": []
    }
    for name, label, cat, mode, _, stage in all_members:
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
    # 1. 优先检测是否为 nm-skills 多 Agent 协同排他子命令 (claim / done / board / release / gc / renew / check-file)
    if len(sys.argv) > 1 and sys.argv[1] in ("claim", "done", "board", "release", "gc", "renew", "check-file"):
        try:
            import nm_register
            return nm_register.main()
        except ImportError:
            try:
                from tools.nm_skills.scripts import nm_register
                return nm_register.main()
            except Exception as e:
                print(f"[ERROR] 调用 nm-skills 协同模块失败: {e}")
                sys.exit(1)

    # 2. 检测是否为个人私有进化同步子命令 (sync-private / private-sync)
    if len(sys.argv) > 1 and sys.argv[1] in ("sync-private", "private-sync"):
        try:
            import sync_evolution
            # 去除首个参数后再转发
            sys.argv.pop(1)
            return sync_evolution.main()
        except Exception as e:
            print(f"[ERROR] 调用私有同步模块失败: {e}")
            sys.exit(1)

    # 3. 检测是否为技能自安装/纳管子命令 (install-skill / onboard-skill)
    if len(sys.argv) > 1 and sys.argv[1] in ("install-skill", "onboard-skill"):
        try:
            import tool_onboarder
            sys.argv.pop(1)
            return tool_onboarder.main()
        except Exception as e:
            print(f"[ERROR] 调用工具纳管模块失败: {e}")
            sys.exit(1)

    ap = argparse.ArgumentParser(description="auto-skills 智能化自适应工作流调度引擎 (v3.0 旗舰双轨版，深度融合 nm-skills 协同排他锁与私有 Git 同步)")
    ap.add_argument("query", nargs="*", help="任务描述文本，或协同子命令 (claim/done/board/renew/sync-private/install-skill)")
    ap.add_argument("--mode", choices=["auto", "fast", "full"], default="auto", help="路由模式：auto 自动评估复杂度，fast 极速省Token，full 完整SDLC")
    ap.add_argument("--list", action="store_true", help="列出所有收编成员与其自适应解析状态")
    args = ap.parse_args()

    if args.list:
        sys.exit(cmd_list())

    if not args.query:
        ap.error("请提供任务描述，或传入 --list 查看支持的成员技能，或使用 claim/done/board 协同子命令")

    plan = build_smart_plan(" ".join(args.query), mode=args.mode)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
