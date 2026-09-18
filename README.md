# auto-skills ⚡🤖
> **Next-Gen AI Development Workflow Orchestrator & Multi-Skill Router (v2.5 Flagship)**  
> 全能旗舰级 AI 研发技能总控中枢：自洽收拢 25 大顶流核心技能，自适应多根寻址与 SDLC 阶段感知流水线。

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Agent Skills Ready](https://img.shields.io/badge/Agent%20Skills-Standard-green.svg)](https://agentskills.io/)
[![Zero Missing Members](https://img.shields.io/badge/Members-25%20Self--Contained-brightgreen.svg)]()
[![Full SDLC Pipeline](https://img.shields.io/badge/SDLC-Preflight%E2%86%92Design%E2%86%92TDD%E2%86%92Review%E2%86%92Closeout-blue.svg)]()

---

## 🌟 为什么需要 auto-skills？ (Why auto-skills?)

当开发环境安装了数十个甚至上百个 Agent Skills 时，开发者和 AI 往往面临以下混乱局面：
1. **技能选择困难与错配**：面对复杂工程任务，不知道该调用哪个技能，经常出现工具错配。
2. **盲目动手写代码**：跳过需求澄清、方案设计与测试，直接在主分支敲代码，导致反复推倒重来。
3. **缺乏质量防线与交接**：修 Bug 靠碰运气、合代码不审查安全与复杂度、多轮对话后关键状态被遗忘。

**auto-skills** 专为解决软件工程全流程治理而生。它将 **25 个高星通用技能** 收编为一个统一入口。你只需输入任务意图，调度引擎将自动为你生成端到端的执行流水线，并严格保证各阶段的硬门禁！

---

## 🏗️ 架构与 25 大内置成员 (Architecture & Tools)

auto-skills 内部收拢所有成员，100% 自洽且支持多根自适应寻址：

```text
auto-skills/
├── SKILL.md                # 技能主入口规范与生命周期契约
├── README.md               # 项目主说明文档
├── LICENSE                 # MIT 开源协议
├── .gitignore              # Git 忽略配置
├── scripts/
│   └── auto_router.py      # v2.5 智能多根自适应寻址与 SDLC 阶段路由器
├── tools/                  # 内部收拢的 25 大核心专业工具集
│   ├── using-superpowers/  # 【流程基座】动手前技能全盘扫描（第0步）
│   ├── skills-manager-cli/ # 【环境管理】驱动 skm 完成跨环境软链接修复与纳管
│   ├── codex-memory-guard/ # 【记忆守护】跨轮任务边界防护与关键记忆写入守卫
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
│   ├── playwright/         # 【端到端验证】真实浏览器自动化测试、表单录制与UI走查
│   ├── gh-fix-ci/          # 【交付保障】GitHub Actions CI/CD 流水线报错排查与自愈
│   ├── codex-project-closeout/ # 【交付收尾】工程收尾清单核验与知识沉淀
│   ├── team-handoff/       # 【协作交接】多 Agent 任务移交与复盘检查点
│   ├── memory-consolidate/ # 【记忆整理】长期事实梳理去重、冲突裁决与归档
│   ├── talk-like-girlfriend/# 【表达人格】口令门控女友人格（仅限 /gf 显式触发）
│   ├── caveman/            # 【极限紧凑】洞穴人极限 token 压缩模式（节约 65% tokens）
│   └── no-negative-echo/   # 【干净输出】去除纠错痕迹与负面回声，保持交付纯粹
└── references/
    └── capability-map.md   # 详细能力映射矩阵与冲突仲裁指南
```

---

## 🚀 SDLC 9 阶段全景流水线 (Execution Pipeline)

调度引擎会根据任务意图自动挂载对应生命周期阶段：

1. `pre-flight` (前置侦测) -> `using-superpowers`：全盘扫描适用技能，声明行动前提。
2. `manage` (环境与记忆) -> `skills-manager-cli` / `codex-memory-guard`：软链健康自愈与任务边界记忆锁定。
3. `acquire` (能力供应链) -> `find-skills` / `discovery` / `skillnet`：自动补齐外部技能或提炼资产。
4. `understand` (系统侦查) -> `codebase-onboarding`：生成架构拓扑与上手指南。
5. `clarify` (极限施压) -> `grill-me`：苏格拉底式反向质询，深挖需求边界漏洞。
6. `design` (方案门禁) -> `brainstorming` / `markdown-viewer`：**硬性门禁**，设计未获批准严禁写代码。
7. `implement` (TDD极简实施) -> `test-driven-development` / `ponytail` / `cli-creator` / `jupyter`：红绿测试驱动开发，YAGNI 极简编码。
8. `verify` (根因排错与安全严审) -> `systematic-debugging` / `code-review` / `security` / `playwright` / `ci`：4步根因调试、5轴严审、漏洞加固与端到端 UI 测试。
9. `handoff` (交付收尾与归档) -> `closeout` / `team-handoff` / `memory-consolidate`：交付核验与记忆整理。

---

## 🛠️ CLI 快速上手 (Quickstart)

### 1. 查看 25 大编队成员与自适应解析状态
```bash
python scripts/auto_router.py --list
```

### 2. 对复杂端到端任务进行流水线路由
```bash
python scripts/auto_router.py "接手一个陌生的前端项目，先做架构梳理并做需求质询，然后按TDD开发新模块并做5轴代码审查与CI修复"
```

输出示例：
```json
{
  "pipeline": [
    {"order": 0, "skill": "using-superpowers", "stage": "pre-flight"},
    {"order": 1, "skill": "codebase-onboarding", "stage": "understand"},
    {"order": 2, "skill": "grill-me", "stage": "clarify"},
    {"order": 3, "skill": "brainstorming", "stage": "design"},
    {"order": 4, "skill": "test-driven-development", "stage": "implement"},
    {"order": 5, "skill": "ponytail", "stage": "implement"},
    {"order": 6, "skill": "code-review", "stage": "verify"},
    {"order": 7, "skill": "gh-fix-ci", "stage": "verify"}
  ],
  "primary_focus": "codebase-onboarding",
  "missing_members": []
}
```

---

## 📜 许可证 (License)

本项目基于 [MIT License](LICENSE) 开源发布。内部收拢的成员技能遵循其各自原始开源协议。
