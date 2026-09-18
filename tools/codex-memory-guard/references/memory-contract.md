# Memory contract

## Artifacts

| Artifact | Role | Promotion threshold |
|---|---|---|
| Raw transcript | Immutable evidence reference | Never summarized in place |
| `HANDOFF.md` | Compact working checkpoint | One current goal, active state, blockers, up to three milestones, one next action, key files; 1500-character hard limit |
| `memory/YYYY-MM-DD.md` | Episodic candidates | Unconfirmed items allowed with labels |
| `DECISIONS.md` | Durable semantic memory | Confirmed decision plus rationale and source |
| `LESSONS.md` | Durable procedural memory | Reproduced or verified practice |
| `memory/inbox/pending-*.json` | Compaction closure queue | Must become `processed` after closure |

## Pending schema

Required fields:

- `schema_version`
- `status`: `awaiting_extraction` or `processed`
- `captured_at`
- `project_root`
- `cwd`
- `session_id`
- `trigger`: `manual` or `auto`
- `transcript_path`
- `handoff_check`:
  - `path`
  - `exists`
  - `status`: `ready`, `over_recommended_limit`, `invalid`, `missing`, or `over_hard_limit`
  - `characters`
  - `last_write_at`
  - `sha256`
  - `recovery_required`
  - `issues`

When processed, add `processed_at` without deleting the original capture metadata.

## Acceptance checks

1. Re-running initialization creates no files and changes no existing content.
2. Existing Hook definitions remain present after installation.
3. `PreCompact` produces schema v2 JSON with a deterministic HANDOFF check and a pending record.
4. Compact `SessionStart` resumes directly from a ready HANDOFF and requires targeted transcript repair when `recovery_required` is true.
5. No transcript content or credentials are copied into the pending record.
6. After real compaction, the pending status becomes `processed` and project memory reflects the durable information.
7. Initialization creates all four memory layers while preserving existing files.
8. `HANDOFF.md` passes the 1500-character validator and contains only one current goal and one next action.
9. Compact recovery reads `HANDOFF.md` before selectively searching the transcript.
10. Explicitly confirmed critical information is written immediately and verified by read-back instead of waiting for compaction.
11. Global installation preserves existing `AGENTS.md` content and creates exactly one `codex-memory-guard` managed block.
12. Uninstall removes only this Skill's Hook handlers and managed global `AGENTS.md` block.
13. Boundary evaluation compares goal relevance before expected duration; unrelated short topics are not exempted solely because they may end quickly.
14. A boundary reminder occurs once per distinct boundary, respects the user's choice to stay, and never creates a Codex task without an explicit request.
15. HANDOFF validation checks the six-section checkpoint shape, exactly one current-goal item, exactly one next-action item, at most three recent milestones, required placeholders, character limits, last-write time, and SHA-256 without attempting semantic summarization.
