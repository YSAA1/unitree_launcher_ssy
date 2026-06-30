# Current State

updated: 2026-06-30

## Objective

Create a PRD and issue breakdown for T4 low-level deployment, then continue
TDD slices toward the staged T4 port.

## Active Slice

Next TDD slice:

```text
Design and verify the T4 publish gate. Do not add command publishing until the
gate proves robot state prerequisites, `/change_robot_state` semantics,
`/all_joint_cmd` subscriber behavior, real `cmd_type`, conservative gains,
operator opt-in, support/stop procedure, and emergency path.
```

## Current Phase

The initial T4 SDK/DDS dry-run slices are complete locally. The observed T4
robot's onboard ROS2 state path is verified read-only. The `t4_ros2`
full-project policy smoke dry-run is complete locally and on the T4 robot, with
command publishing still disabled.

## Active Artifact

`docs/plans/2026-06-30--t4-ros2-policy-smoke-plan.md`

## Verification Path

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_ros2_probe_state.py tests/test_t4_probe_state.py tests/test_t4_ros2_robot.py tests/test_t4_robot.py tests/test_main.py tests/test_config.py tests/test_factory.py tests/test_safety.py -q
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
- `uv run pytest tests/test_config.py tests/test_t4_ros2_robot.py tests/test_main.py -q` passed with 106 tests.
- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_ros2_probe_state.py tests/test_t4_probe_state.py tests/test_t4_ros2_robot.py tests/test_t4_robot.py tests/test_main.py tests/test_config.py tests/test_factory.py tests/test_safety.py -q` passed with 182 tests.
- Robot-side full project smoke ran from `/home/zl/projects/unitree_launcher_t4_dryrun` after sourcing `/home/zl/work/bipedal_humanoid_pro/install/setup.bash`: `uv run --no-sync real --config configs/t4_ros2_real.yaml --policy assets/t4/policies/2026-06-10_12-11-59_t4_kick_modified_4096_7000_gpu0.onnx --t4-policy-smoke --duration 0.1 --no-log`.
- Robot-side output: `[main] T4 policy smoke built one 29-DoF policy command for 0.100s; state_timestamp=5460731976.000000; command publishing remains disabled.`
- Host-side Zvalley SDK probe reached DDS subscription setup but received no samples from `rt/all_joint_state` within the timeout on the current T4 network/configuration.
- Onboard ROS2 probe was copied to `/tmp/t4_ros2_probe_state.py` on T4 and run after `source /home/zl/work/bipedal_humanoid_pro/install/setup.bash`; it subscribed to `/all_joint_state`, `/nav_all`, and `/robot_state`, printed `read_only: true`, observed `joint_count: 29`, IMU/nav fields, and `robot_state: 2`, with no command publisher.
- `real` mode with `robot.variant: t4_29dof` now requires explicit backend selection: `t4_sdk_dds` routes to `T4Robot`, and `t4_ros2` routes to `T4Ros2Robot`.
- `T4Robot.connect()` now initializes read-only Zvalley subscribers for `rt/all_joint_state` and `rt/nav_all` when the SDK is importable.
- `T4Robot.build_command_message()` converts a 29-DoF `RobotCommand` into a Zvalley `AllJointCmd_` with 29 `JointCmd_` entries and rejects wrong-length commands.
- `real --t4-static-smoke --duration N` with `robot.variant: t4_29dof` builds one bounded static hold command message without active policy load, Runtime construction, or command publication.
- `real --t4-policy-smoke --duration N --policy PATH` with `robot.variant: t4_29dof` loads a T4 policy, executes one policy step, builds a backend command message, and exits without Runtime construction or command publication.
- `docs/runbooks/t4-deployment-gates.md` documents the T4 operator gates, pass evidence, stop conditions, and future publish prerequisites.
- `T4Robot.send_command()` is intentionally command-disabled and raises clear `NotImplementedError` until the Zvalley command path is implemented.
- GitHub issue publishing is blocked by invalid `gh` auth token: latest `gh auth status` reports the active account `YSAA1` token in keyring is invalid.
- T4 root assets were moved under `assets/t4/` and `assets/robots/t4/`; no root-level T4 ONNX or `motion.npz` files remain.
- Local SDK review found `rt/all_joint_state`, `rt/all_joint_cmd`, and `rt/nav_all`; `AllJointState_` does not document IMU fields, so navigation/IMU should be probed through `rt/nav_all`.
- `docs/plans/2026-06-30--t4-ros2-policy-smoke-plan.md` records the completed T4 ROS2 policy smoke slice: explicit `robot.backend`, `T4Ros2Robot`, ROS2 `AllJointCmd` build with `cmd_type = 0`, and full project `--t4-policy-smoke` evidence on the T4 robot without publishing.
- ADRs record the current direction: use the onboard ROS2 adapter as the next T4 path and split robot `variant` from communication `backend`.

## Risks

- Host-side SDK direct discovery remains unresolved on the current T4 configuration; onboard ROS2 read-only probing is the proven state path.
- The real SDK may expose only 23 DoF; if so, current 29-DoF policy is incompatible with that control surface.
- GitHub issues have not been published because local `gh` authentication is invalid.
- Robot-side dependency sync through PyPI failed on `onnxruntime==1.23.2` with TLS handshake EOF; the verified dry-run used an isolated copied Python 3.10 `.venv` and `uv run --no-sync`, with script paths fixed inside the temporary project.
- Publish remains unimplemented and must not be inferred from the successful dry-run.

## Next Actions

1. Design the explicit T4 publish gate before adding any command publisher.
2. Keep command publishing disabled until that gate is reviewed and verified.
3. Repair `gh` authentication and publish `docs/prd/t4-low-level-deployment.md` plus `docs/issues/t4-low-level-deployment-issues.md` to GitHub Issues when credentials are available.
