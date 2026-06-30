# Unitree G1 Deployment Stack

Control stack for the Unitree G1 humanoid robot. Supports MuJoCo simulation (macOS/Linux) and onboard real robot deployment (G1 Jetson Orin). Runs ONNX neural network policies at 50 Hz with safety enforcement.

## Modes

| Mode | Command | Description |
|------|---------|-------------|
| **sim** | `uv run sim` | MuJoCo simulation (GUI, Viser, or headless) |
| **eval** | `uv run eval` | Accurate evaluation (1000 Hz physics, headless) |
| **real** | `uv run real` | Onboard G1 deployment (C++ DDS backend) |
| **mirror** | `uv run mirror` | Read-only DDS visualization of the real robot |
| **replay** | `uv run replay` | Play back logged data (GUI, Viser, or summary/CSV) |

## Supported Policies

- **IsaacLab** — Velocity-tracking locomotion (arrow key / stick controls)
- **BeyondMimic** — Motion-tracking with trajectory playback and ONNX metadata gains

## Requirements

- Python 3.10
- [uv](https://docs.astral.sh/uv/) package manager
- macOS (Apple Silicon) or Linux (x86_64 / aarch64)
- Real robot: Linux + C++ unitree_interface binding

## Quick Start

```bash
# Install
uv sync

# Simulation with MuJoCo GUI (macOS needs mjpython)
uv run sim --gui --policy assets/policies/stance_29dof.onnx

# Simulation with web viewer
uv run sim --viser --policy assets/policies/beyondmimic_29dof.onnx
# Open http://localhost:8080

# Headless evaluation
uv run eval --steps 500 --policy assets/policies/stance_29dof.onnx

# Replay logged data
uv run replay logs/run_name/ --gui
uv run replay logs/run_name/ --viser --speed 0.5 --loop

# Run tests
uv run pytest tests/ -x
```

## Gantry Arm Test (Sim2Real)

The `--gantry` flag runs a right shoulder pitch sinusoid while the robot hangs from a gantry. Used for sim2real comparison — the same test runs identically in sim and on real hardware.

```bash
# Sim with GUI viewer
uv run sim --gantry --gui --duration 40

# Sim with viser
uv run sim --gantry --viser --duration 40

# Real robot (on G1, after deploy — press Start when ready)
uv run real --gantry --duration 40

# Compare logged data
uv run python scripts/compare_sim2real.py logs/<sim_run>/ logs/<real_run>/
```

The test sequence:
1. **Prepare** (5s): Smooth blend from current pose to home position
2. **Hold**: Waits for Start button (real) or Space (sim) before continuing
3. **Sinusoid**: Right shoulder pitch sweeps through quarter ROM (negative direction only, 0.2 Hz)

All infrastructure is active: wireless E-stop (A button), gamepad, keyboard, data logging, video recording (`--record`).

## Real Robot Deployment

### Network

| Node | IP |
|------|----|
| Motor control board | `192.168.123.161` |
| G1 PC (SSH) | `192.168.123.164` (user: `unitree`, pass: `123`) |
| Dev machine | `192.168.123.100` (configure with `./scripts/setup_robot_network.sh`) |

### Deploy to Robot

```bash
# Sync code and run preflight checks (auto-installs uv if needed)
./scripts/deploy_to_robot.sh

# SSH in and build C++ backend (first time only)
ssh unitree@192.168.123.164
cd ~/unitree_launcher
./scripts/build_cpp_backend.sh

# Run (press Start on wireless controller after prepare completes)
uv run real --policy assets/policies/stance_29dof.onnx
```

## Experimental T4 Probe

T4 low-level deployment is being investigated as a separate staged port. The
first safe gate is read-only: subscribe to Zvalley SDK state and do not publish
any command topic.

```bash
python scripts/t4_probe_state.py --domain-id 0 --interface eth0 --sdk-root zv_robot_sdk --samples 1 --timeout 5
```

The probe is intended to run first on the T4 official or onboard control
environment where `zv_robot_sdk_python` and the DDS network are already
available. It subscribes to `rt/all_joint_state` and `rt/nav_all`, prints the
real joint count and available state/navigation fields, and intentionally never
creates an `rt/all_joint_cmd` publisher.

On the current observed T4 robot, the onboard control stack is a ROS2 workspace
at `/home/zl/work/bipedal_humanoid_pro`, and host-side SDK probing did not
receive samples while the robot was publishing ROS2 state locally. Use the ROS2
read-only probe on the robot after sourcing the onboard workspace:

```bash
scp scripts/t4_ros2_probe_state.py zl@192.168.12.100:/tmp/t4_ros2_probe_state.py
ssh zl@192.168.12.100
source /home/zl/work/bipedal_humanoid_pro/install/setup.bash
python3 /tmp/t4_ros2_probe_state.py --samples 1 --timeout 5
```

This subscribes to `/all_joint_state`, `/nav_all`, and `/robot_state`, prints
the joint count and state fields, and never creates an `/all_joint_cmd`
publisher.

T4 configs must set both robot identity and communication backend:

```yaml
robot:
  variant: t4_29dof
  backend: t4_ros2     # or t4_sdk_dds for the Zvalley SDK path
```

`t4_sdk_dds` routes to `T4Robot`, which subscribes read-only to
`rt/all_joint_state` and `rt/nav_all` when the Zvalley SDK environment is
available. `t4_ros2` routes to `T4Ros2Robot`, which subscribes read-only to
`/all_joint_state`, `/nav_all`, and `/robot_state` on the observed onboard ROS2
stack. Both backends can build a 29-DoF command message from a project
`RobotCommand`; both keep command publishing disabled. Do not treat T4 `real`
mode as a motor-control path until a separate publish gate is implemented.

The current static-pose smoke gate is a dry run: it builds one bounded 29-DoF
hold command message and exits without publishing.

```bash
uv run real --config configs/t4_ros2_real.yaml --t4-static-smoke --duration 0.1 --no-log
```

The current policy smoke gate is also a dry run: it loads the T4 ONNX, reads
one real state sample, executes one policy step, builds one 29-DoF command
message, and exits without publishing.

```bash
uv run real --config configs/t4_ros2_real.yaml --policy assets/t4/policies/2026-06-10_12-11-59_t4_kick_modified_4096_7000_gpu0.onnx --t4-policy-smoke --duration 0.1 --no-log
```

Latest T4 ROS2 full-project smoke evidence on the robot:

```text
[main] T4 policy smoke built one 29-DoF policy command for 0.100s; state_timestamp=5460731976.000000; command publishing remains disabled.
```

The T4 porting PRD and implementation slices are tracked in:

- `docs/prd/t4-low-level-deployment.md`
- `docs/issues/t4-low-level-deployment-issues.md`
- `docs/plans/2026-06-30--t4-porting-grill.md`
- `docs/plans/2026-06-30--t4-ros2-policy-smoke-plan.md`
- `docs/runbooks/t4-deployment-gates.md`

Current local T4 assets are organized under:

- `assets/t4/policies/`
- `assets/t4/motions/`
- `assets/robots/t4/`
- `zv_robot_sdk/` for the local Zvalley SDK checkout

### Wireless Controller (Real Robot)

| Button | Action |
|--------|--------|
| **A** | E-stop (software, checked every tick) |
| **L2+B** | Hardware damping mode (firmware-level, always works) |
| **B** | Stop policy (return to stance) |
| **X** | Resume / re-activate policy |
| **Y** | Reset policy (stop + reset + re-prepare) |
| **Start** | Start policy (also activates after prepare hold) |
| **Select** | Stop policy |
| **Left stick** | Forward/back (Y) and strafe (X) |
| **Right stick X** | Yaw rate |
| **R1 + DPad Up/Down** | Next / previous policy |

### Prepare Phase

On real hardware, a 5-second prepare phase blends from the current pose to the default stance:
- Linear ramp (80% of duration) from current motor positions to home pose
- Policies warm up (ONNX session + observation history) during prepare
- Wireless A-button E-stop is active throughout
- At 90%, policy state is reset for clean activation
- After prepare, the robot **holds pose** until you press **Start** (wireless) or **Space** (keyboard)
- Use `--auto` to skip the hold and activate the policy immediately

## Keyboard Controls (Simulation)

| Key | Action |
|-----|--------|
| `Space` | Toggle policy (start / stop, also activates after prepare hold) |
| `Backspace` | E-stop (latching) |
| `Enter` | Clear E-stop |
| `Delete` | Reset robot and policy |
| `Up` / `Down` | Forward / back velocity (±0.1) |
| `Left` / `Right` | Strafe velocity (±0.1) |
| `,` / `.` | Yaw rate (±0.1) |
| `/` | Zero all velocity |
| `=` / `-` | Next / previous policy |

## Web Viewer (Viser)

```bash
uv run sim --viser --policy path/to/policy.onnx
# Open http://localhost:8080
```

Sidebar controls: Start/Stop, E-stop, Reset, policy selector, velocity sliders, telemetry panel (Hz, inference time, height, step count).

## Configuration

YAML configs in `configs/`. Each mode auto-selects its config — no `-c` needed unless overriding.

| Config | Auto-selected by | Description |
|--------|------------------|-------------|
| `sim.yaml` | `sim`, `eval`, `mirror` | Simulation defaults (500 Hz physics, domain ID 1) |
| `real.yaml` | `real` | Onboard deployment (eth0, domain ID 0, tilt/frame-drop checks) |
| `t4_ros2_real.yaml` | explicit `--config` | T4 onboard ROS2 read-only policy smoke config |
| `unsafe.yaml` | `--preset unsafe` | Disables tilt check and joint position limits |

Key settings:
```yaml
control:
  policy_frequency: 50    # Policy inference rate (Hz)
  sim_frequency: 500      # MuJoCo physics rate (Hz)
  kd_damp: 8.0            # Damping gain for safety/non-controlled joints
  transition_steps: 5     # Steps to interpolate to policy starting pose

safety:
  tilt_check: true        # E-stop on >57° tilt
  frame_drop_check: true  # E-stop on >200ms frame drop
```

## Policy Transitions

- **Activation**: Cosine-interpolates from current position to `default_pos` over `transition_steps` (default 5). Policy `warmup()` runs during transition (ONNX + obs history).
- **Return to stance**: Instant (stance policy needs full authority immediately).
- **BeyondMimic**: Holds at first reference frame for 5 steps before advancing. ONNX metadata `start_timestep` / `end_timestep` trims unstable trajectory edges.

## Docker

Build the image from the repo root:

```bash
docker build -f docker/Dockerfile -t unitree-launcher .
```

Run directly:

Policy files are gitignored and not baked into the image — mount them with `-v`:

```bash
# Headless simulation
docker run --rm -v ./assets/policies:/app/assets/policies:ro \
    unitree-launcher sim --policy assets/policies/stance_29dof.onnx --duration 10

# Headless evaluation (1000 Hz physics)
docker run --rm -v ./assets/policies:/app/assets/policies:ro \
    unitree-launcher eval --steps 500 --policy assets/policies/stance_29dof.onnx

# Viser web viewer (open http://localhost:8080)
docker run --rm -p 8080:8080 -v ./assets/policies:/app/assets/policies:ro \
    unitree-launcher sim --viser --play

# Mirror real robot via viser (Linux, host networking for DDS)
docker run --rm --network host unitree-launcher mirror --viser --interface eth0

# Real robot (Linux, host networking for DDS, C++ backend)
docker build -f docker/Dockerfile --build-arg BUILD_CPP_BACKEND=1 -t unitree-launcher-real .
docker run --rm --network host -v ./assets/policies:/app/assets/policies:ro \
    unitree-launcher-real real --policy assets/policies/stance_29dof.onnx

# X11 GUI (Linux only)
xhost +local:docker
docker run --rm -e DISPLAY=$DISPLAY -e MUJOCO_GL=glx \
    -v /tmp/.X11-unix:/tmp/.X11-unix -v ./assets/policies:/app/assets/policies:ro \
    unitree-launcher sim --gui --policy assets/policies/stance_29dof.onnx
```

### Docker Compose Profiles

| Profile | Services | Description |
|---------|----------|-------------|
| `headless` | `sim-headless`, `eval` | EGL rendering, no display needed |
| `gui` | `sim-gui` | X11 forwarding (Linux only) |
| `viser` | `sim-viser`, `mirror` | Viser web viewer on port 8080 |
| `real` | `real-robot` | Host networking + C++ backend |
| `test` | `test` | pytest runner |

```bash
# Headless sim
docker compose -f docker/docker-compose.yml --profile headless run --rm sim-headless \
    sim --policy assets/policies/stance_29dof.onnx --duration 10

# Evaluation
docker compose -f docker/docker-compose.yml --profile headless run --rm eval \
    eval --steps 500 --policy assets/policies/stance_29dof.onnx

# Viser sim
docker compose -f docker/docker-compose.yml --profile viser run --rm sim-viser \
    sim --viser --policy assets/policies/stance_29dof.onnx

# Tests
docker compose -f docker/docker-compose.yml --profile test run --rm test
```

**Note:** X11 GUI forwarding requires Linux with an X server. macOS does not support X11 forwarding to Docker containers natively — use `--viser` instead.

## Project Structure

```
src/unitree_launcher/
  main.py                     # CLI entry point, viewer/headless runners
  config.py                   # Joint constants, dataclasses, YAML loading
  mirror.py                   # Mirror mode entry point (DDS → MuJoCo viewer)
  replay.py                   # Replay mode entry point (logged data → viewer)
  gantry.py                   # Elastic band + gantry simulation utilities
  trajectory.py               # Collision-aware IK trajectory planning
  recording.py                # MuJoCo video recording (MP4)
  compat.py                   # unitree_sdk2py patches, cross-platform helpers
  script_utils.py             # Shared helpers for diagnostic scripts
  control/
    runtime.py                # Step-based control loop, transitions, state machine
    safety.py                 # Safety controller, E-stop, command clamping
    gamepad.py                # Gamepad monitor (E-stop via USB HID)
  policy/
    base.py                   # Policy ABC, action smoothing, warmup()
    isaaclab_policy.py        # IsaacLab velocity-tracking policy
    beyondmimic_policy.py     # BeyondMimic motion-tracking policy
    hold_policy.py            # Static PD hold at home pose
    sinusoid_policy.py        # Joint sinusoid for gantry testing
    joint_mapper.py           # Robot ↔ policy joint ordering
    factory.py                # Policy loading, gain overrides, preloading
  robot/
    base.py                   # RobotState, RobotCommand, RobotInterface ABC
    sim_robot.py              # MuJoCo simulation backend
    real_robot.py             # C++ unitree_interface backend (onboard)
    mirror_robot.py           # Read-only Python DDS backend
  controller/
    input.py                  # InputManager (merges all controllers)
    keyboard.py               # Keyboard input (GLFW keys)
    wireless.py               # Unitree wireless gamepad (real robot)
    gamepad_input.py          # USB HID gamepad (sim/real)
    viser_input.py            # Viser web UI input
  estimation/
    state_estimator.py        # InEKF + contact detection + FK
    inekf.py                  # Invariant Extended Kalman Filter
    contact.py                # Contact detection (GRF thresholding)
    kinematics.py             # Leg forward kinematics (Jacobian)
    lie_group.py              # SO(3)/SE(3) Lie group operations
  datalog/
    logger.py                 # HDF5/NPZ time-series logging
    replay.py                 # Log loading, state reconstruction, CSV export
  viz/
    viser_viewer.py           # Web-based 3D viewer
    conversions.py            # MuJoCo geom → trimesh

configs/                      # YAML configuration presets
assets/robots/g1/             # MuJoCo XML models + meshes
assets/policies/              # ONNX policy files
scripts/                      # Shell helpers (deploy, build, network setup)
tests/                        # 505 automated tests
```

## Testing

```bash
uv run pytest tests/ -x              # All tests
uv run pytest tests/ -k transition   # Specific tests
uv run pytest tests/ -m "not slow"   # Skip slow tests
```

## State Estimator

An InEKF state estimator fuses IMU predictions with contact-foot kinematics (leg Jacobian).

- **Real mode**: Always on — the estimator is the only source of base state.
- **Sim mode**: Opt-in with `--estimator` to validate estimator-in-the-loop before hardware.
- **Tuning**: Add `--estimator-verbose` for diagnostic output. See [`docs/estimator_tuning.md`](docs/estimator_tuning.md).

Two estimation modes:

| Mode | Flag | Estimates | Default for |
|------|------|-----------|-------------|
| **pos+vel** | _(default)_ | `base_position`, `base_velocity` | Real and sim |
| **pos+vel+imu** | `--estimate-imu` | Above + smoothed `imu_quaternion`, bias-corrected `imu_angular_velocity` | Policies trained with filtered IMU |

Most policies are trained with raw IMU in Isaac Lab — use the default mode. Only add `--estimate-imu` for policies explicitly trained with filtered IMU inputs.

```bash
# Sim: test estimator against MuJoCo ground truth
uv run sim --estimator --policy assets/policies/beyondmimic_29dof.onnx

# Real: estimator is automatic, verbose for tuning
uv run real --estimator-verbose --policy assets/policies/stance_29dof.onnx

# Full estimation (pos+vel+imu) for policies that expect filtered IMU
uv run real --estimate-imu --policy assets/policies/filtered_imu_policy.onnx
```

## Safety

- **Joint limits**: Commands clamped to physical joint position/velocity/torque ranges
- **Tilt detection**: E-stop on >57° tilt from vertical (every tick)
- **Frame drop**: E-stop on >200ms control loop stall
- **Wireless E-stop**: A-button checked in `get_state()` (tightest Python loop)
- **Hardware fallback**: L2+B on wireless controller triggers firmware-level damping
- **Exception handling**: Any control loop exception triggers immediate E-stop
- **E-stop latching**: Persists until explicitly cleared

## Acknowledgments

This project is an independent implementation inspired by the design and architecture of:

- [RoboJuDo](https://github.com/HansZ8/RoboJuDo) by HansZ8 — Plug-and-play deployment framework for humanoid robots (CC BY 4.0)
- [unitree_cpp](https://github.com/HansZ8/unitree_cpp) by GDDG08 — C++ binding for Unitree G1 motor control (CC BY 4.0)

Third-party licenses are in the [`licenses/`](licenses/) directory.
