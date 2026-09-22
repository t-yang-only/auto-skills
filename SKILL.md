---
name: auto-skills
description: >
  Next-Gen AI Development Workflow Orchestrator, Multi-Skill Router & Multi-Agent Coordination Hub (v3.0 Flagship).
  深度融合多 Agent 原子任务认领与排他工作台账中枢 (nm-skills 牛马协同中枢)：原生提供任务独占锁 (claim)、租约排他锁 (Lease with TTL)、严格单调防撞编号分配器、实时任务看板 (board) 与工作日志自动归档，彻底根除多 Agent 并发抢跑同一任务、序号同号冲突与文件覆盖痛点。
  Bundles 35 top-tier universal workflow skills with zero-missing multi-root fallback resolution and full SDLC lifecycle stage routing:
  using-superpowers (baseline pre-flight), nm-skills (atomic task claim & mutual exclusion ledger), grill-me (Socratic requirement stress-test), brainstorming (intent/design hard gate),
  codebase-onboarding (unfamiliar repo recon), markdown-viewer (architectural diagrams), ponytail (YAGNI minimal coding),
  test-driven-development (TDD red-green-refactor), systematic-debugging (4-phase root cause), code-review (5-axis QA),
  verification-before-completion (evidence before any completion claim),
  cli-creator (CLI generator), jupyter-notebook (interactive research), security-best-practices (vulnerability & baseline audit),
  authorized-pentest-guard (offensive-defensive security guard), playwright (E2E browser testing), gh-fix-ci (GitHub Actions auto-fix),
  find-skills / skill-discovery / skillnet (skill supply chain), skills-manager-cli (multi-tool symlink management),
  codex-memory-guard & memory-consolidate (memory defense), codex-project-closeout & team-handoff (closeout & handoff),
  talk-like-girlfriend, caveman, and no-negative-echo.
  当用户提到 auto-skills、nm-skills、牛马skills、工作登记、任务认领、排他锁、agent_word、多Agent协作、防止重复做任务时使用。
metadata:
  short-description: 全能旗舰级 AI 研发全生命周期与多 Agent 协同排他台账总控中枢 (v3.0 深度融合 nm-skills)
---

# auto-skills · 全能旗舰级 AI 研发与多 Agent 协同中枢 (v3.0)

`auto-skills` 是面向复杂软件工程、AI 自治研发与多 Agent 协同的 **端到端工作流调度、排他防撞与技能编排总控引擎**。

它深度融合了 **多 Agent 牛马协同台账 (nm-skills v2.0)**，自洽收拢了 **35 个顶流高星通用 Agent Skills**，不仅打通了从「前置自愈 -> 系统认知 -> 需求施压 -> 设计门禁 -> TDD/YAGNI实施 -> 根因调试 -> 5轴代码严审 -> 安全防线 -> 自动化测试 -> 交付收尾与记忆归档」的完整工业级生命周期闭环，更彻底解决了**多 Agent 在同一工程下并发作业时抢跑同一任务、编号同号冲突与代码互撞覆盖**的行业顽疾！

---

## 1. 核心架构 (Unified Architecture)

母 Skill 内部 100% 自洽收拢：

```text
auto-skills/
├── SKILL.md                # 全局调度规范、多 Agent 协同契约与生命周期规则
├── README.md               # 开源项目全景说明文档
├── LICENSE                 # MIT 开源协议
├── .gitignore              # Git 过滤规则 (包含 .evolution 私有进化区保护)
├── .gitattributes          # 统一行尾为 LF (防 Windows autocrlf 把检出改成 CRLF)
├── config/                 # 统一配置中心 (默认下载时配置细节为空)
│   ├── config.yaml         # 活跃配置文件 (默认空配置模版)
│   └── config.example.yaml # 完整配置注释范例文本
├── scripts/
│   ├── auto_router.py      # v3.0 智能多根自适应寻址、任务分级、协同命令与引导分发器
│   ├── db_sync.py          # 数据库存储与全链路自动落库引擎 (MySQL 8.4 专有子账户支持)
│   ├── experience_mining.py# 历史工具链调用与经验挖掘沉淀引擎 (30天滚动清理)
│   ├── config_manager.py   # 统一全局配置读写与多层自适应合并引擎
│   ├── wizard_setup.py     # 首次调用配置向导与跨 Agent 自动连接引擎
│   ├── pull_persona_traits.py # 从知识库自适应拉取女友人格定义与温情特性
│   ├── nm_register.py      # 原生内置：多 Agent 原子任务认领、排他租约锁与台账维护
│   ├── sync_evolution.py   # 用户个人私有 Git 仓库一键同步与推送引擎
│   ├── notify_push.py      # 多渠道消息同步中心 (支持 Server酱/企微/飞书/钉钉等8大渠道)
│   ├── git_push_notify.py  # 自动化 Git 提交、推送与多渠道广播联动
│   ├── obsidian_bridge.py  # Obsidian 本地/在线双模知识库自适应同步桥梁
│   ├── init_evolution_vault.py # 个人私有双轨进化仓库初始化向导
│   ├── tool_onboarder.py   # 新技能自动接入、元数据萃取与注册台账维护
│   ├── opinion_request.py  # 意见请求通道客户端（向人提问 / 取回结论）
│   ├── sync_skill_counts.py# 文档技能计数自动同步（13 个锚点）
│   ├── _test_registry.py   # 回归：台账 / 计数 / 占位 / 树成员一致性
│   ├── _test_failover.py   # 回归：落库容错三层（熔断 / 暂存 / 补传）
│   └── _test_doc_tree_guards.py # 守卫的守卫：破坏文档树必须让断言变红（防断言失效）
├── tools/                  # 内部完全自洽收拢的 35 大核心通用工具集
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
│   ├── verification-before-completion/# 【完成前验证】证据先于断言：未跑验证不得声称完成
│   ├── receiving-code-review/# 【审查反馈】逐条回应 review 意见：不辩解、不打包、不同意要说理
│   ├── diagnosing-skills/  # 【故障诊断】技能未触发/落库无数据/任务重复：查轨迹表定位断点
│   ├── security-best-practices/ # 【安全防线】语言与框架特定安全漏洞与加固审计
│   ├── authorized-pentest-guard/ # 【攻防守卫】合法授权渗透、漏洞PoC与防误拒技术守卫
│   ├── playwright/         # 【端到端验证】真实浏览器自动化测试、表单录制与UI走查
│   ├── gh-fix-ci/          # 【交付保障】GitHub Actions CI/CD 流水线报错排查与自愈
│   ├── codex-project-closeout/ # 【交付收尾】工程收尾清单核验与知识沉淀
│   ├── team-handoff/       # 【协作交接】多 Agent 任务移交与复盘检查点
│   ├── memory-consolidate/ # 【记忆整理】长期事实梳理去重、冲突裁决与归档
│   ├── talk-like-girlfriend/# 【表达人格】口令门控女友人格（仅限 /gf 显式触发）
│   ├── caveman/            # 【极限紧凑】洞穴人极限 token 压缩模式（节约 65% tokens）
│   ├── no-negative-echo/   # 【干净输出】去除纠错痕迹与负面回声，保持交付纯粹
│   ├── incremental-implementation/ # 【增量实现】薄垂直切片：改一点/验一点/提交一点
│   ├── using-git-worktrees/ # 【物理隔离】并行 Agent 各用一个 worktree，不撞同一批文件
│   ├── requesting-code-review/ # 【请审查】给可验证上下文，而不是“帮我看看”
│   ├── writing-plans/       # 【计划】把方向拆成可验证可提交的步骤
│   └── finishing-a-development-branch/ # 【收尾】合并前清单、合并形状与清理
├── template/
│   └── SKILL.md            # 新技能纳管骨架模板 (--add 缺 SKILL.md 时按此生成)
└── references/
    └── capability-map.md   # 35 大成员能力全景映射表与冲突优先级
```

---

## 2. 深度融合：多 Agent 原子任务认领与排他工作台账 (nm-skills)

在同一工程目录下，当多个 Agent（Codex、Cursor、DSH、Claude、WorkBuddy、豆包）并行协作时，**必须执行原子排他认领**：

### 核心机制：
1. **排他租约锁 (Lease with TTL)**：基于底层原子排他锁，任何 Agent 在开始修改代码前必须成功 `claim`。若已被其他活跃 Agent 认领，立即硬性拦截并报告持有者及剩余租约，**彻底防止两个 Agent 同时进行同一任务**；
2. **严格单调单向编号**：分配 Agent 编号 (`NM-<CLIENT>-XXX`) 时使用互斥锁保护，彻底根除编号重复冲突；
3. **文件防撞预警**：认领时声明涉及的文件；若检测到其他进行中任务正在修改重叠文件，立即预警拦截；
4. **统一台账看板**：自动在工程根目录维护 `agent_word/`，包含 `任务认领表.md`（实时看板）、`工作登记表.md`（流水总表）、`工作日志.md`（详细复盘日志）等。
5. **技能多根寻址（固定根 + 动态发现）**：解析成员技能时先查固定根（自带 `tools/` → 私有进化区 → 同级母技能 → 常见 harness 根），再查**动态发现**的根 —— 扫描 `~/*/skills` 与 `~/*/skills` 中确实含 `SKILL.md` 的目录，按路径排序、规范化去重后缓存。这样用户在任意 harness（Claude Code / Cursor / Gemini / Hermes / CodeBuddy / zcode / OpenClaw …）里装的技能都能被解析到；只靠硬编码列表时，实测本机 20+ 个技能根里有 17 个是盲区，「零遗漏」会变成空话。

### 常用原生命令：
```bash
# 1. 任务认领 (动手前必做：成功加锁并分配严格递增编号；被抢占则强行拦截)
python scripts/auto_router.py claim --task-id "TASK-AUTH-01" --task "重构系统认证逻辑" --client CODE --files "auth.py"

# 2. 查看看板 (查看当前谁在执行什么任务、租约有效期)
python scripts/auto_router.py board

# 3. 文件冲突前置检测 (检查文件是否被其他活跃 Agent 锁定占用)
python scripts/auto_router.py check-file --files "auth.py,router.py"

# 4. 长任务租约续期 (为当前正在进行的任务延长租约时长)
python scripts/auto_router.py renew --task-id "TASK-AUTH-01" --extend 60

# 5. 查看身份与锁状态感知
python scripts/auto_router.py whoami

# 6. 任务完成 (释放排他锁，追加详细工作日志与技能建议)
python scripts/auto_router.py done --task-id "TASK-AUTH-01" --changes "已完成认证模块重构" --files "auth.py"

# 7. 放弃/转交任务
python scripts/auto_router.py release --task-id "TASK-AUTH-01" --reason "等待前置PR合入"

# 8. 清理超时僵尸锁
python scripts/auto_router.py gc

# 9. 查看最近工作登记流水
python scripts/auto_router.py log --limit 15
```

---

## 3. 全局配置中心与首次 Agent 启动引导 (Config & Wizard)

在 `config/` 目录下提供全局配置能力（首次下载时所有细节配置项均为空）：
- **配置文件**：`config/config.yaml`（活跃配置模板）与 `config/config.example.yaml`（注释范本）；
- **首次强制引导门禁**：任何 AI Agent 首次调用 `auto-skills` 无论执行什么任务，系统都会优先辅助用户完成基础配置：
  1. 是否自动检查并下载公开 `auto-skills` 更新；
  2. 是否永远默认启用 `nm-skills` 在项目目录下建立执行登记（`agent_word/`）；
  3. 多渠道推送凭据（Server酱、企业微信、飞书、钉钉等）；
  4. 是否默认启用女朋友人格模式，以及是否从本地/在线知识库拉取人格温情特性；
  5. 是否建立并同步到个人私有 Git 进化仓库（`<your-private-vault-repo>`）；
- **跨 Agent 自动连接与镜像**：配置完成后自动扫描本机所有 Agent 技能目录（Codex, Agents, DSH, WorkBuddy, Claude Code, Cursor 等），一键建立互联同步。

```bash
# 启动配置向导
python scripts/auto_router.py setup

# 扫描并连接本机所有 Agent 环境
python scripts/auto_router.py connect-agents

# 查看当前配置与 Agent 互联状态
python scripts/wizard_setup.py --status
```

---

## 4. SDLC 全生命周期阶段感知流水线

调度引擎会根据任务意图自动挂载对应生命周期阶段：

1. `pre-flight` (前置侦测) -> `using-superpowers`：全盘扫描适用技能，声明行动前提。
2. `manage` (环境与协同) -> `skills-manager-cli` / `codex-memory-guard` / `nm-skills`：软链修复、记忆防跨轮遗忘、多 Agent 任务排他认领与工作台账。
3. `acquire` (能力供应链) -> `find-skills` / `skill-discovery` / `skillnet`：自动检索、深度评估或从代码逆向沉淀技能。
4. `understand` (系统侦查) -> `codebase-onboarding`：生成架构拓扑与上手指南。
5. `clarify` (极限施压) -> `grill-me`：苏格拉底式反向质询，深挖需求边界漏洞。
6. `design` (方案门禁) -> `brainstorming` / `markdown-viewer`：**硬性门禁**，设计未获批准严禁写代码。
7. `implement` (TDD极简实施) -> `test-driven-development` / `ponytail` / `cli-creator` / `jupyter`：红绿测试驱动开发，YAGNI 极简编码。
8. `verify` (根因排错与安全严审) -> `systematic-debugging` / `code-review` / `verification-before-completion` / `receiving-code-review` / `diagnosing-skills` / `security` / `authorized-pentest-guard` / `playwright` / `ci`：4步根因调试、5轴严审、漏洞加固与端到端 UI 测试。
9. `handoff` (交付收尾与归档) -> `closeout` / `team-handoff` / `memory-consolidate`：交付核验与记忆整理。

---

## 5. 极速模式 (Fast-Path) 与 Token 优化

为防止微小任务或查询类任务浪费 Token，`auto-skills` 搭载了三档自适应路由：
- `--mode auto` (默认)：智能判定任务复杂度。小任务自动走 Fast-Path（仅调用 1 个最关键技能），大任务拉起完整 SDLC；
- `--mode fast`：强制极速单点执行，节省 90%+ 上下文 Token；
- `--mode full`：强制拉起全套工业级流程。

```bash
# 极速排错示例
python scripts/auto_router.py --mode fast "修复 auth.py 中的 SyntaxError"
```

---

## 6. 数据库存储、工具链自动落库与经验挖掘 (MySQL 8.4)

支持 MySQL 8.4 云端/内网数据库与 SQLite 本地双模：
- **专用权限最小化子账户**：日常工具链落库采用只具备 `SELECT, INSERT, UPDATE, DELETE` 权限的专用子账户（如 `auto_agent`），彻底杜绝 DROP/ALTER 等高危系统权限污染；
- **全链路自动落库**：任务认领 (`nm_tasks`)、工作完成与日志 (`nm_work_logs`)、工具链调用轨迹 (`tool_execution_traces`)、技能资产台账 (`skill_registry`)、路由器审计 (`router_audit_logs`)、参考文献定义 (`academic_references`) 全部无感自动写入。工具链轨迹的**自动触发点**（诚实边界：能自动拦的是本 Skill 自己的执行链，"任意 harness 里每一次 Read/Bash 调用"需要 harness 级钩子，不在本 Skill 能力内）：
  - `auto_router.py <任意查询>` -> `route_dispatch` 轨迹（stage=pre-flight，含 tier 与流水线摘要）
  - `nm_register.py claim` / `done` -> `claim` / `done` 轨迹（stage=coordination）
  - 其余工具调用显式记录：`auto_router.py trace <工具名> "<做了什么>" [--action] [--stage] [--status FAILED --error "..."] [--duration-ms N]`
  - Python 内用 `db_sync.trace_tool(...)` 上下文管理器（自动测耗时、自动判成败）；
  - **落库失败绝不静默**：统一写 `.evolution/db_sync_errors.log`（此前是 `except: pass`，"没报错"会被误当成"在写"）；
- **30天滚动清理**：工具调用轨迹自动滚动清理超过 30 天的历史记录，保持数据库轻量高响应；
- **历史经验挖掘**：遇到相似工程报错或多 Agent 协作冲突时，自动通过 `scripts/experience_mining.py` 挖掘过往成功避坑经验。

```bash
# 查看数据库状态与统计
python scripts/auto_router.py db --status

# 针对相似问题检索过往工具链执行经验
python scripts/auto_router.py exp "多 Agent 任务冲突"

# 查看最近 30 天工具调用排行榜与成功率
python scripts/auto_router.py exp --top-tools
```

---

## 7. 多渠道消息同步与 Obsidian 在线知识库

- **多渠道消息聚合广播** (`scripts/notify_push.py`)：支持配置 Server酱 Turbo (微信)、企业微信、飞书、钉钉 (带签名)、PushPlus、Telegram、Bark、自定义 Webhook，任务完成或 Git 提交时并行广播；
- **Obsidian 本地/在线知识库双模桥梁** (`scripts/obsidian_bridge.py`)：支持配置在线端点与访问密钥（均可留空），首次运行自动探测本地/在线环境并决定最优同步方式；
- **双轨私有进化区** (`.evolution/`)：独立 Git 仓库保护个人偏好与敏感凭据，上游主库更新时零覆盖、零污染。


---

## 8. 意见请求（Agent 向人提问的唯一通道）

**当 Agent 走到必须由人拍板的岔路时，不要自己替人决定，也不要只是把问题打印在对话里等人看见**——
用本 skill 提供的通道开一张单子：人会在他自己的知识库里看到，答复后 Hermes 会通知回你。

### 8.1 什么时候必须提问

- 两条路都合理，但选了就不好回头（改架构、删数据、换渠道、对外发布）
- 需要人的价值取舍（省钱 vs 稳妥、快 vs 全）
- 涉及外部副作用且没有明确授权（装软件、花钱、发消息、改生产配置）
- 信息不足且只有人手里有（某个口令、某个业务口径）

**不需要提问**：能从代码/文档/知识库查到答案的，自己查；实现细节，自己定。

### 8.2 怎么提问

```bash
python scripts/opinion_request.py ask \
  --title "一句话问题" \
  --question "具体问什么，要能独立看懂" \
  --context "背景：我在做什么、卡在哪、为什么必须你拍板" \
  --option "A:做什么、代价、后果" \
  --option "B:做什么、代价、后果" \
  [--project D:\foo] [--harness codex] [--session xxx] [--urgency high]
```

- **选项给 2–5 个**，每个都要能独立看懂；也可以让人不选、直接写意见。
- **一张单子只问一件事。**

### 8.3 身份是硬要求（不要跳过）

脚本会自动采集 `harness / session / project` 三项，采集不到会**直接报错要求你显式传入**。
这三项决定 Hermes 事后能不能找回你——**没有它们的单子等于白问**。

```bash
python scripts/opinion_request.py whoami    # 先看自动采到了什么
```

支持的自动探测来源：`AGW_HARNESS` / `DSH_SESSION_ID` / `CLAUDE_*` / `CODEX_*` / `CURSOR_*` / `GEMINI_*` / `PI_*` / `GROK_*` / `HERMES_HOME`。

### 8.4 身份前缀（写进知识库的硬规定）

**凡是 Agent 写进知识库的任何文字，首行必须是身份行**：

```
[HARNESS <harness> | session=<会话ID> | project=<项目文件夹>]
```

本脚本已自动带上。手工写时也必须遵守。

> **不带这个前缀的文字 = 人写的。** Agent 永远不要伪造或省略它——
> 否则 Hermes 会把人工回复误判成 Agent 消息，或者反过来，
> 导致「人已经选好了却没人去划掉选项」这种事故。

### 8.5 取回答复

```bash
python scripts/opinion_request.py list            # 有无新答复
python scripts/opinion_request.py check <单号>     # 看某张单子的结论
```

拿到答复后**按结论执行**，并在知识库对应位置收尾（划掉待办、更新页面）。

### 8.6 允许做什么、不允许做什么

网关按令牌分级，`agent` 令牌的权限是：

| 能力 | 允许 |
|---|---|
| 读知识库（增量识别用 `?since=` 游标） | ✅ 全域只读 |
| 新建意见请求单 | ✅ 仅 `意见请求/待回答/` |
| 写自己的登记文件 | ✅ 仅 `意见请求/agent登记/<你的harness>.md` |
| 改已存在的意见请求单 | ❌ |
| 写 `随心记/` `日记/` `知识/` `index.md` | ❌ **用户的书写区，Agent 不得触碰** |
| 写 `意见请求/索引.md` `已回答/` `说明.md` | ❌ 那是 Hermes 的地盘 |
| 读 `_知识库访问指南.md` 等含密钥的文件 | ❌ |
| 写知识库任何其他位置 | ❌ |

**除 Hermes 外，任何 Agent 都不能写用户的书写区。** 这是刻意设计，不要试图绕过。

---

## 9. 回归测试与自检 (Regression & Self-Check)

改动本仓库后跑这三条，它们是**可执行的判据**，不是说明文字：

```bash
# 1) 台账与文档一致性（31 项断言）
python scripts/_test_registry.py

# 2) 数据库落库容错层（12 项断言，需能连到实例 A）
python scripts/_test_failover.py

# 3) 守卫的守卫：破坏文档树必须让上面第 1 条变红（6 个用例）
python scripts/_test_doc_tree_guards.py
```

`_test_registry.py` 覆盖两类曾经真实发生过的缺陷，改完必须重跑：

- **防 BOM 复发**：任一 `tools/*/SKILL.md` 带 UTF-8 BOM 即判失败。根因是 frontmatter 正则 `^---`
  要求文件第一个字符就是 `-`，BOM（`EF BB BF`）会让匹配失败，`description` 静默回退成「无描述」，
  症状隐蔽（技能仍在、只是描述为空）。
- **防文档脱节**：`SKILL.md` / `README.md` / `references/capability-map.md` 里的技能计数必须等于
  `tools/` 下的实际目录数；capability-map 的矩阵行数也必须相等、序号不得重复。

`_test_doc_tree_guards.py` 为什么必须存在：**一条再也拦不住人的断言，和一条通过的断言长得一模一样**。
本项目实测过一次 —— 仓库根留下一个 `.bak` 文件，第 7 段断言因此常红，于是「破坏后确实变红了」
不再证明任何事，负向测试悄悄变成安慰剂。所以改了文档树相关断言后，要跑第 3 条：
它在临时副本里逐个破坏文档结构（删一个 scripts 条目 / 删整段 tools 子项 / 删整段 scripts 子项 /
删整段 scripts 块 / 删一行矩阵），要求真断言**必须**变红，并额外要求杂散 `*.bak`、`*.swp` **不得**触发断言。
原始文件全程不被修改。

两条都是 `exit 0/1`，可直接接进任何 CI 或 pre-push 流程。
