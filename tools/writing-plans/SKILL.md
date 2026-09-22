---
name: writing-plans
x-category: design
description: "Turn an agreed direction into a step-by-step plan someone else can execute: each step is one verifiable, committable slice with its own acceptance and rollback point. Use before starting multi-step work, when handing work to another agent or a future session, when the user asks for a plan / 计划 / 方案 / 拆任务, or when a task is big enough that starting immediately would mean improvising."
---

# Writing Plans（写计划）

## 核心原则

**计划的价值在于减少执行时的决策。**

如果执行者（人或 agent）读完计划还要重新想「下一步该做什么」，那就不是计划，是一份愿望清单。

一份能执行的计划，每一步都应能回答：**做什么 / 怎么知道它成了 / 失败了怎么办**。

## 最小结构（五段，不多不少）

| 段 | 内容 | 缺了会怎样 |
|---|---|---|
| **目标** | 一句话说清最终交付什么（不是过程） | 做到一半不知道为什么在做 |
| **前置条件** | 已经确定的事实、环境、依赖 | 执行时才发现前提不成立 |
| **步骤** | 每步 = 一个可验证、可提交的切片 | 步骤太大，做完才能验证，错了很贵 |
| **验收标准** | 可重跑的命令 + 预期输出 | 无法判断「算不算完成」 |
| **回滚点** | 出事了退回哪里（提交、备份、开关） | 不敢往前走，或出事后无处可退 |

## 步骤的粒度

**一步 = 一次可提交的改动。**

判据：如果一步做到一半时你不敢提交，说明这一步太大或不够垂直。

- ✗「改完整个认证模块」——没法中途验证
- ✗「把所有文件的 import 改成新写法」——横向切片，改完一半系统是坏的
- ✓「新旧两条路径并存，默认走旧路，老行为逐字不变（提交 1）」
- ✓「切默认到新路径，旧路径保留一个版本（提交 2）」
- ✓「删掉旧路径（提交 3）」

切片方法详见 `incremental-implementation`；并行执行时的物理隔离见 `using-git-worktrees`。

## 什么时候不需要写计划

不要把计划当仪式：

- 一步就能做完（改一个字符串、跑一条命令），直接做
- 方向还没定（正在 brainstorming），先把方向定下来再写计划
- 纯探索性的「先看看它长什么样」，直接看

判据：**你能不能在一次回合内做完并验证？** 能，就别写计划。

## 反合理化表

| 你会想 | 现实 |
|---|---|
| 「写计划太耗时，直接开干」 | 没计划时的返工与迷路更贵；但一步能完成的事不在此列 |
| 「步骤写粗一点，执行时再细化」 | “执行时再想”就是为什么会跑偏；粗粒度的部分要明确标为「待定」 |
| 「验收标准就写「测试通过」吧」 | 哪个测试、什么输出算通过？不能重跑的标准等于没标准 |
| 「回滚点不用写，肯定没事」 | 写回滚点的成本是一行字，不写的成本是出事时的一场混乱 |
| 「计划写完就算交付了」 | 计划是为了执行；写完不执行的计划是文档污染 |

## 红线信号（STOP）

- 步骤里出现「然后看情况」「大概改一下」「其余同上」
- 某一步需要改十几个文件且中途不可验证
- 验收标准里没有一条可重跑的命令
- 计划里写了具体的数值/路径/提交号，但你并没有真的核对过它们
- 把探索当执行：计划里的步骤依赖「还不知道行不行」的前提

## 与 auto-skills 台账的结合

计划落实到台账上，每个步骤就是一个可认领的任务（多 Agent 场景下不会抢跑）：

```bash
# 每一步占一个认领，--files 声明该步涉及的文件
python scripts/auto_router.py claim --task "计划第 1 步: <做什么>" --client CODE --files "<文件列表>"
python scripts/auto_router.py done --task-id <id>
```

计划本身也值得留痕（供事后回看「当初为什么这么拆」）：

```bash
python scripts/auto_router.py trace writing_plans "计划: <目标> | <N> 步" --stage plan --query "<任务关键词>" --project-root "<工程根>"
```

交接给未来会话时，计划要能独立读懂——不要写「如上所述」「按前面的思路」，那些指向的是你当时的上下文，而它已经不在了。

## 边界

本技能管**怎么把已定方向拆成可执行步骤**；方向本身尚未定时先用 `brainstorming`，切片原则见 `incremental-implementation`，执行中的完成判定见 `verification-before-completion`。
