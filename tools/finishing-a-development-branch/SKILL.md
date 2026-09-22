---
name: finishing-a-development-branch
x-category: handoff
description: "Close out a branch properly: verify before merging, pick the right merge shape, clean up the worktree and the task ledger, and leave a record when the work is abandoned instead of merged. Use when a branch or worktree is done, before merging / 合并 / 收尾, when the user asks to wrap up / 收尾 / 合并分支, or when work is about to be discarded."
---

# Finishing a Development Branch（分支收尾）

## 核心原则

**分支做完了 ≠ 可以合并了。**

代码能跑、测试绿了，只说明「这份改动本身没坏」。合并还要回答：**审查意见处理了吗 / 调试残留清了吗 / 提交信息能让人看懂吗 / 文档同步了吗**。

## 合并前清单（一条不过就别合）

| 项 | 判据 |
|---|---|
| **验证** | 有新鲜的可重跑证据（见 `verification-before-completion`），不是「刚才跑过」 |
| **审查** | 提出的问题已逐条处理；未处理的要明确说为「接受风险」而不是默默带过（见 `receiving-code-review`） |
| **残留** | 无调试输出、无临时路径、无硬编码的本机值、无注释掉的代码 |
| **提交** | 每个提交只做一件事；提交信息说明「为什么」而不只是「改了什么」 |
| **文档** | 行为变了就改文档；文档里的计数、路径、命令都还对得上 |
| **台账** | 任务认领已释放（否则别人永远认领不了这个任务） |

## 合并形状的选择

| 形状 | 适用 | 代价 |
|---|---|---|
| **squash** | 分支里有大量「边做边改」的中间提交，最终只想留一条干净记录 | 丢失探索过程（若过程有价值，先写进经验库） |
| **merge** | 分支本身有意义（并行开发、需要保留分支结构） | 历史变成图，回溯变难 |
| **rebase** | 未推送的本地分支，想让历史保持线性 | **已推送的分支绝不能 rebase**（会改变别人已拉取的历史） |

不确定时默认 **merge**：它不会静默丢掉任何东西，也不会改写历史。

## 合并后的清理

```bash
git worktree list                  # 先看清楚现在有哪些工作树
git worktree remove <path>         # 合并完成后移除对应工作树
git branch -d <branch>             # 已合并的分支（-d 会拒绝未合并的，是保护）
python scripts/auto_router.py done --task-id <id>   # 释放认领
```

并行开发时的隔离纪律见 `using-git-worktrees`。

## 不合并而放弃时

**丢弃也要留记录。** 一个花了两小时发现不可行的方案，下个人（或你自己三天后）会再试一次：

- 把「试了什么 / 为什么不行」写成一段可搜索的记录（代码可以删，结论要留）
- 分支先不删，标注原因后再删；删之前确认里面没有别人还需要的东西
- 任务台账里记一笔「不做了，因为 X」，而不是默默关掉

## 反合理化表

| 你会想 | 现实 |
|---|---|
| 「测试都绿了，直接合吧」 | 测试不检查调试残留、提交信息和文档同步 |
| 「审查意见有几条没改，不影响」 | 那就明说「接受风险」；默默带过是对审查者的不尊重 |
| 「分支先留着，以后再说」 | 未清理的 worktree 会让下一个人以为这块还在做 |
| 「任务认领不用释放，反正我做完了」 | 锁不释放 = 这个任务在台账上永远是「进行中」 |
| 「放弃就放弃，不用写什么」 | 下个人会重复走一遍同样的死路 |

## 红线信号（STOP）

- 合并前没重跑验证（“刚才还好好的”不是证据）
- 对已推送的分支执行 rebase 或 force push
- 合并后不清理 worktree / 不释放认领 / 不删已合并分支
- 放弃时不留记录（下个人必定重走）
- 为了「干净的历史」而把探索过程全部抹掉

## 与 auto-skills 台账的结合

收尾是一次可留痕的动作，不只是心里的一句「完了」：

```bash
python scripts/auto_router.py trace finishing_branch "收尾: <分支> | 合并形状=<squash|merge> | 验证: <命令> → <结果>"     --stage verify --query "<任务关键词>" --project-root "<工程根>"
```

跨会话/跨工具交接时用 `codex-project-closeout` 记一笔结论；多 Agent 并行时先看 `git worktree list` 再动手。

## 边界

本技能管**分支如何收尾**；「算不算完成」的判定见 `verification-before-completion`，工作树隔离与清理见 `using-git-worktrees`，任务认领的拿与放见 `nm-skills`。
