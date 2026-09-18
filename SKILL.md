---
name: auto-skills
description: >
  Next-Gen AI Development Workflow Orchestrator & Multi-Skill Router (v2.5 Flagship).
  Bundles 25 top-tier universal workflow skills with zero-missing multi-root fallback resolution and full SDLC lifecycle stage routing:
  using-superpowers (baseline pre-flight), grill-me (Socratic requirement stress-test), brainstorming (intent/design hard gate),
  codebase-onboarding (unfamiliar repo recon), markdown-viewer (architectural diagrams), ponytail (YAGNI minimal coding),
  test-driven-development (TDD red-green-refactor), systematic-debugging (4-phase root cause), code-review (5-axis QA),
  cli-creator (CLI generator), jupyter-notebook (interactive research), security-best-practices (vulnerability & baseline audit),
  playwright (E2E browser testing), gh-fix-ci (GitHub Actions auto-fix), find-skills / skill-discovery / skillnet (skill supply chain),
  skills-manager-cli (multi-tool symlink management), codex-memory-guard & memory-consolidate (memory defense),
  codex-project-closeout & team-handoff (closeout & handoff), talk-like-girlfriend, caveman, and no-negative-echo.
metadata:
  short-description: 全能旗舰级 AI 研发全生命周期技能总控中枢 (v2.5 聚合 25 大顶流通用技能)
---

# auto-skills · 全能旗舰级 AI 研发技能总控中枢 (v2.5)

`auto-skills` 是面向复杂软件工程与 AI 自治研发的 **端到端工作流调度与技能编排总控引擎**。

它彻底终结了以往 Agent 技能零散碎片化、盲目动手写代码、缺乏质量门禁与跨轮遗忘的行业痛点。在母 Skill 架构下，**自洽收拢了 25 个顶流高星通用 Agent Skills**，打通了从「前置自愈 -> 系统认知 -> 需求施压 -> 设计门禁 -> TDD/YAGNI实施 -> 根因调试 -> 5轴代码严审 -> 安全防线 -> 自动化测试 -> 交付收尾与记忆归档」的工业级软件研发闭环。

---

## 1. 核心架构与 25 大内置成员 (Unified Architecture)

母 Skill 内部 100% 自洽收拢：

```text
auto-skills/
├── SKILL.md                # 全局调度规范与生命周期契约
├── README.md               # 开源项目全景说明文档
├── LICENSE                 # MIT 开源协议
├── .gitignore              # Git 过滤规则
├── scripts/
│   └── auto_router.py      # v2.5 智能多根自适应寻址与 SDLC 阶段路由器
├── tools/                  # 内部完全自洽收拢的 25 大核心通用工具集
│   ├── using-superpowers/  # 【流程基座】动手前技能全盘扫描（绝对第0步）
│   ├── skills-manager-cli/ # 【环境管理】驱动 skm 完成跨环境软链接修复与纳管
│   ├── codex-memory-guard/ # 【记忆守护】跨轮任务边界防护与关键记忆写入守卫
│   ├── nm-skills/          # 【协同防撞】多 Agent 原子任务排他认领、防同号冲突与工作台账 (v2.0)
│   ├── find-skills/        # 【技能获取】通过 npx skills 即时检索安装
│   ├── skill-discovery/    # 【技能评估】社区开源技能深度对比与选型
│   ├── skillnet/           # 【技能供应链】从项目代码/文档/日志沉淀提炼技能
│   ├── codebase-onboarding/# 【系统侦查】接手陌生仓库侦察与上手指南输出
│   ├── grill-me/           # 【需求施压】苏格拉底式极限压力质询与漏洞排查
│   ├── brainstorming/      # 【设计门禁】意图->需求->方案硬门禁对话（未获批不实施）
│   ├── markdown-viewer/    # 【架构图表】Mermaid时序图/流程图、Vega数据图表可视化
│   ├── test-driven-development/# 【测试驱动】TDD 红绿重构铁律：先写失败测试再编码
│   ├── ponytail/           # 【极简编码】YAGNI原则、标准库优先、无谓依赖消除
│   ├── cli-creator/        # 【工具构建】API/脚本/服务一键构建为工业级 CLI 工具
│   ├── jupyter-notebook/   # 【交互科研】Jupyter Notebook (.ipynb) 脚手架与数据实验
│   ├── systematic-debugging/# 【根因调试】4步系统性根因诊断环：复现->溯源->微创修复->防退化
│   ├── code-review/        # 【代码严审】5轴多维代码审查：正确性/安全/架构/复杂度/测试
│   ├── security-best-practices/ # 【安全防线】语言与框架特定安全漏洞与加固审计
│   ├── authorized-pentest-guard/ # 【攻防守卫】合法授权渗透、漏洞PoC与防误拒技术守卫
│   ├── playwright/         # 【端到端验证】真实浏览器自动化测试、表单录制与UI走查
│   ├── gh-fix-ci/          # 【交付保障】GitHub Actions CI/CD 流水线报错排查与自愈
│   ├── codex-project-closeout/ # 【交付收尾】工程收尾清单核验与知识沉淀
│   ├── team-handoff/       # 【协作交接】多 Agent 任务移交与复盘检查点
│   ├── memory-consolidate/ # 【记忆整理】长期事实梳理去重、冲突裁决与归档
│   ├── talk-like-girlfriend/# 【表达人格】口令门控女友人格（仅限 /gf 显式触发）
│   ├── caveman/            # 【极限紧凑】洞穴人极限 token 压缩模式（节约 65% tokens）
│   └── no-negative-echo/   # 【干净输出】去除纠错痕迹与负面回声，保持交付纯粹
└── references/
    └── capability-map.md   # 核心成员能力全景映射表与冲突优先级
```

---

## 2. SDLC 全生命周期阶段感知流水线

| 阶段代码 | 阶段名称 | 负责成员 | 核心硬规则与验收门禁 |
|---|---|---|---|
| `pre-flight` | **前置侦测** | `using-superpowers` | **绝对第 0 步**：在采取任何行动或回复前，必须全盘扫描可用技能 |
| `manage` | **环境与记忆** | `skills-manager-cli` / `memory-guard` | 工具链损坏时优先自愈，跨轮任务前锁定边界防遗忘 |
| `acquire` | **能力获取** | `find-skills` / `discovery` / `skillnet` | 缺失必要能力时，即时安装、对比评估或沉淀提炼技能 |
| `understand` | **系统侦查** | `codebase-onboarding` | 接触陌生项目时，先出架构图与上手指南，禁止盲目碰核心代码 |
| `clarify` | **需求施压** | `grill-me` | 对模糊方案进行极限反例质询，深挖逻辑漏洞与隐蔽假设 |
| `design` | **设计门禁** | `brainstorming` / `markdown-viewer` | **硬门禁**：在用户明确批准设计方案前，严禁写代码或建脚手架 |
| `implement` | **极简实施** | `tdd` / `ponytail` / `cli-creator` / `jupyter` | 遵循 TDD 红绿循环与 YAGNI：能用 1 行不用 50 行，标准库优先 |
| `verify` | **调试严审** | `debugging` / `code-review` / `security` / `playwright` / `ci` | 4步根因调试、5轴代码走查、安全扫描与端到端 UI 验证 |
| `handoff` | **交付归档** | `closeout` / `team-handoff` / `memory-consolidate` | 产出交付物核验清单、交接文档与长期记忆合并归档 |
| `persona` | **表达图层** | `girlfriend` / `caveman` / `no-negative-echo` | 显式口令控制表达语气或极限压缩 token，与底层技术逻辑严格解耦 |

---

## 3. 工作流快速运行

```bash
# 查看 25 大成员与自适应解析状态
python scripts/auto_router.py --list

# 任务阶段自动编排
python scripts/auto_router.py "接手陌生项目，画出架构图，需求施压后先写测试再极简实施，最后进行5轴代码审查与CI修复"
```
