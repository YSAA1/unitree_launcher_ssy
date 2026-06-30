# Unitree Launcher Resources

## Knowledge

- [README.md](README.md)
  Primary operator guide. Use for modes, commands, real-robot deployment notes, controls, and configuration defaults.
- [CLAUDE.md](CLAUDE.md)
  Project rules and compressed architecture notes. Use for coding discipline and stable local vocabulary.
- [study_plan.md](study_plan.md)
  High-level mental model. Use as orientation, not as execution state.
- [docs/plans/2026-06-29--unitree-launcher-learning-plan.md](docs/plans/2026-06-29--unitree-launcher-learning-plan.md)
  Active executable learning plan and verification contract.
- [docs/tutorials/trained-policy-to-g1-deployment.md](docs/tutorials/trained-policy-to-g1-deployment.md)
  Visual mental model and step-by-step guide for deploying a trained ONNX policy to a Unitree G1 robot.
- [docs/understanding/robot-sdk-porting-workflow.md](docs/understanding/robot-sdk-porting-workflow.md)
  Data-flow tutorial for the current G1 SDK path and the minimum workflow for porting to another robot SDK.
- [docs/understanding/lesson-01-cli-to-runtime-assembly.md](docs/understanding/lesson-01-cli-to-runtime-assembly.md)
  First sensemaking lesson: how `uv run real --policy ...` becomes `Runtime(robot, policy, safety, input)`.
- [docs/prd/t4-low-level-deployment.md](docs/prd/t4-low-level-deployment.md)
  PRD for adding T4 low-level deployment through the existing Runtime and a staged Zvalley SDK bridge.
- [docs/issues/t4-low-level-deployment-issues.md](docs/issues/t4-low-level-deployment-issues.md)
  Local source for T4 implementation issues; publish to GitHub once `gh` authentication is repaired.
- [docs/runbooks/t4-deployment-gates.md](docs/runbooks/t4-deployment-gates.md)
  Operator runbook for staged T4 deployment gates from read-only probe through dry-run policy smoke and future publish prerequisites.
- [docs/plans/2026-06-30--t4-porting-grill.md](docs/plans/2026-06-30--t4-porting-grill.md)
  Decision record and evidence from the T4 low-level porting grill session.
- [docs/plans/2026-06-30--t4-ros2-policy-smoke-plan.md](docs/plans/2026-06-30--t4-ros2-policy-smoke-plan.md)
  Executable plan and completion evidence for the T4 ROS2 full-project policy smoke dry-run slice.
- [docs/adr/0001-t4-low-level-policy-control.md](docs/adr/0001-t4-low-level-policy-control.md)
  ADR choosing low-level T4 policy control instead of vendor high-level action switching.
- [docs/adr/0002-add-t4-as-robot-variant.md](docs/adr/0002-add-t4-as-robot-variant.md)
  ADR choosing `t4_29dof` as the first T4 representation in the existing robot variant model.
- [docs/adr/0003-use-onboard-ros2-adapter-for-t4.md](docs/adr/0003-use-onboard-ros2-adapter-for-t4.md)
  ADR choosing the observed onboard ROS2 adapter as the next T4 deployment path.
- [docs/adr/0004-split-robot-variant-from-backend.md](docs/adr/0004-split-robot-variant-from-backend.md)
  ADR separating robot model identity from communication backend selection.
- [scripts/t4_probe_state.py](scripts/t4_probe_state.py)
  Read-only T4 SDK probe. Use on the T4 control environment to inspect `rt/all_joint_state` without publishing commands.
- [scripts/t4_ros2_probe_state.py](scripts/t4_ros2_probe_state.py)
  Read-only T4 onboard ROS2 probe. Use after sourcing the T4 ROS2 workspace to inspect `/all_joint_state`, `/nav_all`, and `/robot_state` without publishing commands.
- [src/unitree_launcher/robot/t4_robot.py](src/unitree_launcher/robot/t4_robot.py)
  T4 real-mode backend boundary. It subscribes read-only to Zvalley joint/nav state, builds SDK command messages, and remains publish-disabled until static-pose gates are implemented.
- [src/unitree_launcher/robot/t4_ros2_robot.py](src/unitree_launcher/robot/t4_ros2_robot.py)
  T4 onboard ROS2 backend. It subscribes read-only to `/all_joint_state`, `/nav_all`, and `/robot_state`, waits for a real joint-state sample, builds ROS2 `AllJointCmd`, and remains publish-disabled.
- [configs/t4_ros2_real.yaml](configs/t4_ros2_real.yaml)
  T4 onboard ROS2 read-only policy smoke config using `robot.variant: t4_29dof` and `robot.backend: t4_ros2`.
- [tests/test_t4_probe_state.py](tests/test_t4_probe_state.py)
  Fake-SDK tests for the read-only T4 probe behavior.
- [tests/test_t4_ros2_probe_state.py](tests/test_t4_ros2_probe_state.py)
  Fake-rclpy tests for the read-only T4 onboard ROS2 probe behavior.
- [tests/test_t4_robot.py](tests/test_t4_robot.py)
  Fake-SDK tests for T4 backend state conversion, command-message conversion, and command-disabled behavior.
- [tests/test_t4_ros2_robot.py](tests/test_t4_ros2_robot.py)
  Fake-rclpy tests for T4 ROS2 backend state conversion, first-state waiting, command-message conversion, and command-disabled behavior.
- [tests/test_main.py](tests/test_main.py)
  Includes T4 real-mode routing, `--t4-static-smoke`, and `--t4-policy-smoke` dry-run wiring coverage.
- [assets/t4/policies/](assets/t4/policies/)
  Local T4 ONNX policy artifacts supplied for the low-level deployment investigation.
- [assets/t4/motions/](assets/t4/motions/)
  Local T4 tracking motion artifacts such as `motion.npz`.
- [assets/robots/t4/](assets/robots/t4/)
  Local T4 XML/URDF robot assets used as joint-order evidence.
- [zv_robot_sdk/](zv_robot_sdk/)
  Local Zvalley SDK checkout with Python/C++ examples and Python binding libraries.
- [CONTEXT.md](CONTEXT.md)
  Canonical glossary for stable project terms such as SDK, backend, `RobotState`, `RobotCommand`, `Runtime`, and `RealRobot`.
- [src/unitree_launcher/main.py](src/unitree_launcher/main.py)
  CLI and object wiring source of truth. Use for mode parsing, config selection, robot/policy/safety/runtime construction, and runner selection.
- [src/unitree_launcher/config.py](src/unitree_launcher/config.py)
  Configuration and robot constants source of truth. Use for YAML schema, defaults, validation, joint names, limits, and CLI overrides.
- [tests/test_main.py](tests/test_main.py)
  Executable expectations for mode parsing, config overrides, wiring, and runner behavior.
- [Python argparse documentation](https://docs.python.org/3/library/argparse.html)
  Official source for `ArgumentParser`, `add_argument`, `parse_args`, `Namespace`, and subcommands.
- [src/unitree_launcher/robot/base.py](src/unitree_launcher/robot/base.py)
  Source of truth for `RobotState`, `RobotCommand`, and `RobotInterface`.
- [src/unitree_launcher/policy/base.py](src/unitree_launcher/policy/base.py)
  Source of truth for the policy interface used by Runtime.
- [tests/test_runtime.py](tests/test_runtime.py)
  Tests showing Runtime calls policy, sends commands, handles E-stop, and updates telemetry.
- [src/unitree_launcher/robot/real_robot.py](src/unitree_launcher/robot/real_robot.py)
  Source of truth for real robot connection, state reading, command sending, and C++ backend use.
- [configs/real.yaml](configs/real.yaml)
  Real robot default network, safety, and logging configuration.
- [scripts/deploy_to_robot.sh](scripts/deploy_to_robot.sh)
  Code sync and robot-side preflight checks.
- [scripts/build_cpp_backend.sh](scripts/build_cpp_backend.sh)
  Robot-side C++ SDK and `unitree_cpp` binding build path.
- [src/unitree_launcher/controller/wireless.py](src/unitree_launcher/controller/wireless.py)
  Wireless controller button and stick parsing for real mode.

## Wisdom

- Local test suite: `uv run pytest tests/ -x`
  Use as the first feedback loop before trusting any code-level understanding.

## Gaps

- No external community or upstream docs have been selected yet. For this first slice, local source and tests are higher-trust than broad web material.
