# Decisions

## 2026-06-29

### Use `.harness/` for active task recovery

Decision: Keep current task state in `.harness/` and plans under `docs/plans/`.

Reason: `AGENTS.md` should remain a thin durable entry point. Active slice,
evidence, decisions, and next actions need to be recoverable without turning
the entry file into a stale task log.

### Treat `study_plan.md` as background, not runtime state

Decision: Keep `study_plan.md` as the high-level mental-model note and write
the executable learning workflow to `docs/plans/2026-06-29--unitree-launcher-learning-plan.md`.

Reason: `study_plan.md` is useful context, but it does not define a single
active slice, verification status, commit units, or recovery rules.

### Require `dev + sim` extras for full tests

Decision: Use `uv sync --extra dev --extra sim` before the full pytest suite.

Reason: The full test suite imports MuJoCo and visualization-related modules.
`dev` alone is insufficient for the current test baseline.
