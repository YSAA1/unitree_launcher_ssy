# Add T4 as a Robot Variant

We will represent T4 as `robot.variant = "t4_29dof"` and add a T4 joint list to the existing variant-to-joints mechanism. This keeps the initial port aligned with the current config, policy loading, gain validation, and JointMapper flow, all of which already depend on `robot.variant`.

**Considered Options**

- Add `t4_29dof` to the existing variant model: smallest change and easiest to verify against the 29-DoF ONNX metadata.
- Add a separate `robot.backend` or `robot.type` model immediately: cleaner for many robot families, but broader than needed for the first T4 port.

**Consequences**

The first T4 port keeps `variant` as both kinematic identity and backend selection signal. If more robot families are added later, `variant` and `backend` may need to be split.
