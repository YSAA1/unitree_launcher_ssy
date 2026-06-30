# T4 ROS2 Policy Smoke Dry-Run Plan

This plan is the next TDD execution slice after the T4 onboard ROS2 read-only
probe passed. It targets the first complete project-level dry run for the T4
policy path, without publishing motor commands.

## Target

Run the full project entrypoint on the T4 robot itself:

```bash
uv run real \
  --config configs/t4_ros2_real.yaml \
  --policy assets/t4/policies/2026-06-10_12-11-59_t4_kick_modified_4096_7000_gpu0.onnx \
  --t4-policy-smoke \
  --duration 0.1 \
  --no-log
```

The command must read real ROS2 state, load the real ONNX policy, build a
29-DoF ROS2 command message, and exit without publishing `/all_joint_cmd`.

## Current Evidence

- T4 is reachable over Ethernet at `192.168.12.100`.
- SSH login works as `zl`.
- T4 onboard ROS2 workspace is `/home/zl/work/bipedal_humanoid_pro`.
- Onboard stack is launched as `ros2 launch robot_system robot.launch.py`.
- `/all_joint_state` publishes `robot_msgs/msg/AllJointState`.
- `/all_joint_state` exposes 29 joints with `model_id` `0..28`.
- `/all_joint_state` publishes at approximately 200 Hz.
- `/nav_all` publishes navigation/IMU-like data.
- `/robot_state` publishes current robot state.
- `scripts/t4_ros2_probe_state.py` ran on the robot and printed
  `read_only: true`, `joint_count: 29`, nav fields, and `robot_state: 2`.
- Host-side Zvalley SDK DDS probing can initialize subscriptions but currently
  receives no samples on this T4 configuration.

## Decisions

- Use the onboard ROS2 adapter path as the critical path.
- Keep host-side Zvalley SDK DDS direct connection as a separate investigation.
- Add a new `T4Ros2Robot`; do not overload the current SDK-oriented `T4Robot`.
- Split robot identity from backend selection:
  - `robot.variant` means model/joint identity.
  - `robot.backend` means communication adapter.
- Existing G1 configs may keep their current default backend.
- T4 configs must explicitly set a backend.
- The next backend is `robot.backend: t4_ros2`.
- Dry-run command messages use ROS2 `robot_msgs/msg/AllJointCmd`.
- Dry-run `cmd_type` is fixed to `0`.
- Publish gate is a later, explicit slice and is not part of this plan.
- The main validation path must be the full project entrypoint on the T4 robot.
- Dependencies may be installed only into an isolated project environment.
- Do not modify `/opt/ros`, system Python, the robot's original ROS2 workspace,
  launch files, systemd services, or shell startup files.
- Temporary project deployment path is
  `/home/zl/projects/unitree_launcher_t4_dryrun`.

## Scope

Implement enough for `t4_ros2` policy smoke dry-run:

- Config accepts a backend field.
- T4 requires explicit backend selection.
- G1 old configs remain compatible.
- `configs/t4_ros2_real.yaml` exists.
- `T4Ros2Robot` implements read-only state conversion.
- `T4Ros2Robot.build_command_message()` builds ROS2 `AllJointCmd`.
- `T4Ros2Robot.send_command()` remains disabled.
- `main.py` routes `real + t4_29dof + t4_ros2` to `T4Ros2Robot`.
- `--t4-policy-smoke` works with the ROS2 backend and does not publish.

Out of scope:

- Publishing `/all_joint_cmd`.
- Publishing `/change_robot_state`.
- Switching robot state.
- Choosing real publish `cmd_type`.
- Static hold publish test.
- Runtime active control loop on T4.
- Installing anything globally on the robot.
- Modifying the vendor ROS2 workspace.

## TDD Slices

### Slice 1: Backend Config

Behavior:

- G1 configs without `robot.backend` still load.
- T4 config without `robot.backend` fails clearly.
- T4 config with `backend: t4_ros2` loads.
- T4 config with `backend: t4_sdk_dds` loads for the existing SDK path.
- Unknown backend fails clearly.

Evidence:

```bash
uv run pytest tests/test_config.py -q
```

### Slice 2: T4Ros2Robot State Conversion

Behavior:

- Fake ROS2 `AllJointState` with 29 joints becomes `RobotState`.
- Fake ROS2 `NavAll` fills quaternion, angular velocity, and acceleration.
- Fake ROS2 `RobotState` is retained for diagnostics/state gating.
- Missing optional fields do not crash.
- `base_position` and `base_velocity` keep the real-robot `NaN` convention.
- No publisher is created during read-only connection.

Evidence:

```bash
uv run pytest tests/test_t4_ros2_robot.py -q
```

### Slice 3: ROS2 Command Message Build, Publish Disabled

Behavior:

- A 29-DoF `RobotCommand` builds one ROS2 `AllJointCmd` message.
- Message contains 29 `JointCmd` entries.
- `cmd_type == 0` in dry-run.
- Position, velocity, torque, `kp`, and `kd` map without reordering.
- Wrong-length commands fail before message construction.
- `send_command()` raises `NotImplementedError`.
- No publisher or `publish()` call occurs.

Evidence:

```bash
uv run pytest tests/test_t4_ros2_robot.py -q
```

### Slice 4: Main Wiring

Behavior:

- `real` mode with `robot.variant: t4_29dof` and `robot.backend: t4_ros2`
  creates `T4Ros2Robot`.
- Existing SDK T4 path remains selectable as `robot.backend: t4_sdk_dds`.
- `--t4-policy-smoke` loads the ONNX policy, reads one state, runs one policy
  step, builds one ROS2 `AllJointCmd`, and exits.
- `Runtime` is not constructed during smoke dry-run.
- `send_command()` is not called during smoke dry-run.

Evidence:

```bash
uv run pytest tests/test_main.py tests/test_t4_ros2_robot.py -q
```

### Slice 5: Local Verification

Behavior:

- Existing T4 SDK tests still pass.
- Existing G1 config/factory/main/safety tests still pass.
- Probe help still renders.

Evidence:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run pytest \
  tests/test_t4_ros2_probe_state.py \
  tests/test_t4_probe_state.py \
  tests/test_t4_ros2_robot.py \
  tests/test_t4_robot.py \
  tests/test_main.py \
  tests/test_config.py \
  tests/test_factory.py \
  tests/test_safety.py \
  -q
python scripts/t4_ros2_probe_state.py --help
python scripts/t4_probe_state.py --help
```

## Robot-Side Full-Project Verification

Deploy the project to the robot without touching the vendor workspace:

```bash
ssh zl@192.168.12.100 'mkdir -p /home/zl/projects'
rsync -a --delete \
  --exclude .git \
  --exclude .venv \
  --exclude __pycache__ \
  ./ zl@192.168.12.100:/home/zl/projects/unitree_launcher_t4_dryrun/
```

On the robot:

```bash
cd /home/zl/projects/unitree_launcher_t4_dryrun
source /home/zl/work/bipedal_humanoid_pro/install/setup.bash
uv sync --extra dev
uv run real \
  --config configs/t4_ros2_real.yaml \
  --policy assets/t4/policies/2026-06-10_12-11-59_t4_kick_modified_4096_7000_gpu0.onnx \
  --t4-policy-smoke \
  --duration 0.1 \
  --no-log
```

If `uv` is missing, install or bootstrap it into the user environment without
using `sudo` or modifying system Python. If dependency installation fails,
diagnose the dependency failure before considering a fallback script. A fallback
script may help isolate the failure but does not satisfy this plan.

## Completion Criteria

This slice is complete only when all are true:

- Local tests pass.
- Project is deployed to `/home/zl/projects/unitree_launcher_t4_dryrun`.
- Robot-side isolated dependency environment is working.
- Full project command runs on the robot after sourcing the T4 ROS2 workspace.
- Output proves real ROS2 state was read.
- Output proves a 29-DoF ROS2 `AllJointCmd` was built.
- Output proves command publishing remains disabled.
- No `/all_joint_cmd` publish occurs.
- No vendor workspace, ROS install, system Python, launch file, or systemd unit
  is modified.

## Publish Gate Placeholder

The next slice after this plan is the publish gate. It must decide and verify:

- real `cmd_type`
- required `robot_state`
- `/change_robot_state` semantics
- `/all_joint_cmd` subscriber behavior
- conservative gains
- bounded duration
- operator opt-in
- physical support
- stop path and emergency procedure

Do not implement publish behavior in this dry-run slice.

## Execution Result

Status: complete for dry-run policy smoke; publish remains out of scope.

Implemented:

- `robot.backend` config field and validation.
- `configs/t4_ros2_real.yaml`.
- `T4Ros2Robot` read-only ROS2 backend.
- ROS2 `/all_joint_state`, `/nav_all`, and `/robot_state` state conversion.
- First joint-state wait before policy smoke state use.
- ROS2 `AllJointCmd` message construction with `cmd_type = 0`.
- `send_command()` remains disabled.
- `main.py` routes `real + backend: t4_ros2` to `T4Ros2Robot`.
- `--t4-policy-smoke` builds one backend command message and exits without
  Runtime construction or command publication.

Local evidence:

```bash
uv run pytest tests/test_config.py tests/test_t4_ros2_robot.py tests/test_main.py -q
# 106 passed in 10.83s

env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_ros2_probe_state.py tests/test_t4_probe_state.py tests/test_t4_ros2_robot.py tests/test_t4_robot.py tests/test_main.py tests/test_config.py tests/test_factory.py tests/test_safety.py -q
# 182 passed in 12.01s

python scripts/t4_ros2_probe_state.py --help
python scripts/t4_probe_state.py --help
# both rendered help successfully
```

Robot-side evidence:

```bash
cd /home/zl/projects/unitree_launcher_t4_dryrun
source /home/zl/work/bipedal_humanoid_pro/install/setup.bash
uv run --no-sync real \
  --config configs/t4_ros2_real.yaml \
  --policy assets/t4/policies/2026-06-10_12-11-59_t4_kick_modified_4096_7000_gpu0.onnx \
  --t4-policy-smoke \
  --duration 0.1 \
  --no-log
```

Output:

```text
[main] T4 policy smoke built one 29-DoF policy command for 0.100s; state_timestamp=5460731976.000000; command publishing remains disabled.
```

Robot deployment notes:

- Deployed temporary project to `/home/zl/projects/unitree_launcher_t4_dryrun`.
- Robot user environment did not have `uv`; copied a compatible x86_64 `uv`
  binary to `/home/zl/.local/bin/uv`.
- Robot PyPI download for `onnxruntime==1.23.2` failed with TLS handshake EOF.
- To keep dependencies isolated and avoid system Python changes, copied the
  local Python 3.10 `.venv` into the temporary project, fixed the project `.pth`
  and script shebangs to robot paths, then ran with `uv run --no-sync`.
- No `/all_joint_cmd`, `/change_robot_state`, vendor ROS workspace, system
  Python, launch file, or systemd unit was modified.

Next slice:

- Publish gate design and verification. It must explicitly decide robot state
  prerequisites, `/change_robot_state` behavior, `/all_joint_cmd` subscriber
  behavior, real `cmd_type`, conservative gains, support/stop procedure, and
  operator opt-in before any command publisher is added.
