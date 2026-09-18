# auto-skills ⚡🤖
> **Next-Gen AI Development Workflow Orchestrator & Multi-Skill Router (v2.0)**  
> AI 研发全生命周期智能工作流调度与技能编排总控引擎：自洽收拢 11 大顶流核心技能，自适应多根寻址与 SDLC 阶段感知编排。

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Agent Skills Ready](https://img.shields.io/badge/Agent%20Skills-Standard-green.svg)](https://agentskills.io/)
[![Zero Missing Members](https://img.shields.io/badge/Members-100%25%20Self--Contained-brightgreen.svg)]()

---

## 🌟 为什么需要 auto-skills？ (Why auto-skills?)

当开发环境安装了数十个甚至上百个 Agent Skills 时，开发者和 AI 往往面临以下混乱局面：
1. **技能选择困难**：不知道当前任务应该用哪个技能，经常出现工具错配。
2. **盲目动手写代码**：跳过需求澄清与方案设计，直接在主分支写代码，导致反复推倒重来。
3. **缺少生命周期闭环**：缺乏“前置检查 -> 架构侦察 -> 需求施压 -> 设计门禁 -> 极简实施 -> 协同交接”的标准研发流水线。

**auto-skills** 将 11 个专业级工作流技能收编为一个统一入口。你只需给出任务意图，调度引擎将自动为你生成有序的流水线，并严格保证各个阶段的硬门禁！

---

## 🏗️ 架构与内置成员 (Architecture & Tools)

auto-skills 内部收拢所有成员，100% 自洽且支持多根自适应寻址：

```text
auto-skills/
├── SKILL.md                # 技能主入口规范与调度守则
├── README.md               # 项目主说明文档
├── LICENSE                 # MIT 开源协议
├── .gitignore              # Git 忽略配置
├── scripts/
│   └── auto_router.py      # v2.0 自适应多根寻址与 SDLC 阶段路由器
├── tools/                  # 内部收拢的 11 大核心专业工具集
│   ├── using-superpowers/  # 【流程基座】动手前技能全盘扫描（第0步）
│   ├── grill-me/           # 【需求澄清】苏格拉底式极限需求施压与方案可行性质询
│   ├── brainstorming/      # 【设计门禁】意图->需求->方案硬门禁对话（未获批不实施）
│   ├── codebase-onboarding/# 【工程理解】接手陌生仓库侦察与上手指南输出
│   ├── ponytail/           # 【极简编码】YAGNI原则、标准库优先、无谓依赖消除
│   ├── find-skills/        # 【技能获取】通过 npx skills 即时检索安装
│   ├── skill-discovery/    # 【技能评估】社区开源技能深度对比与选型
│   ├── skillnet/           # 【技能供应链】从项目代码/文档/日志沉淀提炼技能
│   ├── skills-manager-cli/ # 【多端管理】驱动 skm 完成跨环境软链接修复与纳管
│   ├── team-handoff/       # 【协作交接】多 Agent 任务移交与复盘检查点
│   └── talk-like-girlfriend/# 【表达人格】口令门控女友人格（仅限 /gf 显式触发）
└── references/
    └── capability-map.md   # 详细能力映射矩阵与冲突仲裁指南
```

---

## 🚀 SDLC 阶段流水线 (Execution Pipeline)

调度引擎会根据任务意图自动挂载对应生命周期阶段：

1. `pre-flight` (前置侦测) -> `using-superpowers`：全盘扫描适用技能，声明行动前提。
2. `understand` (系统侦察) -> `codebase-onboarding`：生成架构拓扑与上手指南。
3. `clarify` (极限施压) -> `grill-me`：苏格拉底式反向质询，深挖需求漏洞。
4. `design` (方案门禁) -> `brainstorming`：**硬性门禁**，设计未获批准严禁写代码。
5. `implement` (极简编码) -> `ponytail`：极简代码实现，YAGNI，严控代码膨胀。
6. `manage` & `acquire` -> `skills-manager-cli` / `find-skills` / `skill-discovery` / `skillnet`：自动补齐环境与技能供应链。
7. `handoff` (协同移交) -> `team-handoff`：产出标准交接材料。

---

## 🛠️ CLI 快速上手 (Quickstart)

### 1. 查看编队成员与解析状态
```bash
python scripts/auto_router.py --list
```

### 2. 对复杂任务进行流水线路由
```bash
python scripts/auto_router.py "接手一个陌生的前端项目，先做架构梳理并做需求质询，然后开发新模块并极简编码"
```

输出示例：
```json
{
  "pipeline": [
    {"order": 0, "skill": "using-superpowers", "stage": "pre-flight"},
    {"order": 1, "skill": "codebase-onboarding", "stage": "understand"},
    {"order": 2, "skill": "brainstorming", "stage": "design"},
    {"order": 3, "skill": "ponytail", "stage": "implement"}
  ],
  "primary_focus": "codebase-onboarding",
  "missing_members": []
}
```

---

## 📜 许可证 (License)

本项目基于 [MIT License](LICENSE) 开源发布。内部收拢的成员技能遵循其各自原始开源协议。
