---
name: receiving-code-review
description: "Handle code review feedback without defensiveness: read all of it first, classify each item (real issue / misread / partly right / style preference), fix what is real, explain what is not with evidence, and reply per item. Use when receiving review comments on a PR or diff, when a reviewer or user points out problems in your code, or when asked to address review findings. 触发场景：收到代码审查意见、PR review 反馈、用户指出代码问题、被要求处理 review 结论时。"
---

# Receiving Code Review（接收代码审查反馈）

## 核心原则

**审查意见不是攻击，是免费的第二双眼睛。**

写代码的人对自己的实现有盲区 —— 审查者的价值恰恰在于那些盲区。**把"被指出问题"当成信息，不是当成评价。**

## 三条铁律

1. **先读完，再开口** —— 不要边读边辩解，那会让你只看见能反驳的那几条
2. **逐条回应，不打包** —— 每条意见都要有明确结论，不能合并成"已处理"
3. **不同意要说理，不要沉默** —— 沉默等于默认接受，会让真问题被埋掉

## 处理流程

### 1. READ —— 完整读完

把全部意见读完再动手。中途开始改会让你漏掉后面的意见，或做出与后文矛盾的修改。

### 2. CLASSIFY —— 分四类

| 类别 | 判据 | 动作 |
|---|---|---|
| **真问题** | 能复现、能举出反例、违反明确约定 | 改，并补验证 |
| **误判** | 审查者基于错误前提 | 说明前提为什么不对，**附证据** |
| **部分对** | 指出的现象对，归因或方案不对 | 改对的部分，说明保留的部分 |
| **风格偏好** | 无客观对错 | 按项目既有约定决定，说明取舍理由 |

**分类不是推卸** —— 是把"真问题"和"偏好"分开，让真问题得到足够重视。

### 3. FIX —— 只改真问题

改动范围以"关闭这条意见"为界。**不要顺手重构**（会让 review 变成滚雪球，也让审查者无法核对）。

### 4. VERIFY —— 改完必须验证

见 `verification-before-completion`：跑测试、读输出、拿到证据。**"已按意见修改"不是证据，测试通过才是。**

### 5. REPLY —— 逐条回应

格式：

```
[意见 1] 真问题 → 已修（commit abc1234），新增回归测试 X 通过
[意见 2] 误判 → 未改。该分支在 Y 条件下不可达，见 test_z 用例第 12 行
[意见 3] 部分对 → 已改 A 部分；B 部分保留，因为 <理由 + 证据>
[意见 4] 风格 → 按项目 .editorconfig 保留现写法
```

**每条都要有结论**，哪怕结论是"不改"。

## 红线（不要做）

- 说"你说得对"然后什么都不改（敷衍）
- 辩解式回应（以"但是…"开头，把回应变成辩护）
- 把多条意见合并成一句"已处理"
- 改了但没验证
- 对不同意的那几条**沉默跳过**（最常见的失职）
- 为了显得配合而改掉自己确认正确的地方

## 特别提醒：区分「审查者错」和「我看不懂」

在判定"误判"之前，先确认自己真的理解了这条意见。**把没读懂的意见归到"误判"，是最贵的错误** —— 它同时得罪了审查者和代码质量。

判定"误判"的门槛：**能用一句话说出审查者假设的前提，并指出那个前提为什么不成立**。说不出来，就是还没读懂。

## 与 auto-skills 台账的结合

处理完审查反馈后落一条轨迹，让"审查→修改→验证"这条链可追溯：

```bash
python scripts/auto_router.py trace receiving_code_review \
  "审查意见 N 条：真问题 X / 误判 Y / 部分对 Z；已验证 <命令> → <结果>" \
  --stage verify --status SUCCESS --query "<本次审查主题>" --project-root "<项目根>"
```

若某条意见引发的改动**验证失败**，用 `--status FAILED` 并在 summary 里写清是哪条 —— 失败证据对 `experience_mining` 同样有价值。

## 一句话

**审查者给你的是问题清单，不是判决书；你要交付的是逐条结论，不是态度。**
