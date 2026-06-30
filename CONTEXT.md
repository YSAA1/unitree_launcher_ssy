# Project Context Glossary

这个文件只记录理解 `unitree_launcher` 时反复出现的稳定术语。

## Terms

- **CLI**：命令行入口。用户在终端输入 `uv run real ...`、`uv run sim ...` 这类命令后，项目会通过 `pyproject.toml` 的脚本入口进入 `main.py`。
- **ArgumentParser**：`argparse` 的总命令行解析器，用来定义这个程序允许哪些参数和子命令。
- **Subparser**：`argparse` 的子命令分支。当前项目用它区分 `sim`、`eval`、`real`、`mirror` 和 `replay` mode。
- **args / Namespace**：终端字符串被 `argparse` 解析后的结构化对象，例如 `args.mode`、`args.policy`、`args.preset`、`args.interface`。它不是最终运行配置。
- **Config**：项目最终运行配置，由 YAML 默认值、preset/custom config 和 CLI overrides 合并得到，后续用于创建 robot、policy、safety、input 和 Runtime。
- **SDK**：机器人厂商提供的硬件通信层。当前 G1 链路的底层 SDK 是 Unitree SDK2，本项目通过 `unitree_cpp` 间接使用它。
- **Backend**：一个 `RobotInterface` 实现，用来把通用运行时接到某个具体执行目标，例如仿真或真机。
- **RobotInterface**：机器人后端边界。每个后端都必须实现 `connect`、`get_state`、`send_command`、`step`、`reset` 和 `n_dof`。
- **RobotState**：项目内部统一的机器人状态快照，供策略和安全检查使用。包含关节状态、IMU 状态、base 状态和可选 raw SDK 状态。
- **RobotCommand**：项目内部统一的机器人命令，供后端下发。包含目标关节位置、速度、前馈力矩和 PD 增益。
- **RealRobot**：当前 G1 真机后端。它导入 `unitree_cpp.UnitreeController`，读取 Unitree 状态，并发送 Unitree position-PD 命令。
- **unitree_cpp**：围绕 Unitree SDK2 的 Python 可导入 C++ binding，供 `RealRobot` 处理 DDS、CRC、motor mode 和命令发布。
- **UnitreeController**：`unitree_cpp` 暴露给 Python 的控制对象。`RealRobot.connect()` 创建它，后续通过它读取 robot state、设置 PD gain、发送目标关节位置。
- **SDK bridge**：把项目内部 `RobotState` / `RobotCommand` 契约转换到具体机器人 SDK 的适配层。当前 G1 的 SDK bridge 是 `RealRobot -> unitree_cpp`。
- **LowState / rt/lowstate**：Unitree 低层状态流，方向是 robot -> software。本项目通过它获得关节状态、IMU、无线手柄和 raw SDK 状态。
- **LowCmd / rt/lowcmd**：Unitree 低层命令流，方向是 software -> robot。本项目通过 `unitree_cpp` 把目标关节位置和 PD gain 发到这条链路。
- **T4**：Zvalley Robotics 的 29-DoF 人形机器人目标。本仓库当前已有 T4 MJCF/URDF 资产、T4 BeyondMimic ONNX 策略和对应 tracking motion 数据。
- **Zvalley SDK**：T4 的厂商 SDK。它提供 C++/Python API，并通过 DDS topic 暴露高层运动服务和低层关节状态/命令通道。
- **AllJointState / rt/all_joint_state**：Zvalley SDK 低层状态流，方向是 robot -> software，用来读取 T4 关节状态和控制相关状态。
- **AllJointCmd / rt/all_joint_cmd**：Zvalley SDK 低层命令流，方向是 software -> robot，用来发送 T4 关节目标、速度、力矩和 PD gain。
- **T4 SDK bridge**：待新增的 T4 后端适配层，把项目内部 `RobotState` / `RobotCommand` 转换到 Zvalley SDK 的 AllJointState / AllJointCmd 契约。
- **Runtime**：控制编排器。一次 `Runtime.step()` 会读取输入和状态，选择当前模式，运行 policy 或 prepare/damping 逻辑，执行 safety，再发送命令。
- **SystemState**：安全状态机的系统状态，包括 idle、running、stopped 和 estop。它决定 Runtime 是否可以进入 active policy。
- **ControlMode**：Runtime 当前控制模式，包括 hold、default、active、damping、prepare、transition 和 interpolate。它描述当前命令来源。
- **InputManager**：输入合并器。把 keyboard、gamepad、wireless、viser 等输入源合并成速度命令和离散命令。
- **Policy**：推理和控制律层。`Policy.step(state, velocity_command)` 返回一个完整 `RobotCommand`。
- **JointMapper**：机器人原生关节顺序和 policy 关节顺序之间的映射器。
- **SafetyController**：安全和状态层。维护 idle、running、stopped、estop 等系统状态，并在必要时 clamp 或替换命令。
- **Telemetry**：Runtime 输出的运行观测数据，例如 loop frequency、inference time、system state 和 step count，用于调试和可视化。
- **Prepare Phase**：真机启动前的准备阶段，把机器人平滑过渡到 policy/default pose，再进入主动策略执行。
- **DDS Topic**：Unitree 通信通道。当前 G1 后端通过 `unitree_cpp` 使用 `rt/lowstate` 读状态，使用 `rt/lowcmd` 发命令。
