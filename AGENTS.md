# AGENTS.md

Project entry for AI agents working in this repository.

## Read First

1. `README.md` for install, run modes, deployment commands, and operator controls.
2. `CLAUDE.md` for project coding rules, architecture notes, and common commands.
3. `.harness/recovery_policy.md` for session recovery rules.
4. `.harness/work_index.md` for the current active work artifact.
5. `study_plan.md` for the current high-level learning model of the project.

## Project Map

This repository is a Unitree G1 deployment stack, not a training framework.
It runs exported ONNX policies in MuJoCo simulation or on a real G1 through a
shared runtime, robot interface, safety controller, logging, replay, and
visualization stack.

Core paths:

- `src/unitree_launcher/main.py`: CLI mode wiring for `sim`, `eval`, `real`, `mirror`, and `replay`.
- `src/unitree_launcher/control/runtime.py`: atomic control tick and policy transitions.
- `src/unitree_launcher/control/safety.py`: safety state machine, E-stop, tilt/frame-drop checks, and command clamping.
- `src/unitree_launcher/robot/base.py`: shared `RobotState`, `RobotCommand`, and `RobotInterface`.
- `src/unitree_launcher/robot/`: simulation, real robot, and mirror backends.
- `src/unitree_launcher/policy/`: ONNX policy wrappers, factory, and joint mapping.
- `src/unitree_launcher/estimation/`: estimator, contact, and kinematics code.
- `tests/`: pytest suite covering core runtime, safety, policy, robot, config, and integration behavior.
- `configs/`: mode-specific YAML configuration.
- `scripts/`: deployment, network, replay, diagnostics, and sim2real helper scripts.

## Durable Rules

- Preserve real-robot safety behavior. Treat `real` mode, DDS backend, E-stop,
  joint order, gains, and limits as high-risk surfaces.
- Prefer small, verified changes. Read the relevant tests before touching shared runtime, policy, robot, safety, or config behavior.
- Do not add backward-compatibility aliases, legacy fallback paths, or historical notes in code.
- Keep active task state out of this file. Current objectives, active slices,
  evidence, and next steps belong in `.harness/` and linked plans under `docs/plans/`.
- Policy files under `assets/policies/*.onnx`, logs, media, virtualenvs, and cache outputs are not source-of-truth artifacts.

## Verification

Install the local development and simulation dependencies before running the full test suite:

```bash
uv sync --extra dev --extra sim
uv run pytest tests/ -x
```

For quick import/environment checks:

```bash
uv run python -c "import unitree_launcher; print(unitree_launcher.__file__)"
```

Do not claim readiness without fresh evidence from an appropriate command or an explicitly recorded blocker.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues, and external PRs are also a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the default five-label triage vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

Use a single-context domain docs layout: root `CONTEXT.md` plus `docs/adr/`. See `docs/agents/domain.md`.

## Source-Of-Truth Tiers

| Tier | Role | Paths |
| --- | --- | --- |
| T1 | Durable entry and rules | `AGENTS.md`, `CLAUDE.md`, `README.md` |
| T2 | Domain model and architecture notes | `study_plan.md`, `docs/` |
| T3 | Task registry | `.harness/work_index.md` |
| T4 | Active work plan/spec | `docs/plans/`, `.harness/state.md` |
| T5 | Fresh evidence | test output, git status, `.harness/progress.md` |
| T6 | Generated or external artifacts | logs, media, policy binaries, caches |

Conflict rule: fresh evidence beats active plans; active plans beat the work
index; the work index beats durable entry docs for current task state.
