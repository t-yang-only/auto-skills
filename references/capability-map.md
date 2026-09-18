# auto-skills 25 大核心成员能力映射矩阵 (Capability Map v2.5)

> auto-skills 采用母 Skill 架构，内部 `tools/` 完整收拢 25 个顶尖高星通用成员技能。
> 具备 6 级多根自适应寻址机制，兼顾本地独立自洽与系统级跨环境调用。

---

## 1. 25 大成员能力全景矩阵

| 序号 | 成员 Skill | 生命周期阶段 | 核心定位与职责 |
|---|---|---|---|
| 01 | `using-superpowers` | `pre-flight` | **全局基准**：每次动作前强制全盘扫描可用技能，输出声明 |
| 02 | `skills-manager-cli` | `manage` | 驱动 `skm` 工具，完成全平台软链接纳管、跨端同步与修复 |
| 03 | `codex-memory-guard` | `manage` | 跨轮任务边界防护、关键记忆写入与上下文压缩守卫 |
| 04 | `find-skills` | `acquire` | "有没有技能做X"：调用 npx skills 快速安装社区技能 |
| 05 | `skill-discovery` | `acquire` | 社区技能多维对比、选型评估与质量审查 |
| 06 | `skillnet` | `acquire` | 技能供应链：将现有代码/文档/日志/轨迹逆向沉淀为标准技能 |
| 07 | `codebase-onboarding` | `understand` | 陌生仓库系统侦察，输出架构映射、入口目录与上手指南 |
| 08 | `grill-me` | `clarify` | 方案质询、压力测试、反例深挖，极限暴露需求漏洞 |
| 09 | `brainstorming` | `design` | **硬门禁**：意图与设计深度对话，未获用户批准严禁编码 |
| 10 | `markdown-viewer` | `design` | 架构可视化：Mermaid 流程图/时序图、Vega 交互图表生成与渲染 |
| 11 | `test-driven-development`| `implement` | TDD 红绿重构铁律：先写失败测试用例，再写业务实现 |
| 12 | `ponytail` | `implement` | 极简代码哲学：YAGNI、标准库优先、严控新依赖与代码冗余 |
| 13 | `cli-creator` | `implement` | 将 API、本地脚本或后台服务封装为标准工业级 CLI 命令行工具 |
| 14 | `jupyter-notebook` | `implement` | 交互式数据科学、算法原型探索与 Jupyter (.ipynb) 脚手架 |
| 15 | `systematic-debugging` | `verify` | 4步系统性根因诊断环：确定性复现->逆向溯源->单点微创修复->防退化 |
| 16 | `code-review` | `verify` | 5轴代码严审：逻辑正确性、安全防御、架构开闭、复杂度与可测性 |
| 17 | `security-best-practices`| `verify` | 语言与框架特定安全漏洞审计（XSS/注入/密钥泄露）与加固 |
| 18 | `playwright` | `verify` | 真实无头浏览器端到端自动化测试、表单录制、截图走查与数据采集 |
| 19 | `gh-fix-ci` | `verify` | GitHub Actions CI/CD 流水线报错诊断、日志审查与自愈修复 |
| 20 | `codex-project-closeout`| `handoff` | 工程交付收尾归档、交付物核验与知识库落盘 |
| 21 | `team-handoff` | `handoff` | 多 Agent 任务移交协议、状态断点保存与复盘检查点 |
| 22 | `memory-consolidate` | `handoff` | 长期记忆梳理、合并去重、冲突裁决与项目事实归档 |
| 23 | `talk-like-girlfriend` | `persona` | 显式口令 `/gf` 激活亲昵女友人格层（与底层代码逻辑严格解耦） |
| 24 | `caveman` | `persona` | 显式口令 `/caveman` 激活洞穴人极限压缩模式（降低 65% token） |
| 25 | `no-negative-echo` | `persona` | 消除此地无银三百两式的纠错痕迹与多余解释，保持干净交付 |

---

## 2. 编排流水线与阶段流转规则

$$\text{Pre-flight} \rightarrow \text{Manage} \rightarrow \text{Acquire} \rightarrow \text{Understand} \rightarrow \text{Clarify} \rightarrow \text{Design (Gate)} \rightarrow \text{Implement (TDD/YAGNI)} \rightarrow \text{Verify (Debug/Review/Security)} \rightarrow \text{Handoff (Closeout)}$$

1. **绝对前置**：`using-superpowers` 永远作为执行序列的第 0 步，不可跳过。
2. **硬性门禁**：在创造性或重构任务中，`brainstorming` 拥有绝对否决权——未获用户明确批准，绝不开启实施阶段。
3. **实施准则**：优先执行 `test-driven-development` 确认失败测试，再交由 `ponytail` 以最小充分方式通过测试。
4. **质量防线**：任何代码提交前，先经由 `systematic-debugging` 排除潜在隐患，再通过 `code-review` 与 `security-best-practices` 完成安全与质量闭环。
5. **人格解耦**：`talk-like-girlfriend` / `caveman` 仅覆盖自然语言表达层，代码实现与技术判断严格执行底层工程纪律。
