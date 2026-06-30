# Work Index

| id | title | status | primary artifact | last verified |
| --- | --- | --- | --- | --- |
| UL-LEARN-001 | Unitree Launcher project mental model and first optimization readiness | paused | `docs/plans/2026-06-29--unitree-launcher-learning-plan.md` | 2026-06-29: `uv run pytest tests/ -x -q` passed, 505 tests |
| UL-T4-001 | T4 low-level deployment PRD, issues, and staged TDD port | active | `docs/prd/t4-low-level-deployment.md` | 2026-06-30: `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_probe_state.py tests/test_config.py tests/test_factory.py tests/test_main.py -q` passed, 113 tests |

Rules:

- Keep exactly one `active` row unless parallel work is explicitly declared.
- Add new tracked work here instead of editing `AGENTS.md`.
- Mark completed work with the final verification evidence.
