---
name: systematic-debugging
description: "4-phase disciplined root-cause debugging: Reproduce -> Localize -> Fix -> Regression-Proof before making arbitrary code edits."
---

# Systematic Debugging (系统性根因调试)

在修改任何代码之前，必须严格执行 4 步根因诊断环，杜绝「碰运气式改代码」与「掩盖式修补」：

## 阶段 1：确定性复现 (Reproduce)
- 编写最小可复现用例 (Minimal Reproducible Example) 或测试脚本；
- 明确期望行为 (Expected) 与实际错误表现 (Actual)；
- 严禁在无法稳定复现时凭猜测直接修改代码。

## 阶段 2：根因定位与反向追踪 (Localize & Trace)
- 顺着调用栈、日志与数据流反向溯源，找到最初破坏状态的代码行；
- 区分「诱发故障的根本原因 (Root Cause)」与「中途暴露的次生表象 (Symptom)」；
- 提出明确的可证伪假说，并通过微探针或单元测试验证假说。

## 阶段 3：微创单点修复 (Single Surgical Fix)
- 仅做解决根因所必需的最小修改；
- 遵循防守反击与深度防御 (Defense-in-Depth) 原则，在边界处做健全性校验；
- 严禁顺手大面积重构无关代码或引入未经评估的新依赖。

## 阶段 4：防退化守卫 (Regression Prevention)
- 将复现用例沉淀为自动化回归测试，确保新代码绿灯通过且老用例不红；
- 审计同类模式在全仓库中是否存在隐患。
