---
name: resolving-merge-conflicts
x-category: verify
description: 解决进行中的 git merge / rebase 冲突。当 `git status` 显示 "You have unmerged paths"、rebase 停在某一步、或 cherry-pick / pull 报冲突时使用；也适用于把长期分支合回主干前的预演。触发词：合并冲突、rebase 冲突、merge conflict、冲突解决、unmerged paths。
---

# 解决合并冲突

冲突不是"选一边"，是**两个意图在同一条线上打架**。选错一边的代价是静默丢失别人的修复——它不会报错，只会在几周后以"这个 bug 怎么又出现了"的形式回来。

## 五步

1. **看清当前状态**
   `git status`（是 merge 还是 rebase，停在第几个 commit）、`git log --oneline --graph -10`、`git diff --name-only --diff-filter=U`。
   rebase 时额外看 `git rebase --show-current-patch`。

2. **找到每一处的第一手来源** —— 这一步不能跳
   每个冲突块问三个问题：**这个改动为什么存在**（读 commit message、找 PR / issue）、**它要防的是什么**、**如果丢掉它会怎样**。
   只看 diff 猜意图是这类任务最常见的错误来源：一行 `if (x == null) return;` 看着像防御性代码，实际是某次线上崩溃的修复。

3. **逐块解决**
   - 能同时保留两个意图就同时保留（这是默认答案，不是例外）。
   - 真的不兼容时，选**符合本次合并目标**的那一个，并**记下被放弃的取舍**（写进 commit message 或 PR 描述）。
   - **绝不发明新行为** —— 冲突解决不是重构的时机，没被要求的新逻辑不进这个提交。
   - **永远解决，绝不 `--abort`**。`--abort` 只是把冲突藏起来，下一次遇到时上下文更少。

4. **跑项目自己的检查**
   通常是 typecheck → test → format 的顺序。**合并破坏的东西要在这一步修掉**，不要留给"稍后"。
   注意：冲突解决正确 ≠ 代码正确 —— 两边各自的测试都过，合起来仍可能语义冲突（同一个函数被两个方向改成了不同契约）。

5. **收尾**
   merge：`git add -A && git commit`（用默认的 merge message，或补上取舍说明）。
   rebase：`git rebase --continue`，**直到所有 commit 都 rebase 完** —— 中途停下等于留下一个半成品历史。

## 反合理化表

| 借口 | 现实 |
|---|---|
| "这边代码看起来更新，用这边" | 新旧不是判据，意图才是。旧的那边可能正是修复 |
| "反正测试过了" | 测试覆盖行为，不覆盖你丢掉的那个意图 |
| "冲突太多，先 abort 重来" | abort 不解决冲突，只推迟它。现在上下文最全 |
| "顺手把这段重构了" | 冲突解决要能逐块解释。混进重构后没人能 review |
| "两边都要，拼起来" | 语法上拼得起来不代表语义上成立 —— 要能说出合并后的行为 |

## 完成判据

- `git status` 不再有 unmerged paths，且不在 rebase / merge 中间态
- 每一块的取舍都能解释（保留了谁、为什么）
- typecheck / test / format 全部通过
- 若放弃了某个意图，它被记录在 commit message 或 PR 里

## 与 auto-skills 台账的结合

冲突解决完成、检查全绿后落一条轨迹：

```bash
python scripts/auto_router.py trace resolving_merge_conflicts "冲突: <文件数> 个 → <保留/取舍说明>" --stage verify --status SUCCESS --query "合并冲突" --project-root "."
```

若因为语义冲突（不是文本冲突）导致合并后测试失败，用 `--status FAILED` 并写清是哪个契约被改坏 —— 这正是 `experience_mining` 最该挖到的那类记录。
