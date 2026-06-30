# Use Onboard ROS2 Adapter for T4

We will continue the T4 deployment path through an onboard ROS2 adapter instead
of making host-side Zvalley SDK DDS discovery the next blocking step.

**Context**

The connected T4 publishes `/all_joint_state`, `/nav_all`, and `/robot_state`
inside its onboard ROS2 workspace at `/home/zl/work/bipedal_humanoid_pro`.
The read-only ROS2 probe received 29 joint states plus navigation data and robot
state from the robot. Host-side Zvalley SDK probing initialized subscriptions
but did not receive samples from `rt/all_joint_state` under the current robot
network/configuration.

**Considered Options**

- Continue through host-side Zvalley SDK DDS direct connection: matches the
  original SDK bridge plan, but currently depends on unresolved multi-machine
  DDS discovery, interface binding, and robot-side ROS2/DDS configuration.
- Continue through an onboard ROS2 adapter: uses the state/control surface that
  is already live on the robot and lets the policy runner move forward without
  first changing robot networking.

**Decision**

Use the onboard ROS2 adapter as the next implementation path. Host-side SDK DDS
direct connection remains a separate investigation item, not the critical path
for first policy deployment.

**Consequences**

The next T4 backend should run in the robot's ROS2 environment, convert ROS2
messages into `RobotState`, and keep command publishing behind an explicit
publish gate. Documentation and tests should distinguish this ROS2 adapter path
from the earlier Zvalley SDK bridge path.
