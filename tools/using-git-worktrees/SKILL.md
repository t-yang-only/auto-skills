---
name: using-git-worktrees
description: "Physical isolation for parallel agent work: one git worktree per independent task so two agents never edit the same files at the same time. Use when more than one agent or session works in the same repository, when a long-running change must not block other work, when comparing two implementations side by side, or when the user asks for worktree / 工作树 / 隔离开发."
---

# Using Git Worktrees（工作树隔离）

## 核心原则

**锁管「谁做哪个任务」，worktree 管「在哪做」。两者不互相替代。**

nm-skills 的认领锁防的是**抢同一任务**；worktree 防的是**在同一个工作树里同时改同一个文件**。只有锁时，两个 Agent 仍可能因为“顺手改了同一个文件”而互相覆盖；只有 worktree 时，两个 Agent 会各自做同一件事。

## 什么时候用

| 场景 | 用？ |
|---|---|
| 同一仓库里有两个以上 Agent / 会话并行干活 | 是 |
| 一个长任务占着工作树，但你还要做别的 | 是 |
| 要并排比较两种实现（选型 / 性能对比） | 是 |
| 改动风险高、需要一个干净的回滚位置 | 是 |
| 单人、短任务、改完就走 | 不必 |

## 基本操作

```bash
# 新建：从当前 HEAD 开一个隔离工作树（建在仓库外侧，避免被扫进仓库）
git worktree add -b feat/<任务名> ../<repo>-wt-<任务名> <基线分支>

# 查看全部工作树及其分支/状态
git worktree list

# 干完了：先确认已合并（或已推送），再删
git worktree remove ../<repo>-wt-<任务名>

# 对应分支确实不要了才删分支
git branch -d feat/<任务名>
```

**`git worktree remove` 拒绝删除有未提交改动的工作树**（除非 `--force`）——这是保护，不是阻碍。碰到拒绝先看 `git status`，不要直接加 `--force`。

## 与 nm-skills 认领的配合

认领任务时把 worktree 路径写进台账，让别人能看到“这件事在哪个目录里发生”：

```bash
python scripts/auto_router.py claim --task "<任务>" --files "<该切片要动的文件>" --client CODE
# 台账里同时记下 worktree 路径，便于合并时定位
```

三条配合纪律：

1. **一个认领对应一个 worktree** —— 不要两任务共用一个工作树，否则隔离形同虚设。
2. **认领范围（`--files`）应正好是该 worktree 里要动的文件** —— 超出范围就说明切片切错了（见 `incremental-implementation`）。
3. **合并前先看 `git worktree list`** —— 确认没有另一个活动工作树正在改同一批文件。

## 反合理化表

| 你会想 | 现实 |
|---|---|
| 「我只是快改一下，不用开工作树」 | 另一个 Agent 也是这么想的；冲突不看改动大小，只看是否同时 |
| 「我用锁了，不需要 worktree」 | 锁只管任务归属，不管文件字节；两个不同任务仍可能碰同一个文件 |
| 「分支就够了」 | 分支需要切换，切换会打断当前工作；worktree 让两个分支**同时存在于磁盘** |
| 「建完忘了删」 | 每个 worktree 都占盘；任务结束即清理，但清理前必须确认已合并 |

## 红线信号（STOP）

- 因为报 `worktree is dirty` 而加 `--force` 删除 —— 先看 `git status`，那里面可能是别人未合并的成果
- 在仓库目录**内部**建 worktree —— 会被主仓库扫进去，形成嵌套脏乱
- 合并前不看 `git worktree list` 就直接 merge —— 可能合进一个过期基线
- 两个 Agent 共用一个工作树而以为“已隔离”

## 边界

本技能管**物理隔离**；任务归属与抢跑防止是 `nm-skills` 的事，切片划分是 `incremental-implementation` 的事，完成前验证是 `verification-before-completion` 的事。
