# T4 Deployment Gates Runbook

This runbook is the operator sequence for the staged T4 low-level deployment.
It assumes the project is extending the existing `real` deployment path to
`robot.variant: t4_29dof` through the local Zvalley SDK checkout in
`zv_robot_sdk/`.

The current implementation is intentionally dry-run only for command paths:
it can subscribe to state, convert state, build SDK command messages, and run
one policy step into a command message. It must not be treated as real motor
control until the publish gate is explicitly implemented and verified.

## Source Artifacts

- PRD: `docs/prd/t4-low-level-deployment.md`
- Issue breakdown: `docs/issues/t4-low-level-deployment-issues.md`
- ADR: `docs/adr/0001-t4-low-level-policy-control.md`
- ADR: `docs/adr/0002-add-t4-as-robot-variant.md`
- Probe script: `scripts/t4_probe_state.py`
- T4 backend: `src/unitree_launcher/robot/t4_robot.py`
- T4 tests: `tests/test_t4_robot.py`, `tests/test_main.py`

## Gate 0: Asset and Config Readiness

Purpose: prove the project is pointing at the expected T4 model, motion, SDK,
and robot variant before touching the robot network.

Required state:

- T4 policy is under `assets/t4/policies/`.
- T4 motion data is under `assets/t4/motions/`.
- T4 XML/URDF evidence is under `assets/robots/t4/`.
- Zvalley SDK checkout exists at `zv_robot_sdk/`.
- T4 config uses `robot.variant: t4_29dof`.

Pass evidence:

```bash
find . -maxdepth 1 -type f \( -name '*t4*' -o -name 'motion.npz' -o -name '*.onnx' \) -print
find assets/robots/t4 -type d -name __pycache__ -o -type f -name '*.pyc'
```

Both commands should print nothing. The assets should remain in the dedicated
T4 directories, not in the repository root.

Do not continue if:

- The config is not `t4_29dof`.
- The policy path does not point at the T4 ONNX.
- The SDK checkout cannot be found.

## Gate 1: Read-Only SDK Probe

Purpose: prove SDK import, DDS initialization, joint state topic, and navigation
topic without creating any command publisher.

Run this first on the T4 official or onboard control environment:

```bash
python scripts/t4_probe_state.py --domain-id 0 --interface eth0 --sdk-root zv_robot_sdk --samples 1 --timeout 5
```

Expected evidence:

- `read_only: true`
- `subscribed: rt/all_joint_state`
- `subscribed_nav: rt/nav_all`, or a clear message that the nav subscriber is unavailable
- `joint_count: 29` for the current 29-DoF policy path
- per-joint position, velocity, torque, and identifier fields when available
- navigation/IMU fields from `rt/nav_all` when available

Interpretation:

- `joint_count: 29` means the current 29-DoF ONNX can continue through the dry-run gates.
- `joint_count: 23` means SDK connectivity may be working, but the current 29-DoF policy is incompatible with that exposed control surface. Stop and retrain/export for the available control surface or find the 29-DoF SDK path.
- no samples means network, DDS domain, interface, robot power, or SDK environment must be fixed before continuing.

Do not continue if:

- `zv_robot_sdk_python` cannot be imported in the target environment.
- `rt/all_joint_state` returns no samples.
- the joint count is unknown.
- the joint order cannot be compared against the policy/XML evidence.

## Gate 1B: Read-Only Onboard ROS2 Probe

Purpose: prove the observed T4 onboard ROS2 control stack can provide the same
state evidence when host-side Zvalley SDK discovery is unavailable.

Copy the probe to the robot if this repository is not already present there,
then run it over SSH:

```bash
scp scripts/t4_ros2_probe_state.py zl@192.168.12.100:/tmp/t4_ros2_probe_state.py
ssh zl@192.168.12.100
source /home/zl/work/bipedal_humanoid_pro/install/setup.bash
python3 /tmp/t4_ros2_probe_state.py --samples 1 --timeout 5
```

Expected evidence:

- `read_only: true`
- `subscribed: /all_joint_state`
- `subscribed_nav: /nav_all`
- `subscribed_robot_state: /robot_state`
- `joint_count: 29`
- per-joint `model_id`, `motor_id`, position, velocity, torque, and error fields
- navigation/IMU-like fields from `/nav_all`
- current robot state from `/robot_state`

Current observed T4 evidence:

- host can reach `192.168.12.100` over Ethernet and SSH as `zl`
- onboard launch command is `ros2 launch robot_system robot.launch.py`
- running nodes include `robot_control`, `bh_gym`, `joy_remote_control`, and
  `yesense_node_publisher`
- `/all_joint_state` type is `robot_msgs/msg/AllJointState`
- `/all_joint_state` publishes 29 joints with `model_id` `0..28`
- `/all_joint_state` frequency is approximately 200 Hz
- `/nav_all` publishes navigation/IMU-like data
- `/robot_state` reported `robot_state: 3` (`CHECK_MOTORS`) during initial
  manual probing and `robot_state: 2` (`STOP`) during the later scripted
  read-only probe
- no command topic was published during probing

Interpretation:

- Gate 1B passing proves the robot-side state/control stack is alive and exposes
  the 29-DoF state surface needed for adapter work.
- Gate 1B does not prove host-side SDK direct DDS discovery works.
- Gate 1B does not authorize publishing `/all_joint_cmd` or changing robot
  state. It is still a read-only gate.

Do not continue to publish-enabled tests if:

- `/all_joint_state` does not produce samples.
- `joint_count` is not 29 for the current 29-DoF policy.
- `/robot_state` reports `ERROR`.
- the robot is not physically supported for any later state transition.

## Gate 2: Backend State Conversion

Purpose: prove the project can represent T4 SDK state as the shared
`RobotState` contract used by policy and safety code.

Current code path:

- `T4Robot.connect()` initializes read-only subscribers for `rt/all_joint_state` and `rt/nav_all`.
- `T4Robot.get_state()` converts cached joint/nav messages to `RobotState`.
- unavailable world-frame base position and velocity use the existing real-robot `NaN` convention.

Local verification:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_robot.py -q
```

Pass evidence:

- fake SDK state converts to 29 joint positions, velocities, and torques
- nav quaternion, gyro, and acceleration convert to IMU fields
- no command publisher is created during read-only state setup

Do not continue if:

- state conversion requires real SDK imports in tests
- missing optional fields crash the backend
- base position or velocity semantics diverge from real-robot `NaN`

## Gate 3: Command Message Conversion, Publish Disabled

Purpose: prove the project can convert a 29-DoF `RobotCommand` into a Zvalley
`AllJointCmd_` message without writing the command topic.

Current code path:

- `T4Robot.build_command_message(cmd)` creates an SDK command message.
- `T4Robot.send_command(cmd)` still raises `NotImplementedError`.
- wrong-length commands fail before SDK conversion.

Local verification:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_robot.py -q
```

Pass evidence:

- 29 command entries are created
- position, velocity, torque, Kp, and Kd fields map without reordering mistakes
- 23-DoF commands fail clearly
- no publisher or `Write()` call happens

Do not continue if:

- a wrong-length command can be silently converted
- the command conversion creates a publisher
- `send_command()` can publish without a later explicit publish gate

## Gate 4: Static Smoke Dry Run

Purpose: validate the static hold/default pose command shape before any policy
output is involved.

Run:

```bash
uv run real --config path/to/t4_real.yaml --t4-static-smoke --duration 0.1 --no-log
```

Current behavior:

- requires `robot.variant: t4_29dof`
- requires a positive `--duration`
- does not require `--policy`
- connects the T4 backend
- builds one static 29-DoF hold command message
- does not call `send_command()`
- exits and disconnects

Pass evidence:

- command completes without importing/loading an active policy
- log line says the static smoke command was built
- no command publication occurs

Do not continue if:

- the path requires an active policy
- the path can run without a duration
- it calls `send_command()` or writes `rt/all_joint_cmd`

## Gate 5: Policy Smoke Dry Run

Purpose: validate ONNX policy output to T4 command-message conversion before
any SDK command publication is enabled.

Run:

```bash
uv run real --config path/to/t4_real.yaml --policy assets/t4/policies/2026-06-10_12-11-59_t4_kick_modified_4096_7000_gpu0.onnx --t4-policy-smoke --duration 0.1 --no-log
```

Current behavior:

- requires `robot.variant: t4_29dof`
- requires a positive `--duration`
- requires `--policy`
- loads the T4 ONNX through the existing policy loader
- reads one `RobotState`
- executes one policy step with zero velocity command
- builds one 29-DoF Zvalley command message
- does not construct Runtime
- does not call `send_command()`
- exits and disconnects

Pass evidence:

- T4 policy loads successfully
- policy output maps to a 29-DoF command message
- no Runtime control loop starts
- no command publication occurs

Do not continue if:

- ONNX metadata does not match `t4_29dof`
- the policy produces a wrong-length command
- the path can run without a duration
- any command topic write occurs

## Gate 6: Future Publish Gate

This gate is not implemented yet.

Before any code may publish `rt/all_joint_cmd`, collect and record:

- Gate 1 probe output from the real T4 environment
- proof that the SDK command surface accepts 29 command entries, not only the 23-entry example in `zv_robot_sdk/examples_py/lowcmd/publisher.py`
- verified emergency stop and power-off procedure
- verified T4 joint order against SDK output, ONNX metadata, and XML/URDF evidence
- conservative Kp/Kd values for a static pose
- bounded duration and explicit operator opt-in
- operator confirmation that the robot is physically supported or safe for the test

The publish-enabled path must be a separate explicit flag. It must not reuse
`--t4-static-smoke` or `--t4-policy-smoke` silently because those flags currently
mean dry-run only.

## Current Verification Suite

Run this before declaring the local T4 porting slice ready:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_ros2_probe_state.py tests/test_t4_probe_state.py tests/test_t4_robot.py tests/test_main.py tests/test_config.py tests/test_factory.py tests/test_safety.py -q
python scripts/t4_ros2_probe_state.py --help
python scripts/t4_probe_state.py --help
```

Expected local evidence:

- T4 CLI gates are covered without real hardware
- the onboard ROS2 read-only probe is covered without real hardware
- fake SDK state and command conversion are covered
- G1 config, factory, main, and safety behavior remain covered by the selected tests
- probe help renders successfully

## Stop Conditions

Stop the T4 deployment sequence if any of the following occurs:

- SDK import fails on the target T4 environment
- read-only state samples are not received
- low-level joint count is not 29 for the current 29-DoF policy
- SDK joint order cannot be reconciled with policy and XML evidence
- nav/IMU fields are missing and no safe fallback has been accepted
- any dry-run path attempts to publish a command
- any command has a dimension other than 29
- `gh` issue publication is still required for project tracking and authentication has not been repaired
