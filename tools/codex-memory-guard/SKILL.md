---
name: codex-memory-guard
description: Guard task boundaries and preserve confirmed critical project state across Codex compaction. Use when a user wants topic-switch guidance, write-through critical memory, compact HANDOFF checkpoints, PreCompact and compact-resume hooks, four-layer Markdown memory initialization, or memory workflow auditing.
---

# Codex Memory Guard

Keep tasks small enough to finish before compaction when practical. Persist confirmed critical state when it appears, keep the recovery checkpoint compact, and preserve a raw transcript reference as the final fallback.

This Skill does not prevent compaction or promise lossless retention of every chat detail. It makes confirmed critical decisions, constraints, verified lessons, blockers, and execution state durable, reviewable, and traceable.

## Workflow

1. Apply the task-boundary state machine when the current goal is unfinished. Compare the new input with the current goal before estimating its duration.
2. Inspect the target project for existing `AGENTS.md`, memory files, and `.codex/hooks.json`.
3. Run `scripts/initialize-memory-system.ps1` for the target root. It creates all four memory layers when missing and preserves existing content.
4. Run `scripts/install.ps1` only after the user authorizes global installation. It installs the Hooks and safely upserts a marked policy block in the user's global `AGENTS.md` without replacing other rules.
5. Tell the user to review and trust the new handlers through `/hooks`; never claim they are active before trust is confirmed.
6. Verify with `scripts/test.ps1` in an isolated temporary directory. The test covers pre-compaction HANDOFF validation, ready and recovery-required resume paths, installation, and scoped uninstall.
7. After a real compaction, inspect `memory/inbox/pending-*.json` and the short `HANDOFF.md`; search the transcript selectively only when the checkpoint is insufficient.

## Task boundary policy

Use these states: `ACTIVE`, `BOUNDARY_CANDIDATE`, `CONTINUE_CURRENT`, `SWITCH_RECOMMENDED`, and `COMPLETED`.

For each new input while the state is `ACTIVE`:

1. Identify the single current goal from the conversation and short `HANDOFF.md` when present.
2. Decide whether the input directly advances that goal.
3. If it does not, decide whether it is still a goal-related clarification, objection, correction, implementation adjustment, same-deliverable addition, or result check.
4. If neither applies and the input can open an independent discussion or action direction, enter `BOUNDARY_CANDIDATE` and give one lightweight reminder. Do this even when the new topic might end within one or two turns; do not require the user to label it as a test.

Treat the following as additional boundary evidence:

- the project or working directory changes;
- the final deliverable or acceptance criteria change;
- two unrelated current goals would be needed in `HANDOFF.md`;
- the unfinished current task would be displaced by another multi-turn task;
- the new work has materially different permissions, risks, or side effects.

Ask whether the user wants a separate Codex task; do not create one without an explicit request. If the user stays, enter `CONTINUE_CURRENT` for that boundary and do not repeat the reminder unless a distinct boundary appears. If the user chooses a separate task, enter `SWITCH_RECOMMENDED`. When the current goal is closed, enter `COMPLETED` and do not warn merely because the next topic differs.

The short-tangent exemption applies only when the tangent is directly related to the current goal. A short but clearly unrelated topic is still a boundary candidate. Do not persist routine state labels; record only a boundary choice needed for reliable resume. For the normative transition table and examples, read `references/task-boundary-state-machine.md` when implementing, auditing, or testing boundary behavior.

## Memory policy

- Treat the transcript as evidence, not default model context.
- Write confirmed critical information when it appears; do not wait for compaction. Explicit phrases such as "remember this", "this is final", "use this from now on", or equivalent require immediate persistence and a read-back confirmation with the destination path.
- Critical information includes confirmed decisions, user constraints, acceptance criteria, verified lessons, active blockers, exact state required to resume, and facts whose loss would cause rework or duplicate side effects.
- Use `HANDOFF.md` for one current goal, current state, blockers, at most three recent milestones, one next action, and key files. Target 500-1000 Chinese characters and enforce a hard limit of 1500 characters. Rewrite and shrink it instead of appending when over budget.
- Use `DECISIONS.md` for confirmed decisions with source and invalidation conditions.
- Use `LESSONS.md` only for practices verified in real work.
- Route unconfirmed observations to `memory/YYYY-MM-DD.md`.
- Create all four layers, but load only `HANDOFF.md` by default. Read other layers only when the current question needs them.
- Never store credentials, tokens, or secrets in memory artifacts.
- Preserve conflicting history and mark supersession; do not silently rewrite it.
- Read back every critical-memory write and verify content, source, scope, status, and invalidation or review conditions.

## Hook behavior

- `PreCompact` validates `HANDOFF.md` deterministically before writing the pending record. The record includes existence, structure and length status, issues, last-write time, SHA-256, and `recovery_required`, plus the session and transcript evidence pointer. It does not copy transcript contents or perform semantic summarization.
- `SessionStart` matching `compact` reads the recorded check. A ready checkpoint resumes from `HANDOFF.md` without loading the transcript unless state conflicts; a failed checkpoint must search only relevant transcript fragments and repair `HANDOFF.md` before normal work continues.
- Keep both hooks synchronous. The default installation timeout is 10 seconds because they perform local small-file operations only.
- The command hook does not perform semantic extraction itself. Critical state should already be written through when confirmed; the deterministic pre-check and post-compaction closure are the fallback.

Validate a checkpoint:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate-handoff.ps1 -Path C:\path\to\project\HANDOFF.md
```

## Commands

Initialize one project:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/initialize-memory-system.ps1 -Root C:\path\to\project -SingleProject
```

Initialize every immediate child project:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/initialize-memory-system.ps1 -Root C:\path\to\projects
```

Install global hooks and optionally initialize a project:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install.ps1 -ProjectRoot C:\path\to\project
```

Remove only this Skill's global hooks:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/uninstall.ps1
```

Uninstall also removes only the marked `codex-memory-guard` block from global `AGENTS.md`; it preserves all other global rules and project memory files.

For schemas and acceptance checks, read `references/memory-contract.md`.
