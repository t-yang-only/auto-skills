---
name: git-guardrails
x-category: verify
description: 给 AI agent 装 git 防护钩子，在破坏性命令执行前拦下它们。当用户要防止 agent 误用 git push / reset --hard / clean -f / branch -D，或要给项目加 git 安全网时使用；也适用于把已有的 .githooks 扩展成完整拦截清单。触发词：git 防护、危险 git 命令、防误删、git 安全钩子、拦截 push。
---

# Git 防护栏

agent 与人类在 git 上的失败模式不同：人**犹豫**，agent**执行**。一条 `git reset --hard` 在人的手里通常经过三次确认，在 agent 的手里可能只是它"清理工作区"的一步。

## 拦什么

| 命令 | 为什么危险 |
|---|---|
| `git push`（含 `--force`） | 推送不可撤回；force 会覆盖远端历史 |
| `git reset --hard` | 丢弃未提交改动，没有回收站 |
| `git clean -f` / `-fd` / `-fdx` | 删除未跟踪文件 —— 新写的文件往往正是未跟踪的 |
| `git branch -D` | 强删分支，未合并的提交随之消失 |
| `git checkout .` / `git restore .` | 整目录丢弃改动 |

**`-fdx` 比 `-fd` 更危险**：它会连 `.gitignore` 里被忽略的文件一起删（本地配置、密钥、虚拟环境）。

## 三层防线（从外到内）

**1. agent 钩子层** —— 拦在命令执行前
Claude Code 用 `PreToolUse` 钩子 + matcher `Bash`；DSH / Codex 用各自的 hook 机制，或包一层 shell wrapper。

**2. git 原生层** —— 拦在协议层
`git config core.hooksPath` 指向仓库内的 `.githooks/`（本仓库已用这个机制做隐私闸门，是现成范例）；服务端另有分支保护与 `receive.denyNonFastForwards`。

**3. 习惯层** —— 不靠拦截，靠替代动作
`--force-with-lease` 代替 `--force`（远端被别人更新时会失败）；`git stash` 代替 `reset --hard`（可恢复）；`git branch -d` 代替 `-D`（未合并时会拒绝）。

## 安装步骤

1. **先问作用域**：只装本项目，还是所有项目？
2. **写拦截脚本**：读 stdin 的 JSON，取 `tool_input.command`，命中清单就 exit 2 并把原因写 stderr
3. **挂到钩子配置**：已有配置就**合并**进 `hooks.PreToolUse` 数组，不覆盖其他设置
4. **问是否调整清单**：默认清单 + 用户项目特有的危险命令
5. **验证**（必须真跑）：

```bash
echo '{"tool_input":{"command":"git push origin main"}}' | <脚本路径>
# 期望：exit 2，stderr 出现 BLOCKED

echo '{"tool_input":{"command":"git status"}}' | <脚本路径>
# 期望：exit 0，无输出
```

**只测拦截不测放行是不够的** —— 一个把所有命令都拦下的脚本看起来"很安全"，实际会让 agent 完全无法工作。

## 反合理化表

| 借口 | 现实 |
|---|---|
| "我会小心，不用装钩子" | 钩子的价值恰恰在于不依赖当次判断 |
| "只拦 push 就够了" | `clean -fdx` 造成的损失比 push 更难恢复 |
| "先装上，回头再验证" | 没验证过的钩子可能是"永远放行"或"永远拦截"，两者都比没有更糟 |
| "钩子会碍事" | 只拦 5 条命令的钩子不会碍事；会碍事的是拦了 50 条的 |
| "本地钩子能防住一切" | 钩子可被 `--no-verify` 绕过，它是安全带不是防弹衣 |

## 完成判据

- 拦截清单里的每条命令都实测被拦（exit 2 + BLOCKED 消息）
- 至少一条**正常命令**实测放行（exit 0）—— 防止脚本退化成"全部拦截"
- 钩子配置是**合并**进去的，没有覆盖既有设置
- 作用域明确（项目级 / 全局），用户知道它装在哪
- 已如实说明它可被 `--no-verify` 绕过（防护边界要讲清，不夸大）
