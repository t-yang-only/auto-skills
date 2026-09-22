---
name: nm-skills
description: >
  多 Agent 原子任务认领、互斥排他锁与台账协调引擎 (v2.0 升级版)。在项目根目录自动建立并维护 agent_word/。
  核心解决：多 Agent 并发同步时抢跑同一任务的竞争冲突 (Race Condition)、同号序号冲突及文件覆盖。
  提供原子任务认领 (claim)、租约排他锁 (Lease with TTL)、文件防撞检查、状态看板 (board) 与完成归档 (done)。
  当用户要求 NM skills、牛马技能、工作登记、Agent 台账、多 Agent 协作排他锁、防重复任务或跨客户端同步时使用。
---

# NM-Skills (牛马多 Agent 协同与排他锁中枢 v2.0)

面向同一个工程目录下的多个 Agent（Codex、Cursor、DeepSeek Harness、Claude Code、WorkBuddy、豆包等），建立**排他性原子任务认领机制**与统一、可回溯的工作台账，**彻底解决多 Agent 在并发同步时同时进行同一个任务、或者产生同号冲突的严重痛点！**

---

## 1. 为什么必须使用 NM-Skills v2.0？

在复杂工程或多 Agent 并行环境中，缺乏协调锁会导致灾难：
1. **任务撞车 (Duplicate Work)**：Agent A 与 Agent B 同时看到某个未完成的缺陷或需求，各自开干并提交，导致代码逻辑冲突覆写；
2. **序号冲突 (ID Collision)**：多个 Agent 读取到相同的历史最大编号，并发自增生成相同的编号（如产生多份 015、016）；
3. **僵尸阻塞 (Stale Deadlock)**：某 Agent 认领任务后由于报错或超时崩溃退出，任务永久挂在“进行中”状态无人敢碰。

**NM-Skills v2.0 引入分布式原子租约锁 (Lease with TTL)**，杜绝以上所有乱象！

---

## 2. 目录约定 (`agent_word/`)

以当前工程根目录为基准，统一规范为：

```text
<工程根目录>/
`-- agent_word/
    |-- README.md           # 台账与排他协调规范
    |-- 任务认领表.md       # 实时任务排他看板 (TODO / CLAIMED / IN_PROGRESS / DONE)
    |-- 工作登记表.md       # 历史任务流水总表 (严格单调防撞编号)
    |-- 工作日志.md         # 按时间顺序追加的详细工作汇报与复盘
    |-- 技能建议.md         # 汇总本项目已验证的 Skill / MCP / 工具
    |-- API变更.md          # 接口协议变更追溯
    |-- 文件清单.md         # 文件创建与修改追溯
    `-- .locks/             # 原子协调锁与任务租约文件 (系统自动管理)
```

> **运行时状态，不进版本库**：`agent_word/` 记录的是本机各 Agent 的实时认领与工作日志，
> 属本地协作状态而非项目源码。使用本技能的工程应在 `.gitignore` 里加入 `agent_word/`，
> 否则每次认领都会把台账提交进仓库，并与其他机器/他人的状态互相覆盖。

---

## 3. 多 Agent 协同铁律与生命周期

### 阶段 1：动手前【原子认领任务】(Claim)
**铁律：在修改任何代码、创建任何文件前，必须先执行认领！**
```bash
python scripts/nm_register.py claim --task-id "TASK-AUTH-01" --task "重构系统认证与JWT逻辑" --client CODE --files "auth.py,jwt.go"
```
- 若任务未被认领：获得独占锁，租约默认 45 分钟，自动分配全局唯一单调编号 (如 `NM-CODE-001`)；
- **若任务已被他人进行中**：系统立即拦截并报错，输出当前持有者名称、认领时间及剩余租约，**强行禁止重复进行同一任务**！

### 阶段 2：实时查看看板 (Board)
随时查看当前谁在做什么、租约还剩多久、涉及哪些文件：
```bash
python scripts/nm_register.py board
```

### 阶段 3：任务完成【解除排他锁并归档】(Done)
任务完成并验证通过后，释放排他锁，并自动将详细总结追加到 `工作日志.md`：
```bash
python scripts/nm_register.py done \
  --task-id "TASK-AUTH-01" \
  --changes "完成 JWT 鉴权迁移与过期校验" \
  --api "/api/v1/auth/login, /api/v1/auth/refresh" \
  --files "auth.py,jwt.go" \
  --skills "nm-skills,security-best-practices" \
  --tools "edit,pwsh"
```

### 阶段 4：遇错放弃或释放 (Release)
若任务中途遇到不可抗力需要放弃或转交他人：
```bash
python scripts/nm_register.py release --task-id "TASK-AUTH-01" --reason "等待后端接口就绪"
```

### 阶段 5：清理超时僵尸锁 (GC)
超过租约 TTL 的崩溃会话锁会被自动回收：
```bash
python scripts/nm_register.py gc
```

---

## 4. 客户端身份标识规范

| 客户端 | 标识代码 | 示例编号 |
|---|---|---|
| OpenAI Codex | `CODE` | `NM-CODE-001` |
| Cursor | `CUR` | `NM-CUR-002` |
| DeepSeek Harness | `DS` | `NM-DS-001` |
| Claude Code | `CLAUDE` | `NM-CLAUDE-003` |
| WorkBuddy-AI | `WB` | `NM-WB-001` |
| 豆包 / Doubao | `DB` | `NM-DB-002` |
