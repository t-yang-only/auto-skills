# auto-skills ⚡🤖
> **Next-Gen AI Development Workflow Orchestrator, Multi-Skill Router & Multi-Agent Coordination Hub (v3.0 Flagship)**  
> 全能旗舰级 AI 研发与多 Agent 协同总控中枢：深度融合多 Agent 牛马协同台账 (nm-skills v2.0)，自洽收拢 35 大顶流核心技能，提供排他防撞、自适应多根寻址与 SDLC 阶段感知流水线。

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Agent Skills Ready](https://img.shields.io/badge/Agent%20Skills-Standard-green.svg)](https://agentskills.io/)
[![Zero Missing Members](https://img.shields.io/badge/Members-35%20Self--Contained-brightgreen.svg)]()
[![Multi-Agent Mutual Exclusion](https://img.shields.io/badge/Coordination-Atomic%20Lease%20Lock-brightgreen.svg)]()
[![Full SDLC Pipeline](https://img.shields.io/badge/SDLC-Preflight%E2%86%92Design%E2%86%92TDD%E2%86%92Review%E2%86%92Closeout-blue.svg)]()

---

## 🌟 为什么选择 auto-skills v3.0？ (Why auto-skills?)

当开发环境安装了数十个甚至上百个 Agent Skills，且多个 AI 编程代理（Codex、Cursor、DSH、Claude、WorkBuddy、豆包）在同一工程下协作时，开发者和 AI 往往面临严重混乱：
1. **任务撞车与重复施工**：多个 Agent 同时发现同一个缺陷，各自开工修改，提交时造成严重代码冲突与覆盖。
2. **序号冲突与日志错乱**：缺乏全局互斥机制，多个 Agent 同时读取历史流水，分配出相同的编号（如同号 015、016 冲突）。
3. **盲目动手写代码**：跳过需求澄清、方案设计与测试，直接在主分支敲代码，导致反复推倒重来。
4. **跨轮遗忘与交接断层**：复杂任务多轮对话后状态丢失，缺乏客观的工程台账与交接标准。

**auto-skills v3.0** 专为解决全流程治理与多 Agent 协同而生：
- **深度融合 nm-skills 牛马协同台账**：原生搭载分布式原子任务认领 (`claim`)、租约排他锁 (`Lease with TTL`)、严格单调递增编号分配器与实时看板 (`board`)，彻底根除任务冲突；
- **自洽收拢 35 个高星通用技能**：你只需输入任务意图，调度引擎将自动为你生成端到端的执行流水线，并严格保证各阶段的硬门禁！

---

## 🏗️ 架构与 35 大内置成员 (Architecture & Tools)

auto-skills 内部收拢所有成员，100% 自洽且支持多根自适应寻址：

```text
auto-skills/
├── SKILL.md                # 技能主入口规范、多 Agent 协同规则与生命周期契约
├── README.md               # 项目主说明文档
├── LICENSE                 # MIT 开源协议
├── .gitignore              # Git 忽略配置 (包含 .evolution 私有进化区保护)
├── .gitattributes          # 统一行尾为 LF (防 Windows autocrlf 把检出改成 CRLF)
├── config/                 # 统一配置目录 (首次下载所有细节字段全为空)
│   ├── config.yaml         # 默认空白配置文件模板
│   └── config.example.yaml # 完整配置说明与注释范本
├── scripts/
│   ├── auto_router.py      # v3.0 智能多根自适应寻址、任务分级与协同命令分发器
│   ├── db_sync.py          # 数据库存储与全链路自动落库引擎 (MySQL 8.4 专有子账户支持)
│   ├── experience_mining.py# 历史工具链调用与经验挖掘沉淀引擎 (30天滚动清理)
│   ├── config_manager.py   # 全局配置管理与双轨自适应合并引擎
│   ├── wizard_setup.py     # 首次调用配置向导与跨 Agent 自动连接集成器
│   ├── pull_persona_traits.py # 从知识库自适应拉取女友人格定义与温情特性
│   ├── nm_register.py      # 原生内置：多 Agent 原子任务认领、排他租约锁与台账维护
│   ├── sync_evolution.py   # 用户个人私有 Git 仓库自动同步与推送引擎
│   ├── notify_push.py      # 多渠道消息同步中心 (支持 8 大主流推送渠道)
│   ├── git_push_notify.py  # 自动化 Git 提交、推送与多渠道广播联动
│   ├── obsidian_bridge.py  # Obsidian 本地/在线双模知识库自适应同步桥梁
│   ├── init_evolution_vault.py # 个人私有双轨进化仓库初始化向导
│   ├── tool_onboarder.py   # 新技能自动接入、元数据萃取与注册台账维护
│   ├── opinion_request.py  # 意见请求通道客户端（向人提问 / 取回结论）
│   ├── sync_skill_counts.py# 文档技能计数自动同步（13 个锚点）
│   ├── _test_registry.py   # 回归：台账 / 计数 / 占位 / 树成员一致性
│   ├── _test_failover.py   # 回归：落库容错三层（熔断 / 暂存 / 补传）
│   └── _test_doc_tree_guards.py # 守卫的守卫：破坏文档树必须让断言变红（防断言失效）
├── tools/                  # 内部收拢的 35 大核心专业工具集
│   ├── using-superpowers/  # 【流程基座】动手前技能全盘扫描（第0步）
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

## 🤝 多 Agent 原子任务认领与排他防撞 (Native nm-skills)

在任何代码实施前，必须显式抢占独占任务锁：

```bash
# 1. 任务认领 (获得排他锁，默认租约 45 分钟；被抢占则硬性拦截并输出持有者与剩余租约)
python scripts/auto_router.py claim --task-id "TASK-AUTH-01" --task "重构系统认证逻辑" --client CODE --files "auth.py"

# 2. 查看看板 (查看当前谁在执行什么任务)
python scripts/auto_router.py board

# 3. 文件冲突前置检测 (检查文件是否被其他活跃 Agent 锁定占用)
python scripts/auto_router.py check-file --files "auth.py,router.py"

# 4. 长任务租约续期 (为当前正在进行的任务延长租约时长)
python scripts/auto_router.py renew --task-id "TASK-AUTH-01" --extend 60

# 5. 查看身份与当前锁感知
python scripts/auto_router.py whoami

# 6. 任务完成 (释放排他锁，追加详细工作日志与技能建议)
python scripts/auto_router.py done --task-id "TASK-AUTH-01" --changes "已完成认证模块重构" --files "auth.py"

# 7. 释放/放弃任务 (中途放弃或转交)
python scripts/auto_router.py release --task-id "TASK-AUTH-01" --reason "前置依赖未就绪"

# 8. 清理超时僵尸锁
python scripts/auto_router.py gc

# 9. 查看最近工作日志
python scripts/auto_router.py log --limit 15
```

---

## 🛠️ 全局配置中心与首次 Agent 启动引导 (Config & Wizard)

在 `config/` 目录下提供全局配置能力（默认下载时所有细节字段全为空）：
- **空配置模板**：`config/config.yaml` 与 `config/config.example.yaml`；
- **首次调用引导门禁**：任何 Agent 首次运行无论执行何种指令，系统均会优先辅助用户完成基础配置：
  1. 是否自动检查并下载公开 `auto-skills` 更新；
  2. 是否永远默认启用 `nm-skills` 在项目目录下建立执行登记（`agent_word/`）；
  3. 多渠道推送凭据（Server酱、企业微信、飞书、钉钉等）；
  4. 是否默认启用女朋友人格模式，若启用将自动从知识库（Obsidian/在线知识库）拉取人格温情特性；
  5. 是否建立并绑定至个人私有 Git 进化仓库（`<your-private-vault-repo>`）；
- **跨 Agent 智能扫描与连接**：配置完成后自动扫描本机所有 Agent 技能目录并建立互联同步。

```bash
# 启动配置向导
python scripts/auto_router.py setup

# 扫描并连接本机所有 Agent 环境（首次向导时自动执行）
python scripts/auto_router.py connect-agents

# 仓库更新后重新分发（改了本仓库必须跑这条）
python scripts/wizard_setup.py --deploy

# 只检查是否同步（陈旧 / 链接失效 / 残留凭据时 exit 1）
python scripts/wizard_setup.py --check-deploy

# 部署形态：链接（推荐，六根共用一份快照）或副本
python scripts/wizard_setup.py --link --mode link
python scripts/wizard_setup.py --unlink          # 退回独立副本
```

> **为什么需要 `--deploy`**：首次向导只执行一次，仓库之后的每次提交都不会自动分发。
> 实测过一次：六个 Agent 根（`.codex` / `.agents` / `.dsh` / `.workbuddy-ai` / `.claude` / `.cursor`）
> 的副本全部落后一个功能，每个 agent 都在跑旧代码，而没有任何提示。
>
> 用 `--link` 可改成链接形态：六个根共用一份不含凭据的快照，不会再出现
> 「有的根同步了、有的没同步」；同时凭据只在真源一处，链接路径读不到。

---

## ⚡ 极速模式 (Fast-Path Token Saver)

```bash
# 自动复杂度判定 (默认)：小任务走极速模式，中大型任务拉起完整 SDLC
python scripts/auto_router.py "修改 README.md 中的版本号"

# 强制极速模式：节约 90%+ 上下文 Token
python scripts/auto_router.py --mode fast "修复 auth.py 中的语法错误"

# 强制完整模式：拉起全套 9 大生命周期阶段
python scripts/auto_router.py --mode full "重构用户认证微服务并编写 E2E 测试"
```

---

## 🐬 数据库存储、工具链自动落库与经验挖掘 (MySQL 8.4 Dedicated Sub-Account)

支持连接远程/内网 MySQL 8.4 数据库，配备权限最小化专用子账户，实现全链路操作无感落库与经验闭环：
- **权限安全隔离**：配置专用子账户（`auto_agent`），仅被赋予 `SELECT, INSERT, UPDATE, DELETE` 权限，杜绝 DROP/ALTER 等误操作或注入风险，防止权限污染；
- **全链路自动落库**：任务认领 (`nm_tasks`)、工作完成与日志 (`nm_work_logs`)、工具链调用轨迹 (`tool_execution_traces`)、技能资产台账 (`skill_registry`)、路由器审计 (`router_audit_logs`)、参考文献定义 (`academic_references`) 全自动异步持久化。工具链轨迹在 `auto_router.py` 每次路由、`nm_register.py` 每次认领/完成时自动写入；其他工具调用用 `auto_router.py trace <工具名> "<做了什么>"` 显式记录。落库失败写 `.evolution/db_sync_errors.log`，不再静默吞掉；
- **30天滚动清理机制**：自动定期清理超过 30 天的调用轨迹，保持云端存储的高性能与轻量化；
- **历史经验挖掘**：遇到类似技术报错或协作冲突时，从历史数据库中自动检索曾调用过的工具链与避坑经验（`lessons_learned`），杜绝重复踩坑。

```bash
# 查看数据库连接与五大表行数概况
python scripts/auto_router.py db --status

# 针对具体任务或报错检索过往成功经验
python scripts/auto_router.py exp "多 Agent 任务冲突"

# 查看最近 30 天工具调用排行榜与成功率统计
python scripts/auto_router.py exp --top-tools
```

---

## 📡 多渠道消息同步与任务广播 (Multi-Channel Sync Hub)

支持客户自主配置主流消息推送渠道，完成大型任务或 Git 提交时自动广播：
- **支持渠道**：Server酱 Turbo (微信)、企业微信群机器人、飞书机器人、钉钉机器人 (支持签名)、PushPlus、Telegram Bot、Bark (iOS)、自定义 Webhook。
- **客户自配置**：
  ```bash
  # 查看所有渠道状态
  python scripts/notify_push.py --config-list

  # 配置企业微信 / 飞书 / 钉钉
  python scripts/notify_push.py --config-set wecom "https://qyapi.weixin.qq.com/..."
  python scripts/notify_push.py --config-set feishu "https://open.feishu.cn/..."
  python scripts/notify_push.py --config-set dingtalk "https://oapi.dingtalk.com/..." "SEC_SECRET"

  # 启停渠道与联通测试
  python scripts/notify_push.py --enable wecom
  python scripts/notify_push.py --test
  ```

---

## 🧬 双轨私有进化与 Obsidian 知识库互通 (Dual-Track Evolution & Obsidian)

1. **双轨物理隔离**：
   - 公开上游核心（开源 Git 仓库）：标准工程与内置工具集；
   - 用户私有进化（`.evolution/` 目录）：独立 Git 仓库，存放个人习惯、私有技能与凭据；
   - **更新零风险**：上游 `git pull origin main` 绝不会覆盖或冲突你的私有进化资产！
2. **Obsidian 知识库自适应同步**：
   - 支持本地路径（如 `D:\ObsidianVault`）与在线知识库 URL（如 `https://your-wiki.example.com`）；
   - 支持填写访问密钥 / Bearer Token，**均可留空**；
   - **首次自适应判定**：自动探测本地知识库与 Git 关联，决定 `git_sync` / `local_folder` / `online_api` / `hybrid` 同步方式。
  ```bash
  # 自动侦测与查看状态
  python scripts/obsidian_bridge.py --status

  # 填入在线知识库与密钥 (可留空)
  python scripts/obsidian_bridge.py --set-online "https://your-wiki.example.com" --set-token "secret_token"
  
  # 清空在线配置回退至纯本地
  python scripts/obsidian_bridge.py --clear-online
  ```

---

## 📜 许可证 (License)

本项目基于 [MIT License](LICENSE) 开源发布。内部收拢的成员技能遵循其各自原始开源协议。
