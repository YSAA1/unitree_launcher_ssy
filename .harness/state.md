# Current State

updated: 2026-06-30

## Objective

Create a PRD and issue breakdown for T4 low-level deployment, then continue
TDD slices toward the staged T4 port.

## Active Slice

Cleanup and external evidence capture:

```text
Local PRD/issues/TDD/runbook slices are complete; publish issues once gh auth is
repaired and collect real T4 probe output before any publish-enabled control.
```

## Current Phase

TDD Issue 1, Issue 2, Issue 3, and the read-only Issue 4 conversion slice are
complete locally. Issue 5 command message conversion is complete locally.
Issue 6 static-smoke dry-run and Issue 7 policy-smoke dry-run are complete
locally. Issue 8 runbook is complete locally.

## Active Artifact

`docs/prd/t4-low-level-deployment.md`

## Verification Path

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_ros2_probe_state.py tests/test_t4_probe_state.py tests/test_t4_robot.py tests/test_main.py tests/test_config.py tests/test_factory.py tests/test_safety.py -q
python scripts/t4_ros2_probe_state.py --help
python scripts/t4_probe_state.py --help
```

Latest evidence:

- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_probe_state.py tests/test_config.py tests/test_factory.py tests/test_main.py -q` passed with 114 tests.
- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_safety.py -q` passed with 43 tests.
- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_robot.py tests/test_t4_probe_state.py tests/test_main.py tests/test_config.py tests/test_factory.py tests/test_safety.py -q` passed with 161 tests.
- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_main.py tests/test_t4_robot.py tests/test_t4_probe_state.py tests/test_config.py tests/test_factory.py tests/test_safety.py -q` passed with 164 tests.
- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_main.py tests/test_t4_robot.py tests/test_t4_probe_state.py tests/test_config.py tests/test_factory.py tests/test_safety.py -q` passed with 166 tests.
- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_ros2_probe_state.py tests/test_t4_probe_state.py tests/test_t4_robot.py tests/test_main.py tests/test_config.py tests/test_factory.py tests/test_safety.py -q` passed with 171 tests.
- `python scripts/t4_ros2_probe_state.py --help` passed.
- `python scripts/t4_probe_state.py --help` passed.
- Host-side Zvalley SDK probe reached DDS subscription setup but received no samples from `rt/all_joint_state` within the timeout on the current T4 network/configuration.
- Onboard ROS2 probe was copied to `/tmp/t4_ros2_probe_state.py` on T4 and run after `source /home/zl/work/bipedal_humanoid_pro/install/setup.bash`; it subscribed to `/all_joint_state`, `/nav_all`, and `/robot_state`, printed `read_only: true`, observed `joint_count: 29`, IMU/nav fields, and `robot_state: 2`, with no command publisher.
- `real` mode with `robot.variant: t4_29dof` now routes to `T4Robot` and wires T4 joints into Runtime.
- `T4Robot.connect()` now initializes read-only Zvalley subscribers for `rt/all_joint_state` and `rt/nav_all` when the SDK is importable.
- `T4Robot.build_command_message()` converts a 29-DoF `RobotCommand` into a Zvalley `AllJointCmd_` with 29 `JointCmd_` entries and rejects wrong-length commands.
- `real --t4-static-smoke --duration N` with `robot.variant: t4_29dof` builds one bounded static hold command message without active policy load, Runtime construction, or command publication.
- `real --t4-policy-smoke --duration N --policy PATH` with `robot.variant: t4_29dof` loads a T4 policy, executes one policy step, builds a Zvalley command message, and exits without Runtime construction or command publication.
- `docs/runbooks/t4-deployment-gates.md` documents the T4 operator gates, pass evidence, stop conditions, and future publish prerequisites.
- `T4Robot.send_command()` is intentionally command-disabled and raises clear `NotImplementedError` until the Zvalley command path is implemented.
- GitHub issue publishing is blocked by invalid `gh` auth token: latest `gh auth status` reports the active account `YSAA1` token in keyring is invalid.
- T4 root assets were moved under `assets/t4/` and `assets/robots/t4/`; no root-level T4 ONNX or `motion.npz` files remain.
- Local SDK review found `rt/all_joint_state`, `rt/all_joint_cmd`, and `rt/nav_all`; `AllJointState_` does not document IMU fields, so navigation/IMU should be probed through `rt/nav_all`.

## Risks

- Host-side SDK direct discovery remains unresolved on the current T4 configuration; onboard ROS2 read-only probing is the proven state path.
- The real SDK may expose only 23 DoF; if so, current 29-DoF policy is incompatible with that control surface.
- GitHub issues have not been published because local `gh` authentication is invalid.

## Next Actions

1. Repair `gh` authentication and publish `docs/prd/t4-low-level-deployment.md` plus `docs/issues/t4-low-level-deployment-issues.md` to GitHub Issues.
2. Decide whether the next implementation slice should adapt the proven onboard ROS2 topics or continue investigating host-side SDK DDS discovery.
