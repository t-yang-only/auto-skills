---
name: skill-discovery
description: >
  搜索并评估社区 Agent Skill。当用户要 find/install skill、问「有没有
  skill 能做 X」、或需从 skills.sh / SkillNet 发现能力时使用。
---

# Skill Discovery

## 搜索流程

### 1. 明确需求

- 领域（React、测试、部署…）
- 具体任务（写测试、PR review…）
- 目标 agent（默认 Cursor）

### 2. 搜索（按优先级）

```bash
# skills.sh CLI
npx skills find <关键词>

# 可选：SkillNet MCP（若已配置）
# skillnet search "<keyword>" --limit 5
```

也可浏览 [skills.sh](https://skills.sh/) 排行榜。

### 3. 安装前校验

| 检查项 | 标准 |
|--------|------|
| 安装量 | 优先 1K+；<100 需谨慎 |
| 来源 | 优先 vercel-labs、anthropics、microsoft 等 |
| 审计 | `skillshare audit <path-or-url>`（若已安装） |
| 脚本 | **禁止**自动执行 skill 内脚本，须人工审阅 |

### 4. 安装

```bash
npx skills add <owner/repo@skill-name> -g -a cursor -y
```

可选收编到 hub：

```bash
skm adopt --dry-run
skm adopt --yes
skm enable <skill-name> --for cursor
```

### 5. 团队推荐清单

查看 `word/config/recommended-skills.json`，可用：

```powershell
cd word
.\scripts\install-skills.ps1          # dry-run，仅打印命令
.\scripts\install-skills.ps1 -Apply     # 实际安装
```

## 未找到时

1. 说明无匹配 skill
2. 用通用能力直接帮助用户
3. 建议 `npx skills init my-skill` 自建，或添加到 `word/skills/`

## 禁止

- 仅凭搜索结果推荐，不校验来源与安装量
- 未经用户确认批量安装
- 将 token 写入 skill 或安装命令
