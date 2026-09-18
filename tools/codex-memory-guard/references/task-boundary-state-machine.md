# Task boundary state machine

Use this specification when implementing, auditing, or testing topic-boundary behavior. It is a prompt-level state machine, not a separate classifier or extra model call.

## States and transitions

| State | Meaning | Transition |
|---|---|---|
| `ACTIVE` | One unfinished current goal | Related input stays `ACTIVE`; unrelated independent direction becomes `BOUNDARY_CANDIDATE` |
| `BOUNDARY_CANDIDATE` | One lightweight reminder is due | User stays -> `CONTINUE_CURRENT`; user requests a separate task -> `SWITCH_RECOMMENDED` |
| `CONTINUE_CURRENT` | User chose to keep this boundary in the current task | Suppress repeats for the same boundary; a distinct unrelated direction becomes a new `BOUNDARY_CANDIDATE` |
| `SWITCH_RECOMMENDED` | User chose separation | Create or switch only after an explicit user request |
| `COMPLETED` | The prior current goal is closed | A different next topic does not require a boundary warning |

Do not write routine labels to project memory. Persist only a user choice or boundary that is necessary to resume correctly after compaction.

## Evaluation order

1. Determine whether the current goal is unfinished.
2. Compare the new input with that goal.
3. Keep directly related clarification, objection, correction, same-deliverable changes, implementation adjustments, and result checks in the current task.
4. Treat a clearly unrelated input that can open an independent discussion or action direction as `BOUNDARY_CANDIDATE`.
5. Use expected duration only as supporting evidence. It cannot exempt a clearly unrelated topic.
6. Remind once and ask whether the user wants a separate Codex task. Never create one from inference alone.

## Behavioral acceptance matrix

Assume the unfinished current goal is maintaining `codex-memory-guard`.

| New input | Expected state | Reason |
|---|---|---|
| “我想喝奶茶” | `BOUNDARY_CANDIDATE` | Clearly unrelated and can open an independent discussion, even if brief |
| “Hook 为什么没有触发？” | `ACTIVE` | Clarification under the current goal |
| “把刚才的规则写自然一点” | `ACTIVE` | Same-deliverable adjustment |
| “你刚才判断错了” | `ACTIVE` | Objection/correction |
| “帮我规划下周旅游” | `BOUNDARY_CANDIDATE` | Independent deliverable |
| “继续刚才的 Skill 修改” | `ACTIVE` | Directly advances the current goal |

After the user chooses to keep “奶茶” in the current task, further discussion of that same topic is `CONTINUE_CURRENT` and must not trigger another reminder. A later unrelated request such as travel planning creates a distinct `BOUNDARY_CANDIDATE`.
