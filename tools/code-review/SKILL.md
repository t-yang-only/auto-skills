---
name: code-review
description: "Comprehensive multi-axis code review: correctness, security, edge cases, YAGNI, and maintainability before merge. Use when reviewing a diff, PR, or branch before merge, when the user asks for a review / 审查 / code review, or before declaring an implementation complete."
---

# Code Review & Quality Assurance (代码严审与质量守卫)

合并任何代码改动或提交 PR 前的标准多维度代码走查契约：

## 审查核心维度 (5-Axis Review)
1. **正确性与逻辑 (Correctness)**：是否满足业务契约？是否存在空指针、越界、竞态条件与并发安全隐患？
2. **安全与防御 (Security)**：是否存在注入、越权、敏感凭据硬编码、未转义输入与数据泄露？
3. **架构与开闭 (Architecture)**：模块边界是否清晰？是否违反单向依赖？是否破坏现有扩展契约？
4. **复杂度与冗余 (Simplicity)**：是否过度设计 (Over-engineering)？能否用标准库更简短替代？
5. **测试与覆盖 (Testability)**：关键逻辑与异常分支是否均有单元测试兜底？断言是否严密？

## 缺陷定级标准 (Severity Ladder)
- **BLOCKER**：导致死锁、崩溃、数据损坏或严重安全漏洞，阻断合并，必须立刻修复；
- **HIGH**：边界情况未处理、潜在性能倒退，必须修复后方可发布；
- **MEDIUM**：代码异味、命名模糊、注释过时，建议优化；
- **NIT**：微小风格建议或空格微调，不阻断主流程。

## 完成判据

- 五个维度逐个过了一遍，不是只看 diff 里最显眼的那几行
- 每个发现都带**位置 + 定级**（BLOCKER / HIGH / MEDIUM / NIT），没有悬空的"我觉得"
- BLOCKER 与 HIGH 已修复，或明确记录为阻断合并的理由
- 给出的是可执行的修改方向，不是"这里有点问题"
- 审查范围与请求范围一致 —— 顺带发现的无关问题单独记，不混进这次结论
