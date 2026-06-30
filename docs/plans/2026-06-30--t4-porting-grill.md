# T4 Porting Grill

本文件记录把当前 G1 部署程序扩展到 T4 机器人时已经核实的事实、当前设计判断和待追问问题。它不是实现计划，只有在关键问题被问清楚后才会进入实现计划。

## Target

把 `unitree_launcher` 从“只支持 G1 的真机后端”扩展为“可新增 T4 真机后端”，目标是最终能用 T4 的 SDK 承载这个 ONNX tracking policy：

```text
assets/t4/policies/2026-06-10_12-11-59_t4_kick_modified_4096_7000_gpu0.onnx
```

## Evidence

本地事实：

- `assets/t4/motions/motion.npz` 包含 `fps=(1,)`，值为 `50.0`。
- `assets/t4/motions/motion.npz` 包含 `joint_pos=(765, 29)` 和 `joint_vel=(765, 29)`。
- `assets/t4/motions/motion.npz` 包含 `body_pos_w=(765, 30, 3)` 和 `body_quat_w=(765, 30, 4)`。
- `assets/robots/t4/xmls/t4_std.xml` 里有 29 个 actuated joint，顺序是 `J_arm_l_01` 到 `J_ankle_r_roll`。
- ONNX 输入是 `obs [1, 154]` 和 `time_step [1, 1]`。
- ONNX 输出包含 `actions [1, 29]`、`joint_pos [1, 29]`、`joint_vel [1, 29]`、`body_pos_w [1, 30, 3]`、`body_quat_w [1, 30, 4]`。
- ONNX metadata 里的 `joint_names` 与本地 T4 XML 的 29 个 joint 顺序一致。
- ONNX metadata 里包含 T4 policy 的 `joint_stiffness`、`joint_damping`、`default_joint_pos`、`observation_names`、`action_scale`、`anchor_body_name=Trunk` 和 30 个 `body_names`。
- 本项目现有 `RobotInterface` 要求后端实现 `connect`、`disconnect`、`get_state`、`send_command`、`step`、`reset` 和 `n_dof`。
- 当前 G1 后端 `RealRobot` 使用 `unitree_cpp.UnitreeController`，把 `RobotState` / `RobotCommand` 转换到 Unitree SDK2 DDS 通道。
- 当前配置校验只允许 `robot.variant` 为 `g1_29dof` 或 `g1_23dof`，所以 T4 不能只靠新增 YAML 直接通过。

外部 SDK 事实：

- Zvalley SDK README 说明该 SDK 基于 DDS，提供 C++ 和 Python API。
- Zvalley SDK 区分高层服务与底层服务：高层服务用于模式切换、整体运动等低频命令；底层服务用于电机、IMU 等高频数据和直接驱动控制。
- Zvalley SDK 示例里低层命令 topic 是 `rt/all_joint_cmd`，消息是 `AllJointCmd_`。
- Zvalley SDK 示例里低层状态 topic 是 `rt/all_joint_state`，消息是 `AllJointState_`。
- 本地 `zv_robot_sdk/examples_py/lowcmd/publisher.py` 当前只向 `rt/all_joint_cmd` 填了 23 个关节命令，这和本 T4 policy 的 29 个 action 不一致，必须核实真实 T4 低层控制通道是否接受 29 个 joint。
- 本地 `zv_robot_sdk/examples_py/imu_nav/subscriber.py` 订阅 `rt/nav_all`，说明 IMU/导航数据可能不在 `rt/all_joint_state` 里，需要探针输出后再决定 T4Robot 的 IMU 数据来源。

## Confidence Loop

- Target: 新增 T4 真机部署能力，同时复用现有 Runtime、Policy、Safety 和 JointMapper 契约。
- Evidence-backed assumptions: T4 policy 是 BeyondMimic 格式；policy joint order 与本地 T4 XML 一致；T4 SDK 有低层 DDS joint command/state topic。
- Inferred assumptions: T4 SDK 的 `AllJointCmd_` 可以安全接收 29 个 joint；T4 真实机器人 joint order 与本地 XML/ONNX metadata 一致；T4 SDK 的 Python binding 性能足够 50 Hz。
- Success criteria: 能在不触碰 G1 行为的前提下新增 T4 variant/backend/config；能在离线测试中加载 T4 ONNX 并生成 29-DoF `RobotCommand`；能用 mock SDK 验证 `RobotCommand <-> AllJointCmd_` 和 `AllJointState_ <-> RobotState` 映射；真机前有只读订阅和零力矩/阻尼 smoke test。
- Biggest loophole: 现在还没有确认 T4 SDK 的低层控制模式到底是否应该用于外部 RL policy 直控，还是应该只通过高层 `/change_cmd` 切换厂商内置模型。
- Fix: 第一轮 grilling 先锁定控制目标。如果目标是外部 ONNX 直控，后续才进入 T4 backend、joint order、state fields、safety、launch mode 的细化。
- Remaining risk: 真实 T4 机器人 SDK 文档可能和 GitHub 示例不完整，尤其是 23/29 DoF、控制权切换、E-stop、IMU 字段和命令频率。

## Current Design Tree

第一层必须先二选一：

```text
T4 接入目标
  A. 高层接入：调用 Zvalley SDK 的 mode/model 切换，让机器人执行厂商已有动作
  B. 低层接入：复用本项目 Runtime，运行你的 ONNX policy，向 T4 发送 29-DoF position-PD 命令
```

如果选 A，当前 ONNX 和 `motion.npz` 基本不会进入 Runtime，只是作为参考资料或后续训练资产。

如果选 B，才需要新增：

- T4 joint list / variant config
- T4 policy loading path
- T4 `RobotInterface` 后端
- Zvalley SDK bridge
- T4 safety limits
- T4 smoke-test runner

## Grill Question 1

当前必须确认：你这次“新加入 T4 模型”的目标，是不是 **低层接入 B**？

推荐答案：是，选择 B。理由是你给的是 29-DoF BeyondMimic ONNX 和 tracking 数据，不是厂商内置动作名；本项目的价值也在于复用 Runtime 跑外部 policy。  

但如果你的真实目标只是让 T4 执行 SDK 自带的 `kick` / `mimic` / `stand` 这类动作，那应该选 A，工程路线完全不同。

Decision: 选择 B，低层接入。目标是复用本项目 Runtime 加载 T4 ONNX policy，并通过 Zvalley SDK 发送 29-DoF position-PD 关节命令。

## Grill Question 2

下一步必须确认：真实 T4 SDK 低层通道到底接受 **29 个关节命令**，还是只接受公开示例里的 **23 个关节命令**？

推荐答案：按 29 个关节推进，但实现前必须用 SDK 文档、头文件或真机只读订阅验证。原因是你的 ONNX、`motion.npz`、T4 XML 三者都是 29-DoF；如果 SDK 只能控制 23 个关节，那这份 policy 不能直接部署，必须先做重新导出、裁剪控制关节或换 SDK 控制模式。

Decision: 暂时按 29-DoF 推进。若 Zvalley SDK 真实低层通道只支持 23-DoF，则把结果判定为“系统 SDK 连接链路可成立，但当前 29-DoF policy 不适配该 SDK 控制面”，后续需要重新训练、重新导出或更换 SDK 控制模式，而不是把 T4 后端接入本身判定为失败。

## Grill Question 3

新增 T4 后端时，SDK bridge 应该优先采用哪种形态？

选项：

```text
A. Python SDK bridge:
   T4Robot 直接 import zv_robot_sdk_python，订阅 rt/all_joint_state，发布 rt/all_joint_cmd。

B. C++ bridge + Python binding:
   像 G1 的 unitree_cpp 一样，用 C++ 处理 DDS/重发/实时性，再暴露 Python 控制对象。
```

推荐答案：先选 A，Python SDK bridge。理由是 Zvalley SDK 已经公开 Python API 示例，当前首要目标是证明连接、状态读取、joint order 和 policy 维度是否匹配；先做 Python bridge 可以更快建立诊断闭环。只有当 Python 50 Hz 发布不稳定、需要后台重发、或真机安全要求必须独立于 Python tick 时，再升级到 B。

Decision: 选择 A，先做 Python SDK bridge。T4 后端直接使用 `zv_robot_sdk_python` 订阅 `rt/all_joint_state`、发布 `rt/all_joint_cmd`，先建立连接和维度诊断闭环；只有在 Python tick 稳定性或安全重发无法满足需求时，才升级为 C++ bridge。

## Grill Question 4

项目内应该怎样表达 T4 机器人型号和关节列表？

选项：

```text
A. 复用现有 robot.variant 字段，新增 variant = "t4_29dof"，并让 _get_joints_for_variant() 返回 T4_29DOF_JOINTS。

B. 新增一个独立 robot.type/backend 字段，例如 robot.backend = "t4"，不把 T4 放进现有 variant 体系。
```

推荐答案：先选 A。理由是当前 `Config`、`load_policy()`、`JointMapper`、gain 长度校验和 `RealRobot(config)` 都围绕 `robot.variant -> joint list -> n_dof` 工作。新增 `t4_29dof` 是最小改动，能让 T4 policy metadata 的 29 个 joint 进入现有 JointMapper。后续如果机器人种类继续增加，再把 `variant` 和 `backend` 拆开。

Decision: 选择 A，新增 `robot.variant = "t4_29dof"`，并把 T4 的 29 个 joint 作为项目内稳定 joint list。现阶段不新增独立 `robot.backend` 字段。

## Grill Question 5

T4 真机启动入口应该怎么设计？

选项：

```text
A. 复用现有 real 命令:
   uv run real --config configs/t4_real.yaml --policy t4.onnx
   main.py 根据 config.robot.variant == "t4_29dof" 创建 T4Robot。

B. 新增独立命令:
   uv run t4-real --policy t4.onnx
   T4 有自己的 CLI 入口和默认 config。
```

推荐答案：先选 A。理由是项目当前 `real` 表示“连接真实机器人 backend”，不是专指 G1；T4 和 G1 都应该共享 Runtime、Safety、Input、Policy 装配链路。新增独立命令会让 main.py 的模式数量变多，但不能减少真实差异，真实差异应该落在 backend 选择和 config 上。

Decision: 选择 A，T4 复用现有 `real` 命令。典型入口形态是 `uv run real --config configs/t4_real.yaml --policy <t4_policy.onnx>`，`main.py` 根据 `config.robot.variant == "t4_29dof"` 创建 T4 后端。

## Grill Question 6

T4 真机后端如何填充 `RobotState` 里的 base 信息？

已知：

- `RobotState` 要求 `base_position`、`base_velocity`、`imu_quaternion`、`imu_angular_velocity`、`imu_linear_acceleration`。
- 当前 G1 `RealRobot` 在真机上把 `base_position` 和 `base_velocity` 填成 `NaN`，因为没有可靠世界系位置。
- 你的 T4 ONNX observation terms 是 `command,motion_anchor_ori_b,base_ang_vel,joint_pos,joint_vel,actions`。
- 这份 ONNX 不需要 `base_lin_vel`，但需要 `motion_anchor_ori_b` 和 `base_ang_vel`。
- `motion_anchor_ori_b` 主要依赖当前 IMU quaternion 和 ONNX reference body quaternion；不强依赖世界系 base position。

选项：

```text
A. 第一版 T4Robot 只要求 SDK 提供 IMU quaternion、angular velocity、linear acceleration 和 joint state；
   base_position/base_velocity 继续填 NaN，和 G1 真机保持一致。

B. 第一版就接入 T4 SDK/估计器的世界系 base pose/velocity。
```

推荐答案：选 A。理由是你的 ONNX observation 不含 `base_lin_vel`，当前 policy 能靠 IMU 姿态、角速度、关节状态、reference command 和 previous action 运行。先不引入世界系定位，能减少一个高风险不确定项。

Decision: 选择 A。第一版 T4Robot 只要求 Zvalley SDK 提供关节状态和 IMU 状态；`base_position` / `base_velocity` 继续填 `NaN`，与当前 G1 真机后端语义一致。

## Grill Question 7

T4 真机验证顺序应该如何分层？

选项：

```text
A. 分阶段安全门:
   1. 只读订阅 rt/all_joint_state，确认 SDK 连接、joint count、joint order、IMU 字段。
   2. 零力矩/阻尼命令 smoke test，确认 rt/all_joint_cmd 能被机器人接收且可安全停止。
   3. 静态 default pose / hold policy，确认 position-PD 符号、单位、关节顺序。
   4. 低幅度/短时 policy run，确认 ONNX 输出到 T4 命令链路。

B. 直接跑 T4 ONNX policy，再根据现象排查。
```

推荐答案：必须选 A。理由是 T4 是新 SDK、新关节顺序、新命令 topic；直接跑 policy 会把 SDK 连接、关节映射、PD gain、IMU 方向、policy 稳定性混在一起，失败时不可诊断，真机风险也不可接受。

Decision: 选择 A。T4 真机验证必须按只读订阅、阻尼/零力矩、静态 hold/default pose、低幅短时 policy run 的顺序推进；不允许第一步直接跑 ONNX policy。

## Grill Question 8

第一阶段实现切片应该是什么？

选项：

```text
A. 先写 T4 只读 SDK 探针:
   scripts/t4_probe_state.py
   只 import zv_robot_sdk_python，订阅 rt/all_joint_state，打印 joint count、每个 joint 的 index/model_id/motor_id/pos/vel/error、IMU 字段。
   不接 Runtime，不发布命令。

B. 直接把 T4Robot 接进 Runtime:
   改 config/main/robot/policy，然后用 real mode 验证。
```

推荐答案：选 A。理由是当前最大未知不是 Runtime，而是 Zvalley SDK 真实状态消息、joint count、joint order、IMU 字段和控制权状态。只读探针是最小、可逆、安全的第一刀；拿到输出后再写 T4Robot，会少猜很多。

Decision: 选择 A。第一阶段只写 T4 只读 SDK 探针，不接 Runtime，不发布任何 `AllJointCmd_`。探针输出必须能证明 SDK import、DDS 初始化、状态 topic、joint count、joint metadata 和 IMU 字段。

## Grill Question 9

第一阶段只读探针应该运行在哪里？

选项：

```text
A. 运行在 T4 官方/随机器人提供的控制机或机器人板载环境上：
   这个环境已经安装 zv_robot_sdk_python，能访问 T4 DDS 网络。

B. 运行在当前开发机上：
   需要先把 Zvalley SDK 的 Python libs、DDS 环境和网络接口都配置到当前机器。
```

推荐答案：选 A。理由是第一阶段目标是验证 SDK 与真机状态链路，不是先解决开发机依赖安装。官方/板载环境最可能已经具备 `zv_robot_sdk_python`、DDS runtime、topic 权限和正确网络配置；等只读探针证实消息结构后，再决定是否把 SDK libs 固化到本仓库的部署流程里。

Decision: 选择 A。只读探针第一优先运行在 T4 官方/板载控制环境中，用该环境已有的 `zv_robot_sdk_python` 和 DDS 网络验证 `rt/all_joint_state`。

## Current Converged Direction

已经收敛的方向：

1. T4 走低层接入，不走厂商高层动作/model 切换。
2. 先按 29-DoF policy 推进；如果 SDK 实测只支持 23-DoF，则判定为当前 policy 不适配，而不是连接链路失败。
3. 第一版 SDK bridge 使用 Python SDK，不先做 C++ binding。
4. 项目内新增 `robot.variant = "t4_29dof"` 和 T4 29-DoF joint list。
5. T4 复用 `uv run real --config configs/t4_real.yaml --policy <t4.onnx>` 入口。
6. 第一版 T4Robot 的 `base_position` / `base_velocity` 继续使用真机 NaN 语义，只依赖 joint state 和 IMU。
7. 真机验证必须分阶段推进：只读订阅 -> 阻尼/零力矩 -> 静态 pose -> 低幅 policy。
8. 第一阶段实现只写只读 SDK 探针，不接 Runtime，不发命令。
9. 只读探针优先在 T4 官方/板载控制环境运行。

## Next Implementable Slice

第一个实现切片：

```text
scripts/t4_probe_state.py
```

职责：

- 加载 `zv_robot_sdk_python`，优先使用运行环境已有 SDK，也允许从本仓库 `zv_robot_sdk/libs/python` 加载。
- 初始化 `ChannelFactory`。
- 订阅 `rt/all_joint_state`。
- 订阅 `rt/nav_all`，用于确认导航/IMU-like 字段。
- 打印 `timestamp`、`index`、`used_for_ctrl`。
- 打印 `len(joint_states_)`。
- 对每个 joint 打印 `model_id`、`motor_id`、`joint_pos`、`joint_vel`、`joint_torque`、`joint_error` 等可用字段。
- 尝试探测 IMU 字段，如果 SDK 消息里没有 IMU，则明确打印 `IMU fields not found`。
- 不发布任何 `AllJointCmd_`。

探针输出将决定第二阶段是否能写 `T4Robot.get_state()`。
