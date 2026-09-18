# NM-Skills 🐂🐎 (牛马多 Agent 协同与排他锁中枢)
> **Atomic Task Claiming, Mutual Exclusion Lease & Distributed Work Ledger Engine (v2.0)**  
> 专为解决多 Agent 并发同步时「抢跑同一任务」、「同号序号冲突」与「文件冲突覆写」而生的排他性协同中枢。

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Agent Skills Ready](https://img.shields.io/badge/Agent%20Skills-Standard-green.svg)](https://agentskills.io/)
[![Zero Race Conditions](https://img.shields.io/badge/Concurrency-Atomic%20Lease%20Lock-brightgreen.svg)]()

---

## 🌟 核心痛点与解决方案 (Why NM-Skills v2.0?)

在同一个项目目录下，当多个 AI 编程代理（Codex、Cursor、DeepSeek Harness、Claude Code、WorkBuddy、豆包）协同作业时，极易陷入混乱：
1. **任务撞车 (Race Condition)**：两个 Agent 同时发现同一个缺陷，分别开工修改，提交时造成冲突覆盖；
2. **同号序号冲突**：缺乏原子分配器，两个 Agent 同时读取最大编号，双双分配出 `015` 或 `016`；
3. **僵尸阻塞**：某 Agent 崩溃退出，任务永久挂在“进行中”状态。

**NM-Skills v2.0 引入分布式原子租约排他锁 (Lease with TTL)**，彻底解决上述所有问题！

---

## 🏗️ 目录规范 (`agent_word/`)

在项目根目录下自动建立并维护 `agent_word/`：

```text
agent_word/
├── README.md           # 台账与排他协调说明
├── 任务认领表.md       # 实时排他认领看板 (TODO -> CLAIMED -> IN_PROGRESS -> DONE)
├── 工作登记表.md       # 历史任务流水总表 (严格单调递增编号)
├── 工作日志.md         # 按时间追加的详细工作汇报与复盘
├── 技能建议.md         # 推荐 Skill / MCP / 工具沉淀
├── API变更.md          # 接口协议变更追溯
├── 文件清单.md         # 文件创建与修改清单
└── .locks/             # 原子排他锁与租约文件 (系统自动管理)
```

---

## 🚀 核心工作流与 CLI 命令

### 1. 动手前原子认领任务 (Claim)
在修改任何文件前，必须显式抢占任务锁：
```bash
python scripts/nm_register.py claim --task-id "TASK-AUTH-01" --task "重构系统认证模块" --client CODE --files "auth.py"
```
- 若任务空闲：成功加锁（默认租约 45 分钟），分配唯一单调编号 (如 `NM-CODE-001`)；
- **若任务已被他人进行中**：系统立即拦截并报错，输出当前持有者与剩余租约，**强行禁止重复进行同一任务**！

### 2. 实时查看看板 (Board)
```bash
python scripts/nm_register.py board
```

### 3. 任务完成解除锁 (Done)
```bash
python scripts/nm_register.py done \
  --task-id "TASK-AUTH-01" \
  --changes "完成 JWT 鉴权迁移与过期校验" \
  --files "auth.py" \
  --skills "nm-skills"
```

### 4. 任务释放或放弃 (Release)
```bash
python scripts/nm_register.py release --task-id "TASK-AUTH-01" --reason "前置接口未就绪"
```

### 5. 清理超时僵尸锁 (GC)
```bash
python scripts/nm_register.py gc
```

---

## 📜 许可证 (License)

本项目基于 [MIT License](LICENSE) 开源发布。
