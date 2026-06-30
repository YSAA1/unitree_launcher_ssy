# Understanding Guides

这组文档按数据流分节讲解 `unitree_launcher`，目标是建立能迁移到其他机器人 SDK 的心智模型。

## Recommended Route

1. [Lesson 01: CLI 到 Runtime 装配](lesson-01-cli-to-runtime-assembly.md)
   从 `uv run real --policy ...` 追到 `Runtime(robot, policy, safety, input)`。
2. [Lesson 02: RealRobot.connect 到 SDK / DDS](lesson-02-realrobot-connect-to-sdk-dds.md)
   从 `robot.connect()` 追到 `unitree_cpp.UnitreeController`、`rt/lowstate` 和 `rt/lowcmd`。
3. [Lesson 03: Runtime.step 一帧控制循环](lesson-03-runtime-step-control-tick.md)
   从 `RobotState` 和输入命令追到 `Policy.step`、`SafetyController` 和 `robot.send_command`。
4. [Robot SDK Porting Workflow](robot-sdk-porting-workflow.md)
   总览 G1 当前 SDK 路径，以及换成其他机器人 SDK 时要替换哪些层。

## Reading Rule

每节只追一条链：

```text
input -> transformation -> artifact -> output -> downstream consumer
```

不要先按文件树阅读。这个项目更适合按数据流读。
