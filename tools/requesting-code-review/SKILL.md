---
name: requesting-code-review
description: "Ask for a review that can actually find something: hand over verifiable context instead of a summary, self-review the diff first, and keep the change small enough to read. Use before requesting review from a human or another agent, when opening a pull request, when a change is large or touches shared code, or when the user asks for review / 审查 / PR 请人看."
---

# Requesting Code Review（请人审查）

## 核心原则

**审查者需要的是可验证的上下文，不是你的总结。**

「帮我看看」之所以没效，不是审查者不认真，而是**他无法验证你的判断**。你说「已经测试通过」，他只能选择信或不信；你给他命令和输出，他能自己判断。

## 请求前必做：自审先行

在把 diff 递出去之前，自己完整读一遍（`git diff` 而不是你记忆里的改动）。自审能拦下的东西，不要让审查者当第一读者：

- 调试残留（`print` / `console.log` / 注释掉的代码 / TODO 没主）
- 与任务无关的改动（格式化整文件、重命名、升级依赖）
- 调试用的硬编码值、临时路径、本机专用配置
- 该提交但没提交的（新文件忘了 `git add`）

## 请求包：五项必填

| 项 | 内容 | 为什么 |
|---|---|---|
| **改了什么** | 涉及的文件 + 每个的一句话作用 | 让他知道从哪看 |
| **为什么** | 解决的问题 / 原因（不是“需求要求”） | 否则无法判断设计对不对 |
| **怎么验证** | 可重跑的命令 + 你看到的结果 | 让他自己跑一遍，不靠你转述 |
| **已知风险** | 你不确定的地方 / 刻意的权衡 | 主动交代比被问出来好 |
| **想看什么** | 希望重点审的方面（设计 / 边界 / 性能） | 避免他把时间花在不重要的地方 |

**第三项是分水岭**：没有可重跑的验证命令，审查就只能靠读代码推理，效率和准确度都会大幅下降。

## diff 大小的纪律

审查质量与 diff 大小成反比。超出以下规模时先拆（见 `incremental-implementation`）：

| 规模 | 建议 |
|---|---|
| < 200 行 | 直接送审，一次看完 |
| 200～800 行 | 可以，但要分区域指出重点 |
| > 800 行 | **先拆成多个可独立审的提交**，不要一次丢出去 |
| 含全文重排格式 | 单独一个提交，不与逻辑改动混在一起 |

## 反合理化表

| 你会想 | 现实 |
|---|---|
| 「审查者自己看 diff 就行了」 | 他看不到你为什么这么改，只能推测意图 |
| 「我先说明一下我的思路」 | 思路要紧跟代码；长篇叙述会把审查者带偏 |
| 「测试都过了，应该没问题」 | “应该”不是证据；把命令和输出给出去 |
| 「这个改动很大，一次看完吧」 | 大 diff 的审查结果通常是“看不完，随便提几条” |
| 「这个小问题不好意思说」 | 主动交代已知风险正是请审查的价值之一 |

## 红线信号（STOP）

- 请求里只有「帮我看看」或「审查一下」，没有验证命令
- 自己没读过完整 diff 就递出去
- 调试残留让审查者发现（那是你自审能拦的）
- 把多个不相关改动捆在一次请审里
- 请了审查却不回应意见（那就不是请审查，是要背书）

## 与 auto-skills 台账的结合

请审查与收意见都落台账，让「这个切片被谁审过、结论是什么」可追溯：

```bash
python scripts/auto_router.py trace requesting_code_review "请审: <范围> | 验证: <命令> → <结果>" --stage verify --query "<任务关键词>" --project-root "<工程根>"
```

收到意见后按 `receiving-code-review` 逐条分类回应（接受 / 讨论 / 推迟）—— **本技能管「怎么请」，那个管「怎么接」**，两者成对使用。

## 边界

本技能管**请审查的质量**；收意见是 `receiving-code-review`，完成前自查是 `verification-before-completion`，切片划分是 `incremental-implementation`。
