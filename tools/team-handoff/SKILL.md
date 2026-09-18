---
name: team-handoff
description: >
  多 Agent 协作交接协议。当任务需要在 Cursor、Codex、Claude Code 等
  agent 之间传递、续作、或 review 时使用；当用户说「交接」「handoff」
  「给下一个 agent」时使用。
---

# Team Handoff · 多 Agent 交接

## 何时使用

- 当前 agent 无法完成剩余步骤（需换工具/换模型）
- 长任务分段：设计 → 实现 → 测试 → 文档
- PR review 前需要结构化上下文

## 交接输出格式

完成任务段落后，输出以下 Markdown 块：

```markdown
## Handoff · [任务标题]

**状态**: `进行中` | `待 review` | `阻塞` | `完成`

### 已完成
- ...

### 变更文件
- `path/to/file` — 简述

### Skill 变更
- 无
- 或：新增 `skills/xxx`，需运行 `skillshare sync`

### 环境 / 命令
```bash
cd word && .\scripts\sync.ps1
```

### 下一步（给下一个 Agent）
1. ...
2. ...

### 阻塞 / 风险
- 无
- 或：...

### 参考
- AGENTS.md
- 相关 issue/PR: #
```

## 接收方 Agent 必读

1. 读 `word/AGENTS.md`
2. 若 Handoff 提到 skill 变更，先跑 sync
3. 用 `skm list --json` 确认所需 skill 已启用
4. 不要重复 Handoff 中已完成的探索步骤

## 与工具栈的关系

| 操作 | 命令 |
|------|------|
| 同步团队 skills | `skillshare sync` |
| 检查链接 | `skm doctor --json` |
| 启用 skill | `skm enable <name> --for <tool>` |
| 安装社区 skill | `npx skills add <pkg> -g -a cursor -y` |

## 禁止

- 不要在 Handoff 中粘贴密钥、token
- 不要假设下一 agent 已读过完整对话，必须写清「下一步」
