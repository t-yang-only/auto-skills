---
name: verification-before-completion
description: "Evidence before claims: run the real verification command and READ its output BEFORE saying done / fixed / passing / working, before committing, and before reporting to a user. Use whenever about to express satisfaction or completion, when tempted to write 'should work' / 'probably fine' / 'seems fixed', or when trusting another agent's success report. 触发场景：即将说「完成了/修好了/测试通过/应该没问题」之前、提交或推送之前、向用户汇报之前。"
---

# Verification Before Completion（完成前验证）

## 核心原则

**证据先于断言（Evidence before claims, always）。**

违反这条规则的**字面**，就是违反它的**精神**。

## 铁律

```
没有新鲜验证证据，不得声称任何完成状态。
```

**本回合没有跑过验证命令，就不能说它通过。**

## 验证闸门（Gate Function）

在声称任何状态或表达满意之前，必须走完五步：

1. **IDENTIFY** —— 哪条命令能证明这个断言？
2. **RUN** —— 完整执行它（新鲜、完整，不是"刚才跑过"）
3. **READ** —— 读完整输出，看退出码，数失败数
4. **VERIFY** —— 输出真的支持这个断言吗？
   - 否 → 如实说出实际状态 + 证据
   - 是 → 带证据说出断言
5. **ONLY THEN** —— 此时才允许下结论

**跳过任何一步 = 说谎，不是验证。**

## 常见失败对照

| 断言 | 需要什么 | 不够 |
|---|---|---|
| 测试通过 | 测试命令输出：0 failures | 上次跑的结果、"应该能过" |
| Lint 干净 | Linter 输出：0 errors | 部分检查、外推 |
| 构建成功 | 构建命令 exit 0 | Lint 过了、日志看着没问题 |
| Bug 修好了 | 复现原症状的测试通过 | 改了代码、假定修好了 |
| 回归测试有效 | 红-绿循环验证过 | 测试通过一次 |
| Agent 完成了 | VCS diff 显示改动 | Agent 自报"成功" |
| 需求满足 | 逐条 checklist | 测试通过 |

## 红线信号（STOP）

- 用 "should" / "probably" / "seems to" / "应该" / "大概" / "看起来"
- 在验证之前表达满意（"太好了" / "完美" / "搞定了"）
- 未经验证就要 commit / push / PR
- 相信 agent 的成功自报
- 依赖部分验证
- "就这一次"
- 累了、想收工
- **任何暗示成功但没跑验证的措辞**

## 借口与现实

| 借口 | 现实 |
|---|---|
| "现在应该能用了" | 去跑验证 |
| "我有信心" | 信心 ≠ 证据 |
| "就这一次" | 没有例外 |
| "Linter 过了" | Linter ≠ 编译器 |
| "Agent 说成功了" | 独立验证 |
| "我累了" | 疲惫不是借口 |
| "部分检查够了" | 部分什么都证明不了 |
| "换个说法规则就不适用" | 精神高于字面 |

## 关键模式

**测试：**
```
正确：[跑测试] [看到：34/34 通过] → "全部通过"
错误："现在应该能过了" / "看着对"
```

**回归测试（TDD 红-绿）：**
```
正确：写 → 跑（通过）→ 撤销修复 → 跑（必须失败）→ 恢复 → 跑（通过）
错误："我写了回归测试"（没做红-绿验证）
```

**构建：**
```
正确：[跑构建] [看到：exit 0] → "构建通过"
错误："Linter 过了"（Linter 不检查编译）
```

**需求：**
```
正确：重读计划 → 建 checklist → 逐条验证 → 报告缺口或完成
错误："测试通过，阶段完成"
```

**委派给子 agent：**
```
正确：Agent 自报成功 → 查 VCS diff → 验证改动 → 报告实际状态
错误：直接相信 agent 的报告
```

## 何时必须应用

**永远在这些之前：**
- 任何形式的成功/完成断言
- 任何满意表达
- 任何关于工作状态的正向陈述
- Commit、建 PR、任务完成
- 进入下一个任务
- 委派给 agent

**规则覆盖：**
- 精确措辞
- 同义改写
- 暗示成功的语气
- 任何暗示完成/正确的表达

## 与 auto-skills 台账的结合（本技能特有）

本技能不只约束措辞 —— **把验证证据落进台账**，让"验证过"可追溯、可审计：

1. **验证通过后写轨迹**（`tool_execution_traces`）：

   ```bash
   python scripts/auto_router.py trace verification_before_completion \
     "验证: <命令> → <结果>" --stage verify --status SUCCESS \
     --query "<本次任务一句话>" --project-root "<项目根>"
   ```

   验证**失败**时用 `--status FAILED`，并在 summary 里写清失败原因 —— 失败证据同样有价值（`experience_mining` 会挖到）。

2. **多 Agent 协作场景**：声称完成前先走 `nm-skills` 的 `done` 记录工作日志；若验证没过，不要 `done`，改为记录阻塞原因。

3. **证据要能被别人复现**：写进 summary 的必须是**可重跑的命令 + 真实输出摘要**，不是"已验证"三个字。

## 一句话

**能被别人重跑的，才叫证据；跑不出来的，只是说法。**
