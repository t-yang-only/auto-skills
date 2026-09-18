---
name: auto-skills
description: >
  Next-Gen AI Development Workflow Orchestrator & Multi-Skill Router (v2.0).
  Bundles 11 top-tier workflow skills with zero-missing multi-root fallback resolution and full SDLC lifecycle stage routing:
  using-superpowers (baseline pre-flight), grill-me (Socratic requirement stress-test), brainstorming (intent/design hard gate),
  codebase-onboarding (unfamiliar repo recon), ponytail (YAGNI minimal coding), find-skills / skill-discovery / skillnet (skill supply chain),
  skills-manager-cli (multi-tool symlink management), team-handoff (multi-agent checkpoint), and talk-like-girlfriend (command-gated persona).
metadata:
  short-description: AI 研发全生命周期智能工作流调度与技能编排总控引擎 (v2.0)
---

# auto-skills · AI 研发全生命周期技能总控中枢 (v2.0)

`auto-skills` 是面向复杂 AI 辅助研发的 **全生命周期工作流调度与技能编排总控引擎**。

它彻底打破“单一技能零散调用”或“无序盲目写代码”的传统弊端，将 11 个顶级工作流技能收编为自洽的流水线体系。通过**意图特征分析、SDLC 研发阶段感知与自适应多根寻址**，自动为当前任务生成最佳执行流水线（Pipeline），并在各阶段严格执行对应技能的硬门禁与质量契约。

---

## 1. 核心架构与工具收拢 (Unified Architecture)

为保证 100% 独立自洽与跨环境可移植性，`auto-skills` 采用母 Skill 架构，所有成员技能规范与执行工具统一收拢在内部 `tools/` 目录中：

```text
auto-skills/
├── SKILL.md                # 本文件：全局调度规范与生命周期契约
├── README.md               # 开源项目全景说明文档
├── LICENSE                 # MIT 开源协议
├── .gitignore              # Git 过滤规则
├── scripts/                # 调度总控引擎
│   └── auto_router.py      # v2.0 智能多根自适应寻址与 SDLC 阶段路由器
├── tools/                  # 内部完全自洽收拢的 11 大核心成员工具集
│   ├── using-superpowers/  # 【流程基座】动手前技能全盘扫描（第0步）
│   ├── grill-me/           # 【需求澄清】苏格拉底式极限压力质询与漏洞排查
│   ├── brainstorming/      # 【设计门禁】意图->需求->方案硬门禁对话（未获批不实施）
│   ├── codebase-onboarding/# 【工程理解】接手陌生仓库侦察与上手指南输出
│   ├── ponytail/           # 【极简编码】YAGNI原则、标准库优先、无谓依赖消除
│   ├── find-skills/        # 【技能获取】通过 npx skills 即时检索安装
│   ├── skill-discovery/    # 【技能评估】社区开源技能深度对比与选型
│   ├── skillnet/           # 【技能供应链】从项目代码/文档/日志沉淀提炼技能
│   ├── skills-manager-cli/ # 【多端管理】驱动 skm 完成跨环境软链接修复与纳管
│   ├── team-handoff/       # 【协作交接】多 Agent 任务移交与复盘检查点
│   └── talk-like-girlfriend/# 【表达人格】口令门控女友人格（仅限 /gf 显式触发）
└── references/             # 阶段映射手册与编排规则
    └── capability-map.md   # 11 大成员能力全景映射表与冲突优先级
```

---

## 2. SDLC 全生命周期阶段感知流水线

调度引擎将研发任务划分为七大标准阶段，并按序流转：

| 阶段代码 | 阶段名称 | 负责成员 | 核心硬规则与验收门禁 |
|---|---|---|---|
| `pre-flight` | **前置侦测** | `using-superpowers` | **绝对第 0 步**：在采取任何行动或回复前，必须全盘扫描可用技能 |
| `manage` | **环境管理** | `skills-manager-cli` | 工具链或软链接损坏时优先自愈，运行 `skm doctor/fix` |
| `acquire` | **能力获取** | `find-skills` / `discovery` / `skillnet` | 缺失必要工具时，按需完成即时安装或能力提炼 |
| `understand` | **系统侦查** | `codebase-onboarding` | 接触陌生项目时，先出架构图与上手指南，禁止盲目碰核心代码 |
| `clarify` | **需求施压** | `grill-me` | 对模糊方案进行极限反例质询，暴露边界缺陷 |
| `design` | **设计门禁** | `brainstorming` | **硬门禁**：在用户明确批准设计方案前，严禁写代码或建脚手架 |
| `implement` | **极简实施** | `ponytail` | 严格遵循 YAGNI：能用 1 行不用 50 行，标准库优先，不引新依赖 |
| `handoff` | **协同交接** | `team-handoff` | 任务收尾或跨 Agent 协作时输出标准 Handover 报告 |
| `persona` | **表达图层** | `talk-like-girlfriend` | 仅在显式口令触发时覆盖表达语气，不改变任何底层技术实质 |

---

## 3. 工作流执行指南 (Standard Operating Procedure)

1. **执行智能路由**：
   ```bash
   python scripts/auto_router.py "<用户任务描述>"
   ```
   获得结构化执行计划（JSON 包含 `pipeline`、`primary_focus`、`advisory_notes`）。

2. **按序打开 SKILL.md**：
   按照生成的 `pipeline` 列表，依序打开各成员 `path` 指向的文件并严格遵守其内部规范。

3. **冲突仲裁法则**：
   - **用户即时指令** > 任何成员规则。
   - **设计门禁 (brainstorming)** > 动手冲动 (ponytail)：方案未被批准前，禁止实施。
   - **表达层解耦**：女友人格 (talk-like-girlfriend) 仅作用于会话语气，代码与架构实现必须严守 ponytail 极简约束。
   - **安全任务转移**：涉及渗透、逆向、二进制或安全分析任务，自动转交 `hacker-skills`。
