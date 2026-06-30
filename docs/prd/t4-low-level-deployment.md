# T4 Low-Level Deployment PRD

## Problem Statement

用户已经有 T4 机器人、T4 29-DoF BeyondMimic ONNX policy 和对应 tracking motion 数据，希望把当前 G1 部署程序扩展到 T4，而不是只调用厂商 SDK 的内置动作。当前项目的 Runtime、Policy、Safety、JointMapper 和 RobotInterface 已经形成 G1 真机部署链路，但配置校验、robot variant、真机 backend 和 SDK bridge 都还只围绕 G1/Unitree 设计。用户需要一条可诊断、可分阶段验证的 T4 低层接入路线，避免一开始直接上真机跑 policy 把 SDK、关节顺序、IMU、PD gain、控制权和策略稳定性混在一起。

## Solution

新增 T4 低层部署能力，复用现有 `real` 入口、Runtime、Policy、Safety 和 JointMapper。T4 作为 `t4_29dof` robot variant 进入项目，第一版通过 Zvalley Python SDK bridge 订阅 `rt/all_joint_state`、发布 `rt/all_joint_cmd`，并按只读探针、阻尼/零力矩、静态 pose、低幅短时 policy run 的安全门推进。

第一阶段只交付只读 SDK 探针，不接 Runtime、不发布命令。探针运行在 T4 官方/板载控制环境，证明 SDK import、DDS 初始化、状态 topic、导航 topic、真实 joint count、joint metadata、关节状态字段和导航/IMU 字段。若 SDK 只暴露 23-DoF 控制面，则判定为当前 29-DoF policy 不适配该 SDK 控制面，而不是 T4 SDK 连接链路失败。

## User Stories

1. As a robotics developer, I want to verify that the T4 SDK can be imported on the robot control environment, so that I know the deployment environment has the required vendor library.
2. As a robotics developer, I want to initialize the Zvalley DDS channel factory from a read-only probe, so that I can validate SDK connectivity without sending motor commands.
3. As a robotics developer, I want to subscribe to `rt/all_joint_state`, so that I can prove the software can receive T4 low-level state.
4. As a robotics developer, I want to print the real number of returned joint states, so that I can determine whether the SDK exposes 29-DoF or 23-DoF at the low-level control surface.
5. As a robotics developer, I want to print each joint's available identifiers, so that I can compare SDK order with the ONNX metadata and T4 XML order.
6. As a robotics developer, I want to print joint position, velocity, torque, and error fields when available, so that I can determine which fields can populate `RobotState`.
7. As a robotics developer, I want the probe to detect and report missing fields gracefully, so that SDK message differences do not crash the first diagnostic run.
8. As a robotics developer, I want the probe to report whether IMU fields exist, so that I can decide whether `T4Robot.get_state()` can populate orientation and angular velocity directly.
9. As a robotics developer, I want the probe to never publish `AllJointCmd_`, so that the first T4 test is mechanically safe.
10. As a robotics developer, I want a documented interpretation of 23-DoF versus 29-DoF probe output, so that I can decide whether to continue with the current policy or retrain/export another one.
11. As a robotics developer, I want T4 to be represented as `t4_29dof`, so that policy loading and joint mapping can use the existing variant-to-joint-list mechanism.
12. As a robotics developer, I want T4 policy metadata to map through `JointMapper`, so that ONNX joint order can be checked against robot-native order.
13. As a robotics developer, I want the T4 ONNX policy to load as a BeyondMimic policy, so that existing observation and action code can be reused.
14. As a robotics developer, I want `motion.npz` and ONNX dimensions to be documented, so that the deployment path has an evidence-backed model contract.
15. As a robotics developer, I want T4 to reuse `uv run real --config ... --policy ...`, so that true robot deployment has one mental model across G1 and T4.
16. As a robotics developer, I want backend selection to be driven by config, so that `real` means real robot and not a hard-coded G1 path.
17. As a robotics developer, I want a `T4Robot` backend to implement `RobotInterface`, so that Runtime can operate without T4-specific policy logic.
18. As a robotics developer, I want `T4Robot.get_state()` to convert SDK state into `RobotState`, so that policy and safety code remain robot-agnostic.
19. As a robotics developer, I want T4 real state to use `NaN` for unavailable world-frame base position and velocity, so that it matches the existing real-robot semantics.
20. As a robotics developer, I want T4 command conversion to map `RobotCommand` to `AllJointCmd_`, so that Runtime outputs can reach the SDK low-level command topic.
21. As a robotics developer, I want a damping or zero-command smoke test before any policy run, so that command publication and safety shutdown can be validated first.
22. As a robotics developer, I want a static pose or hold-policy test before active policy run, so that joint signs, units, order, and PD gains can be validated independently.
23. As a robotics developer, I want a low-amplitude short policy run after static validation, so that the full ONNX-to-SDK loop is tested with controlled risk.
24. As a robotics developer, I want G1 behavior to remain unchanged, so that adding T4 does not regress the existing deployment stack.
25. As a robotics developer, I want tests to fail clearly when `t4_29dof` is unsupported or mismatched, so that configuration mistakes are caught before real-robot use.
26. As a robotics developer, I want the implementation to distinguish SDK connection failure from policy/model mismatch, so that retraining decisions are based on evidence.
27. As a robotics developer, I want T4 safety limits and shutdown behavior to be explicit before command publishing, so that real-robot risk is controlled.
28. As a robotics developer, I want docs and ADRs to explain why low-level control was chosen, so that future maintainers do not replace it with high-level built-in action calls.
29. As a robotics developer, I want issue-sized implementation slices, so that each stage can be verified independently before moving closer to real motor commands.
30. As a robotics developer, I want test-first changes for each slice, so that behavior is specified before implementation and regressions are detectable.

## Implementation Decisions

- T4 will be integrated through the low-level SDK path, not through vendor high-level action/model switching.
- T4 will initially be represented as a robot variant named `t4_29dof`.
- T4 will reuse the existing `real` command and runtime assembly path.
- The first bridge will use the Zvalley Python SDK, not a new C++ binding.
- The local SDK checkout is `zv_robot_sdk/`; the probe can add `zv_robot_sdk/libs/python` to the Python import path.
- The first implementation slice is a read-only state probe that does not publish commands.
- The read-only probe is expected to run first on the T4 official or onboard control environment.
- The probe must make missing SDK fields diagnosable rather than fatal wherever possible.
- A 23-DoF low-level SDK result is treated as current-policy incompatibility, not proof that SDK connectivity failed.
- The first real T4 backend will implement the existing `RobotInterface` contract.
- T4 true world-frame base position and velocity are out of scope for the first backend; unavailable values use the existing real-robot `NaN` convention.
- The deployment path must keep the current G1 behavior intact.
- Real motor command publishing is gated behind read-only state verification and later explicit smoke tests.

## Testing Decisions

- Tests should verify public behavior: CLI/probe output, config acceptance/rejection, policy loading, RobotInterface behavior, and command/state conversion.
- The first TDD seam is the read-only T4 probe behavior, tested with fake SDK objects injected through the probe's public function boundary.
- Config tests should cover `t4_29dof` as an accepted variant once that slice begins, while preserving existing G1 variant behavior.
- Policy tests should cover loading the provided T4 BeyondMimic ONNX metadata contract if the model is available, or use a fixture with equivalent metadata if large binary artifacts are not suitable for CI.
- Backend tests should use a fake Zvalley SDK module to verify state, navigation, and command conversion without requiring a robot.
- Runtime tests should only be expanded once a T4 backend exists; they should verify backend selection and non-regression, not SDK internals.
- Real robot verification remains manual/operator-gated and must follow staged safety gates.

## Out of Scope

- Training or retraining the T4 policy.
- Changing the ONNX policy architecture.
- Guaranteeing T4 SDK support for 29-DoF before probe evidence exists.
- Implementing a C++ Zvalley bridge in the first pass.
- Publishing low-level motor commands in the first implementation slice.
- Replacing the G1 Unitree backend.
- Adding high-level Zvalley action/model switching as the main deployment path.
- Solving world-frame base pose estimation for T4 in the first backend.

## Further Notes

- Current evidence shows `assets/t4/policies/2026-06-10_12-11-59_t4_kick_modified_4096_7000_gpu0.onnx` has `obs [1,154]`, `time_step [1,1]`, 29-dimensional actions and reference joint outputs, and metadata joint names matching the local T4 XML joint order.
- Current evidence shows `assets/t4/motions/motion.npz` is 50 Hz, 765 frames, 29 joint positions/velocities, and 30 body reference poses.
- Local Zvalley SDK examples in `zv_robot_sdk/` show `rt/all_joint_state` and `rt/all_joint_cmd`, but their lowcmd example fills 23 joint commands. This must be resolved by the read-only probe before real command publishing.
- Local Zvalley SDK examples also show `rt/nav_all` for navigation/IMU-like data, so IMU source remains a probe-driven decision.
