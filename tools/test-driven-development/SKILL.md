---
name: test-driven-development
description: "Test-Driven Development (TDD) Red-Green-Refactor discipline: Write failing tests before implementation logic."
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
