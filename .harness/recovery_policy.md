# Recovery Policy

This directory is the project-local recovery surface for tracked agent work.
It holds current task state and evidence. Do not duplicate active task state in
`AGENTS.md`.

## Session Start

1. Read `AGENTS.md`.
2. Read this file.
3. Read `.harness/work_index.md` and find the single `active` row.
4. Open the active row's primary artifact.
5. Read `.harness/state.md`.
6. Probe fresh dynamic context before editing:

```bash
git status --short
git log --oneline -10
```

7. Run the relevant verification command before claiming readiness.

If `.harness/work_index.md` and `.harness/state.md` disagree on the active
task, stop and reconcile before editing.

## Field Map

| Field | Source |
| --- | --- |
| objective | active plan under `docs/plans/` and `.harness/state.md` |
| active_slice | `.harness/state.md` |
| non_goals | active plan |
| success_criteria | active plan and `.harness/state.md` |
| verification_path | active plan and `.harness/state.md` |
| current_phase | `.harness/state.md` |
| evidence_log | `.harness/progress.md` |
| decisions | `.harness/decisions.md` |
| risks/blockers | active plan and `.harness/state.md` |
| next_actions | `.harness/state.md` |

## Update Triggers

- New tracked task: add or update a row in `.harness/work_index.md`.
- Active slice changes: rewrite `.harness/state.md`.
- Command evidence: append concise evidence to `.harness/progress.md`.
- Irreversible decision or rejected option: update `.harness/decisions.md`.
- Task completion: mark the Work Index row complete and roll up final evidence.

## Stale Signals

- More than one `active` row in `.harness/work_index.md`.
- `AGENTS.md` names a current task instead of pointing to the Work Index.
- `.harness/state.md` references a different plan than the active Work Index row.
- Hot state claims readiness without fresh test or blocker evidence.
