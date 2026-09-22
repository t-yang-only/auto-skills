---
name: test-driven-development
description: "Test-Driven Development (TDD) Red-Green-Refactor discipline: Write failing tests before implementation logic. Use when implementing a feature or fixing a bug whose behavior is testable, when adding regression coverage, or when the user asks for TDD / test-first / red-green-refactor."
---

# Test-Driven Development (TDD 测试驱动开发)

实施业务逻辑、修补 Bug 或变更系统行为时的标准红绿重构铁律：

## 1. 红灯阶段 (RED: 编写失败用例)
- 在写任何功能代码前，先写测试用例；
- 运行测试并**亲眼确认测试失败 (RED)**，验证测试确实在检查预期的断言而不是误报通过；
- 遵循测试金字塔：80% 单元测试、15% 集成测试、5% 端到端测试。

## 2. 绿灯阶段 (GREEN: 最快速度跑通)
- 编写满足测试的最小代码量；
- 不追求过早优化与完美设计，以「尽快变绿灯」为第一目标；
- 确认全部测试套件 100% 绿灯通过。

## 3. 重构阶段 (REFACTOR: 消除异味)
- 在绿灯保护伞下重构实现：消除重复、改善命名、提取函数；
- 遵循 YAGNI 原则与职责单一原则；
- 每次微调后立即重跑测试，确保始终保持绿灯。

## 完成判据

- 每个新行为都有对应测试，且该测试**在实现前确实失败过**（没红过的测试不知道在测什么）
- 断言检查的是行为，不是实现细节 —— 重命名内部函数不该让测试变红
- 全套测试绿灯，且不是靠放宽断言或跳过用例换来的
- 重构阶段每步之后仍全绿
- 没有"先写实现再补测试"的环节（那测的是已经知道的结果）
