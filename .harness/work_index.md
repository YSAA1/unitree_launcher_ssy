# Work Index

| id | title | status | primary artifact | last verified |
| --- | --- | --- | --- | --- |
| UL-LEARN-001 | Unitree Launcher project mental model and first optimization readiness | paused | `docs/plans/2026-06-29--unitree-launcher-learning-plan.md` | 2026-06-29: `uv run pytest tests/ -x -q` passed, 505 tests |
| UL-T4-001 | T4 low-level deployment PRD, issues, and staged TDD port | active | `docs/plans/2026-06-30--t4-ros2-policy-smoke-plan.md` | 2026-06-30: local selected suite passed, 182 tests; T4 robot `uv run --no-sync real --config configs/t4_ros2_real.yaml --policy assets/t4/policies/2026-06-10_12-11-59_t4_kick_modified_4096_7000_gpu0.onnx --t4-policy-smoke --duration 0.1 --no-log` passed with `state_timestamp=5460731976.000000` and publishing disabled |

Rules:

- Keep exactly one `active` row unless parallel work is explicitly declared.
- Add new tracked work here instead of editing `AGENTS.md`.
- Mark completed work with the final verification evidence.
