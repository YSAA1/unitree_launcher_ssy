# Unitree Launcher Learning And Optimization Plan

Date: 2026-06-29

## Objective

Build a usable mental model of this Unitree G1 deployment stack quickly enough
to run it, explain its core control path, and make a small verified
optimization without increasing real-robot risk.

## Spec Source

- User request: learn the whole project mental model, how to use it, then make changes and optimizations.
- Background note: `study_plan.md`
- Project entry evidence: `README.md`, `CLAUDE.md`, `pyproject.toml`, `tests/`
- Verification evidence collected before writing this plan:
  - `uv sync --extra dev --extra sim`
  - `uv run pytest tests/ -x -q` passed with `505 passed in 22.18s`

No separate approved spec exists. This request is clear enough for an
Executable Plan because the objective, non-goals, success criteria, and
verification path are directly testable.

## Active Slice

Understand and verify the core control path:

```text
CLI mode -> config -> robot backend -> policy -> Runtime.step() -> SafetyController -> RobotCommand -> robot backend
```

## Non-Goals

- Do not deploy to a real G1 during the learning slice.
- Do not change DDS, C++ backend, E-stop behavior, joint limits, policy gains,
  or joint mapping without a separate plan and fresh tests.
- Do not train policies or modify ONNX files.
- Do not add new dependencies or broad abstractions while learning.

## Success Criteria

- You can explain the five runtime modes and which backend each one uses.
- You can trace one control tick from state read to command send.
- You can explain the data contract of `RobotState`, `RobotCommand`, `Policy.step`, and `RobotInterface`.
- You can identify where safety checks and command clamps happen.
- You can identify the ONNX policy loading path, format detection, and joint-order mapping risk.
- Before any optimization claim, `uv run pytest tests/ -x` passes or a blocker is recorded with fallback evidence.

## Verification Path

Primary verification:

```bash
uv sync --extra dev --extra sim
uv run pytest tests/ -x
```

Optional quick probes:

```bash
uv run python -c "import unitree_launcher; print(unitree_launcher.__file__)"
uv run python -c "from unitree_launcher.config import load_config; print(load_config('configs/sim.yaml').robot.variant)"
```

Verification path status: `runnable`.

## Required Capabilities

- Local Python 3.10 environment managed by `uv`.
- `dev` and `sim` extras installed for pytest coverage of MuJoCo-dependent tests.
- Ability to read source and tests side by side.
- No real robot required for this learning plan.

## Fallback Evidence

If full tests are blocked by network or optional dependency installation, use:

- `uv run python -c "import unitree_launcher; print(unitree_launcher.__file__)"`
- targeted non-MuJoCo tests such as `uv run pytest tests/test_config.py tests/test_safety.py tests/test_runtime.py -x`
- recorded blocker in `.harness/progress.md` with the exact command and failure.

## Final Integration Claim

The learning and first optimization slice is complete only when:

- the core control-path mental model is documented or explained from source,
- the first selected optimization has a small scope and risk statement,
- relevant tests pass,
- `.harness/state.md` and `.harness/progress.md` point to the final evidence.

## Work Items

### 1. Environment And Test Baseline

Status: complete

Actions:

- Install dev and sim dependencies.
- Run the full pytest suite.
- Record the command needed by future agents.

acceptance_criteria:

- `uv run pytest tests/ -x` runs from the repository root.
- The dependency command needed to reach that state is known.

verification_commands:

```bash
uv sync --extra dev --extra sim
uv run pytest tests/ -x
```

success_definition:

The project has a fresh local test baseline before reading or changing code.

### 2. Entry, Modes, And Configuration

Status: next

Actions:

- Read `README.md`, `CLAUDE.md`, `src/unitree_launcher/main.py`, and `src/unitree_launcher/config.py`.
- Map `sim`, `eval`, `real`, `mirror`, and `replay` to their backend and control-loop shape.
- Note config override paths and high-risk real-robot options.

acceptance_criteria:

- You can explain which objects are constructed for each mode.
- You can identify which config file each mode uses by default.

verification_commands:

```bash
uv run pytest tests/test_main.py tests/test_config.py -x
```

success_definition:

The CLI and config layer is understood enough to predict what a mode command will instantiate.

### 3. Shared Runtime Data Contract

Status: pending

Actions:

- Read `src/unitree_launcher/robot/base.py` and `src/unitree_launcher/policy/base.py`.
- Write a short source-backed note for `RobotState`, `RobotCommand`, `Policy.step`, `Policy.warmup`, and `RobotInterface`.
- Cross-check with `tests/test_runtime.py`, `tests/test_sim_robot.py`, and `tests/test_real_robot.py`.

acceptance_criteria:

- You can state which arrays must be robot-native order.
- You can state what a policy owns versus what Runtime owns.

verification_commands:

```bash
uv run pytest tests/test_runtime.py tests/test_sim_robot.py tests/test_real_robot.py -x
```

success_definition:

The core object contract is clear enough to avoid changing the wrong layer.

### 4. Control Loop And Safety Boundary

Status: pending

Actions:

- Read `src/unitree_launcher/control/runtime.py` and `src/unitree_launcher/control/safety.py`.
- Trace `Runtime.step()` through state read, input merge, policy selection, transitions, safety checks, logging, and robot step.
- Read `tests/test_safety.py`, `tests/test_safety_sim.py`, and relevant runtime tests.

acceptance_criteria:

- You can explain when Runtime sends damping, hold, default policy, or active policy commands.
- You can explain E-stop latching and command clamping behavior.

verification_commands:

```bash
uv run pytest tests/test_runtime.py tests/test_safety.py tests/test_safety_sim.py -x
```

success_definition:

The safety boundary is understood before selecting any optimization.

### 5. Policy Loading And Joint Mapping

Status: pending

Actions:

- Read `src/unitree_launcher/policy/factory.py`, `isaaclab_policy.py`, `beyondmimic_policy.py`, and `joint_mapper.py`.
- Identify how policy format is detected and how policy joint order maps to robot-native order.
- Read policy tests for metadata, action scaling, defaults, gains, and mapping.

acceptance_criteria:

- You can explain the difference between IsaacLab and BeyondMimic ONNX inputs.
- You can state why joint order is a real-robot risk.

verification_commands:

```bash
uv run pytest tests/test_factory.py tests/test_isaaclab_policy.py tests/test_beyondmimic_policy.py tests/test_joint_mapper.py -x
```

success_definition:

The policy interface is understood enough to evaluate future ONNX integration changes.

### 6. Backend, Estimator, Logging, And First Optimization Selection

Status: pending

Actions:

- Read `robot/sim_robot.py`, `robot/real_robot.py`, `robot/mirror_robot.py`, `estimation/`, and `datalog/`.
- Compare simulation-only state with real hardware state and estimator fill-ins.
- Select one first optimization that is low-risk, testable, and does not alter real-robot safety behavior without a separate plan.

acceptance_criteria:

- You can describe the sim/real backend differences and estimator purpose.
- The first optimization candidate has a concrete scope, non-goals, and test command.

verification_commands:

```bash
uv run pytest tests/test_estimator.py tests/test_logger.py tests/test_replay.py tests/test_integration.py -x
```

If `tests/test_replay.py` is absent, run:

```bash
uv run pytest tests/test_estimator.py tests/test_logger.py tests/test_integration.py -x
```

success_definition:

The first code change can be planned from a known layer with known verification.

## Commit Units

### Commit Unit 1: Harness And Learning Plan

scope:

- `AGENTS.md`
- `docs/plans/2026-06-29--unitree-launcher-learning-plan.md`
- `.harness/`

对应阶段:

- Environment And Test Baseline
- Entry, Modes, And Configuration setup

提交前置条件:

- review has no Critical findings
- `uv run pytest tests/ -x` passes or a recorded blocker is accepted

### Commit Unit 2: First Optimization

scope:

- the smallest source/test/doc slice chosen after Work Item 6

对应阶段:

- Backend, Estimator, Logging, And First Optimization Selection

提交前置条件:

- optimization scope is written in `.harness/state.md`
- review has no Critical findings
- relevant targeted tests and final `uv run pytest tests/ -x` pass

## Known Risks And Blockers

- Real robot deployment is out of scope and requires separate operator safety checks.
- Policy ONNX files are gitignored; tests use generated or mock policy files where possible.
- `uv sync --extra dev --extra sim` may need network access for optional packages.
- Joint order, gains, and safety clamps are high-risk change surfaces.

## Handoff

Next skill: `verify` for harness evidence, then `implement` only after a concrete first optimization is selected.
