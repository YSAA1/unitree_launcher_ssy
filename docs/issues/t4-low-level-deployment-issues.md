# T4 Low-Level Deployment Issues

Parent PRD: `docs/prd/t4-low-level-deployment.md`

These issues are written as tracer-bullet vertical slices. The configured tracker is GitHub Issues, but the current `gh` token is invalid, so this file is the local source for later publication.

## Proposed Breakdown

1. **Read-only T4 SDK state probe**
   - Blocked by: None
   - User stories covered: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 29, 30

2. **Accept `t4_29dof` as a first-class robot variant**
   - Blocked by: Issue 1 output for final joint-count confidence, but can start with current ONNX/XML evidence
   - User stories covered: 11, 12, 13, 14, 24, 25

3. **Route real mode to a T4 backend from config**
   - Blocked by: Issue 2
   - User stories covered: 15, 16, 17, 24

4. **Convert T4 SDK state into `RobotState` with fake SDK coverage**
   - Blocked by: Issue 1 and Issue 3
   - User stories covered: 18, 19, 26

5. **Convert `RobotCommand` into Zvalley `AllJointCmd_` behind a command-disabled gate**
   - Blocked by: Issue 4
   - User stories covered: 20, 21, 27

6. **Add T4 static pose smoke path before active policy**
   - Blocked by: Issue 5
   - User stories covered: 21, 22, 24, 27

7. **Enable low-amplitude short T4 policy run**
   - Blocked by: Issue 6
   - User stories covered: 20, 23, 24, 26, 27

8. **Document T4 deployment gates and operator runbook**
   - Blocked by: Issues 1-7
   - User stories covered: 10, 26, 27, 28, 29

## Issue 1: Read-only T4 SDK state probe

## What to build

Build a read-only diagnostic probe for T4 that runs in the T4 official or onboard control environment, imports the Zvalley Python SDK, subscribes to `rt/all_joint_state` and the navigation topic `rt/nav_all`, and prints enough state information to determine SDK connectivity, real joint count, joint metadata, available joint state fields, and IMU/navigation field availability. The probe must not publish any command topic.

## Acceptance criteria

- [ ] The probe can run as a script from the repository.
- [ ] The probe attempts to import `zv_robot_sdk_python` and prints a clear install/environment error if unavailable.
- [ ] The probe can load the SDK from a local `zv_robot_sdk` checkout by adding `libs/python` to the Python path.
- [ ] The probe initializes the Zvalley channel factory with a configurable domain id.
- [ ] The probe subscribes to `rt/all_joint_state` by default.
- [ ] The probe prints timestamp, index, and used-for-control fields when present.
- [ ] The probe prints the number of received joint states.
- [ ] The probe prints per-joint identifiers and state fields when present, without crashing when a field is absent.
- [ ] The probe reports whether IMU-like fields are present in joint state and whether navigation fields are available from `rt/nav_all`.
- [ ] The probe has a bounded sample count or timeout so it can be used in automation.
- [ ] Tests cover the probe with a fake SDK and prove that no publisher or command message is created.

## Blocked by

None - can start immediately.

## Issue 2: Accept `t4_29dof` as a first-class robot variant

## What to build

Add T4 as a 29-DoF robot variant that can pass configuration validation, expose a stable T4 joint list, and allow policy joint metadata to map through the existing JointMapper contract.

## Acceptance criteria

- [ ] `t4_29dof` is accepted by config validation.
- [ ] Unknown variants still fail clearly.
- [ ] The T4 joint list has 29 unique names.
- [ ] The T4 joint list order matches the current T4 ONNX metadata and local T4 XML evidence.
- [ ] Existing G1 variants continue to pass current tests.
- [ ] Tests cover T4 config loading and T4 JointMapper behavior.

## Blocked by

Issue 1 for final SDK confidence, but implementation can begin using current ONNX/XML evidence.

## Issue 3: Route real mode to a T4 backend from config

## What to build

Make the existing `real` command select the appropriate real robot backend from configuration, so `g1_29dof` and `g1_23dof` continue to use the Unitree backend while `t4_29dof` uses a T4 backend.

## Acceptance criteria

- [ ] `real` remains the shared entrypoint for true robot backends.
- [ ] G1 real mode continues to select the existing Unitree backend.
- [ ] T4 real mode selects a T4 backend when `robot.variant` is `t4_29dof`.
- [ ] Backend selection failures are clear for unsupported real variants.
- [ ] Tests cover backend selection without requiring a real SDK.

## Blocked by

Issue 2.

## Issue 4: Convert T4 SDK state into `RobotState` with fake SDK coverage

## What to build

Implement T4 state conversion from Zvalley SDK state and navigation messages into the project's `RobotState`, using fake SDK messages for tests. The first version should populate joint state from `AllJointState_`, treat IMU/navigation as coming from `NavAll_` unless probe evidence proves otherwise, and use the existing real-robot `NaN` convention for unavailable world-frame base position and velocity.

## Acceptance criteria

- [ ] T4 state conversion produces `RobotState` with 29 joint positions.
- [ ] Joint velocities and torques are populated when present and defaulted safely when absent.
- [ ] IMU/navigation fields are populated from `NavAll_` when present, or the absence is reported clearly.
- [ ] Missing optional fields produce clear diagnostics or safe defaults.
- [ ] `base_position` and `base_velocity` use `NaN` values when world-frame state is unavailable.
- [ ] Tests use fake SDK messages and do not import the real SDK.

## Blocked by

Issues 1 and 3.

## Issue 5: Convert `RobotCommand` into Zvalley `AllJointCmd_` behind a command-disabled gate

## What to build

Add command conversion from the project's `RobotCommand` to Zvalley `AllJointCmd_`, but keep real command publication behind an explicit disabled-by-default gate until read-only and static validation are complete.

## Acceptance criteria

- [ ] A 29-DoF `RobotCommand` converts into 29 SDK joint commands.
- [ ] Position, velocity, torque, Kp, and Kd are mapped without reordering mistakes.
- [ ] Command publication is disabled by default for T4 until explicitly enabled.
- [ ] Tests prove conversion with fake SDK command objects.
- [ ] Tests prove disabled mode does not publish to the command topic.

## Blocked by

Issue 4.

## Issue 6: Add T4 static pose smoke path before active policy

## What to build

Add a T4 static pose or hold-policy smoke path that can validate position-PD signs, units, joint order, and shutdown behavior before any active ONNX policy is allowed to run.

## Acceptance criteria

- [ ] T4 can run a static hold/default pose path without loading the active policy.
- [ ] The path has a bounded duration.
- [ ] The path requires explicit operator opt-in.
- [ ] Shutdown sends a safe damping or neutral command according to the T4 command gate.
- [ ] Tests cover mode selection and command gating without real hardware.

## Blocked by

Issue 5.

## Issue 7: Enable low-amplitude short T4 policy run

## What to build

Enable an explicitly gated, low-amplitude, short-duration policy run for the T4 ONNX after state, command, and static pose checks have passed.

## Acceptance criteria

- [ ] The T4 ONNX loads through the existing BeyondMimic path.
- [ ] Policy output maps to 29-DoF T4 command targets.
- [ ] The policy run is duration-limited.
- [ ] The policy run requires explicit operator opt-in.
- [ ] Safety checks remain active.
- [ ] Tests verify the runtime path with fake backend/policy components.

## Blocked by

Issue 6.

## Issue 8: Document T4 deployment gates and operator runbook

## What to build

Document the staged T4 deployment workflow, including how to interpret probe output, when 23-DoF means policy incompatibility, how to run each gate, and what evidence is required before moving to the next stage.

## Acceptance criteria

- [ ] The runbook starts with the read-only probe.
- [ ] The runbook explains 29-DoF versus 23-DoF outcomes.
- [ ] The runbook lists required evidence before command publishing.
- [ ] The runbook lists safety stop and rollback expectations.
- [ ] The runbook links the PRD, ADRs, and relevant understanding docs.

## Blocked by

Issues 1-7.
