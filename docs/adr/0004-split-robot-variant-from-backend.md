# Split Robot Variant from Backend

We will separate robot model identity from the real-robot communication
backend.

**Context**

The original code path used `robot.variant` as the main signal for both joint
identity and real backend selection. That was sufficient while the project only
had G1 real deployment through `unitree_cpp`. T4 now has at least two plausible
communication surfaces: Zvalley SDK DDS and the observed onboard ROS2 stack.

**Considered Options**

- Keep selecting the T4 backend only from `robot.variant = "t4_29dof"`: smaller
  config change, but it makes `variant` mean both kinematic identity and
  communication transport.
- Add a backend field: slightly more config surface, but it makes the deployment
  path explicit and prevents accidentally running the wrong T4 adapter.

**Decision**

Use `robot.variant` for robot model and joint-list identity, and use a separate
backend field for the communication adapter. Existing G1 configs may continue to
default to the current Unitree C++ backend. T4 configs must explicitly select a
backend such as `t4_ros2` or `t4_sdk_dds`.

**Consequences**

T4 deployment configs become more explicit. `variant: t4_29dof` says the policy
and joint mapping are 29-DoF T4; `backend: t4_ros2` says the process should use
the onboard ROS2 adapter. This avoids mixing the SDK DDS investigation path with
the current ROS2 deployment path.
