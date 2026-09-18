# auto-skills 成员能力映射与编排法则 (Capability Map v2.0)

> auto-skills 采用母 Skill 结构，内部 `tools/` 完整收拢 11 个顶尖成员技能。
> 同时也具备多根寻址机制，兼顾本地自洽与系统级全局技能调用。

---

## 1. 11 大成员能力矩阵

| 序号 | 成员 Skill | 生命周期阶段 | 触发特征与场景 | 核心输入/输出契约 |
|---|---|---|---|---|
| 01 | `using-superpowers` | `pre-flight` | **全局基准**：每次动作前强制执行 | 扫描可用技能库，输出执行前声明 |
| 02 | `grill-me` | `clarify` | 方案质询、压力测试、找漏洞、需求不确定 | 苏格拉底式极限追问，输出澄清清单 |
| 03 | `brainstorming` | `design` | 新增功能、组件开发、方案设计、创造性工作 | 意图与设计对话，输出设计方案待批 |
| 04 | `codebase-onboarding` | `understand` | 首次接触项目、梳理代码、接手陌生仓库 | 目录分析与依赖探测，输出上手指南 |
| 05 | `ponytail` | `implement` | 写代码、重构、修 Bug、选依赖 | YAGNI 极简实现，零无谓依赖代码 |
| 06 | `find-skills` | `acquire` | "有没有技能做X"、需要即刻安装技能 | 调用 npx skills，即时安装入库 |
| 07 | `skill-discovery` | `acquire` | 社区技能对比、选型评估、质量审查 | 扫描并对比社区候选，输出选型矩阵 |
| 08 | `skillnet` | `acquire` | 仓库/文档/日志沉淀为可复用技能 | 深度结构化提炼，输出完整 SKILL.md |
| 09 | `skills-manager-cli` | `manage` | 驱动 skm 工具、启用/禁用、软链接修复 | 诊断并同步全平台多端技能链接 |
| 10 | `team-handoff` | `handoff` | 任务交接、换会话、跨 Agent 协作 | 结构化交接文档，确保上下文零丢失 |
| 11 | `talk-like-girlfriend` | `persona` | 显式口令 `/gf`、要求亲昵语气 | 情绪化与亲昵表达层，底层逻辑不变 |

---

## 2. 编排流水线与阶段流转规则

整个执行过程严格按阶段推进：
$$\text{Pre-flight} \rightarrow \text{Manage} \rightarrow \text{Acquire} \rightarrow \text{Understand} \rightarrow \text{Clarify} \rightarrow \text{Design (Gate)} \rightarrow \text{Implement} \rightarrow \text{Handoff}$$

1. **绝对前置**：`using-superpowers` 永远作为执行序列的第 0 步，不可跳过。
2. **硬性门禁**：在创造性或重构任务中，`brainstorming` 拥有绝对否决权——未获用户明确批准，绝不开启 `ponytail` 编码阶段。
3. **获取分流**：
   - 立即要装入可用：选 `find-skills`；
   - 面对多个社区方案需要横向对比：选 `skill-discovery`；
   - 从现有成果或文档反向提炼知识：选 `skillnet`。
4. **人格解耦**：`talk-like-girlfriend` 仅覆盖自然语言输出层，代码实现与技术判断严格执行 `ponytail` 的极简原则。
