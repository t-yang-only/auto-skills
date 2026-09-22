---
name: diagnosing-skills
description: "Diagnose why a session or skill misbehaved: a skill that should have fired but did not, an agent that ignored its plan, repeated work, or burned far more tokens than expected. Reads the session trail and the auto-skills trace tables, reports with line-level evidence, and can package a scrubbed bundle. Use when asked to figure out what went wrong, why a skill did not trigger, why nothing got written to the database, or when a session feels off. 触发场景：会话/技能表现异常、该触发的技能没触发、落库没数据、任务重复、token 异常超支、被要求排查「刚才那次为什么不对」时。"
---

# Diagnosing Skills（会话与技能诊断）

## 什么时候用

会话表现异常，但你**看不出原因**时：

- 技能该触发却没触发（或不该触发却触发了）
- agent 忽略了既定计划、跳过步骤
- 同一件事被做了两遍
- token 消耗远超预期
- 任务卡住，日志看着"成功"但实际什么都没做
- 落库表没有数据，但脚本没报错

**先诊断，再修** —— 直接改代码通常是猜。

## 诊断四步

### 1. COLLECT —— 收集证据

不要凭印象。按顺序读这几处（auto-skills 特有的数据源）：

| 证据源 | 位置 | 能回答什么 |
|---|---|---|
| 工具调用轨迹 | `tool_execution_traces` 表 | 谁在什么时候调了什么、成功没、耗时多少 |
| 路由决策 | `router_audit_logs` 表 | 任务被分到哪条流水线、为什么 |
| 任务台账 | `nm_tasks` / `nm_work_logs` 表 | 是否走了认领锁、有没有重复认领 |
| 落库错误 | `.evolution/db_sync_errors.log` | 落库失败的**真实原因**（不再静默） |
| 死信队列 | `.evolution/db_spool/dead.jsonl` | 补传多次仍失败的记录 |
| 熔断状态 | `.evolution/db_health.json` | 是否处于熔断冷却期（表现为"什么都没写"） |

**查表示例**（用最小权限账号即可）：

```bash
python scripts/db_sync.py --doctor      # 开关 / 连通性 / 熔断 / 暂存积压 一次看全
python scripts/db_sync.py --status      # 各表当前行数
```

### 2. LOCATE —— 定位断点

找到**"本该发生但没发生"的那一步**。判据不是"哪里报错了"，而是"链路在哪一环断的"。

链路的典型环节：触发 → 路由 → 认领 → 执行 → 落库 → 归档。

**逐环验证**，而不是从结果倒推。

### 3. EVIDENCE —— 行级证据

结论必须能落到**具体的一行**：

- 表：`SELECT id, created_at, status FROM tool_execution_traces ORDER BY id DESC LIMIT 5`
- 文件：`db_sync.py:302` 定义处、`:519` 失败分支
- 日志：`[2026-09-22 09:41:07] record_tool_trace_db: ...`

**"应该是配置问题"不是证据；"配置项 X 在第 N 行为 false，而调用点在第 M 行要求它为 true"才是。**

### 4. REPORT —— 结论 + 修复 + 验证

诊断结论必须含四段：

```
现象：<可观察到的>
证据：<行号 / 事件 id / 查询语句与结果>
根因：<可验证的机制，不是猜测>
修复：<具体动作> + <怎么验证修好了>
```

## 常见故障模式与判据

| 症状 | 判据 | 常见根因 |
|---|---|---|
| 技能没触发 | SKILL.md 的 description 是否含用户会说的触发词 | 描述太窄；或 frontmatter 解析失败（**带 UTF-8 BOM 会让 `^---` 正则匹配失败**，症状是 registry 里显示「无描述」） |
| 落库没数据 | 对应表行数是否增长 | 开关未开（权威在 `.evolution/config.yaml`）；熔断打开；落库异常被静默 |
| 任务被重复做 | `nm_tasks` 是否有同题多条 | 没走认领锁，直接开工 |
| token 异常 | trace 里单次调用的耗时与输出长度 | 提示词过宽、缺终止条件；agent 反复调同一个工具 |
| 脚本"成功"但无产出 | 退出码 vs 副作用 | 只看了 `$?`，没看数据；或 `except Exception: pass` 吞掉了 |
| 定时任务"跑了"但没干活 | 执行记录 vs 实际改动 | 门槛条件写窄了（如只检查一个目录），任务在第一步就返回 |

## 导出脱敏包

需要把问题上报或交给别人时，**先脱敏再打包**：

- 去掉：密钥、令牌、服务器地址、个人绝对路径、真实账号
- 保留：时间线、事件类型、行号、报错原文、复现步骤
- 用占位符替换：`APP` / `HOST` / `TOKEN` / `PATH`

**未脱敏的轨迹不要外发** —— 轨迹里通常含完整的命令与环境信息。

## 一句话

**先证明链路在哪一环断的，再动手 —— 修在猜的地方，等于没修。**
