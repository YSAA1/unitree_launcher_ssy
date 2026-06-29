## 一句话结论

这个项目的心智模型是：

> **它不是训练框架，而是一个 Unitree G1 的“策略部署运行时”：把 IsaacLab / BeyondMimic 导出的 ONNX 策略，安全地跑在 MuJoCo 仿真或 G1 真机上。** 🤖

也就是说，它解决的是：

```text
训练好的 policy.onnx
        ↓
统一策略接口 Policy
        ↓
Runtime 控制循环
        ↓
Safety 安全裁剪 / 急停
        ↓
SimRobot / RealRobot
        ↓
MuJoCo 仿真 或 Unitree G1 真机
```

仓库 README 也明确说它是 **Unitree G1 humanoid robot 的 control stack**，支持 MuJoCo simulation 和 onboard real robot deployment，并以 50 Hz 运行 ONNX 神经网络策略，同时有 safety enforcement。([GitHub][1])

---

# 1. 先建立大图：这个项目分 5 层

你可以把它看成一个 **部署系统五层架构**：

| 层                            | 作用         | 你要理解什么                                               |
| ---------------------------- | ---------- | ---------------------------------------------------- |
| **CLI / Mode 层**             | 选择运行方式     | `sim / eval / real / mirror / replay`                |
| **Runtime 层**                | 控制主循环      | 每 tick：读状态 → 策略推理 → 生成命令 → 安全检查 → 发命令                |
| **Policy 层**                 | 包装 ONNX 策略 | IsaacLab velocity policy / BeyondMimic motion policy |
| **Robot Backend 层**          | 屏蔽仿真和真机差异  | `SimRobot` 和 `RealRobot` 统一成同一个接口                    |
| **Safety / Logging / Viz 层** | 工程化部署保障    | 急停、限幅、记录、可视化、回放、状态估计                                 |

项目支持 5 种模式：`sim` 做 MuJoCo 仿真，`eval` 做高精度 headless 评估，`real` 做 G1 真机部署，`mirror` 只读可视化真机 DDS 状态，`replay` 回放日志。([GitHub][1])

---

# 2. 最核心的心智模型：Runtime 是“心脏”

这个项目最关键的文件不是 policy，也不是 robot，而是：

```text
src/unitree_launcher/control/runtime.py
```

它的设计思想是：

```text
Runtime.step() = 一个原子控制 tick

1. 读取输入：键盘 / 手柄 / 网页 UI / 真机无线手柄
2. 读取机器人状态：joint pos / vel / torque / IMU / base state
3. 选择当前控制模式：IDLE / RUNNING / ESTOP / PREPARE / TRANSITION
4. 调用 policy.step()
5. 得到 RobotCommand
6. safety.clamp_command()
7. robot.send_command()
8. robot.step()
```

源码注释明确说：`Runtime.step()` 是一个 atomic control unit，一次 tick 完成 state read、policy inference、command building、command send，而且不负责 sleep，调用者管理 timing。([GitHub][2])

**你学习这个项目，第一优先级就是吃透 Runtime。**

---

# 3. 第二个核心抽象：RobotInterface 屏蔽仿真和真机差异

它把仿真和真机统一成同一套接口：

```python
robot.connect()
state = robot.get_state()
robot.send_command(cmd)
robot.step()
robot.disconnect()
```

`RobotInterface` 有三个实现：

| 后端            | 文件                      | 作用               |
| ------------- | ----------------------- | ---------------- |
| `SimRobot`    | `robot/sim_robot.py`    | MuJoCo 仿真        |
| `RealRobot`   | `robot/real_robot.py`   | G1 真机 C++ DDS 后端 |
| `MirrorRobot` | `robot/mirror_robot.py` | 只读镜像真机状态         |

源码说明里明确写了这三种实现，并且比较了 `connect/get_state/send_command/step/reset` 在 sim 和 real 中的差异。([GitHub][3])

这里的工程味很强：
**Policy 和 Runtime 不应该知道自己面对的是 MuJoCo 还是 G1 真机。**

它们只知道：

```text
我拿到 RobotState
我输出 RobotCommand
```

这就是这个项目最重要的解耦。

---

# 4. 第三个核心抽象：Policy 只负责“观测 → ONNX → 命令”

Policy 基类的思想也很清晰：

```text
Policy.step(state, velocity_command) -> RobotCommand
```

也就是说，策略类不只是跑 ONNX，它还负责：

| 职责               | 说明                 |
| ---------------- | ------------------ |
| 构造 observation   | 把机器人状态变成网络输入       |
| ONNX 推理          | `onnxruntime` 执行策略 |
| action smoothing | 动作平滑 / 裁剪 / 缩放     |
| control law      | 把 action 转成目标关节位置  |
| gain 管理          | 生成每个关节的 Kp / Kd    |

Policy 基类源码明确说：Runtime 只调用 `step(state, velocity_command)`、`reset()`、`load(path)`，而 observation、control law、action scaling、gains 都由具体 policy 子类拥有。([GitHub][4])

当前主要支持两类策略：

| 策略                  | 用途              | 文件                      |
| ------------------- | --------------- | ----------------------- |
| `IsaacLabPolicy`    | 速度跟踪 locomotion | `isaaclab_policy.py`    |
| `BeyondMimicPolicy` | 动作轨迹 tracking   | `beyondmimic_policy.py` |

README 也写了支持 IsaacLab velocity-tracking locomotion 和 BeyondMimic motion-tracking。([GitHub][1])

---

# 5. IsaacLabPolicy 怎么理解？

一句话：

> **IsaacLabPolicy 是“给速度指令，让 G1 走路”的策略包装器。**

它的 observation 大概是：

```text
base_lin_vel 可选
base_ang_vel
projected_gravity
velocity_commands
joint_pos_rel
joint_vel
last_actions
```

控制律是：

```text
target_pos = q_home + action_scale * action
```

源码注释明确给出了 observation format 和 control law：`target_pos = q_home + Ka * action`。([GitHub][5])

所以你可以把它理解成：

```text
键盘/手柄给 vx, vy, yaw
        ↓
拼进 observation
        ↓
ONNX 输出 action
        ↓
转成每个关节的 target position
        ↓
PD 控制
```

---

# 6. BeyondMimicPolicy 怎么理解？

一句话：

> **BeyondMimicPolicy 是“跟踪某段动作轨迹”的策略包装器。**

它跟 IsaacLab 最大区别是：
它的 ONNX 不只有 `obs` 输入，还有 `time_step` 输入。

所以它不是单纯根据当前状态输出动作，而是：

```text
当前机器人状态 + 第 t 帧参考动作
        ↓
ONNX
        ↓
输出 action + reference joint pos/vel + body pose
        ↓
机器人跟踪这段动作
```

源码说明里明确说 BeyondMimic ONNX 带有 `time_step` 输入，用来索引 reference trajectory，并输出 reference `joint_pos/joint_vel/body poses`，这些又进入 observation。([GitHub][6])

这对你很重要，因为你之前关心 mjlab / BeyondMimic / 特技动作部署。这个项目的 BeyondMimicPolicy 基本就是你要重点看的部分。

---

# 7. Safety 是真机部署的底线，不是附属功能

这个项目不是“随便跑个 policy”，它很重视安全。

SafetyController 有几个核心机制：

| 安全机制                 | 作用                                     |
| -------------------- | -------------------------------------- |
| `SystemState`        | `IDLE / RUNNING / STOPPED / ESTOP` 状态机 |
| damping command      | 急停后进入阻尼模式                              |
| tilt check           | 倾斜过大触发 E-stop                          |
| frame drop check     | 控制循环卡顿触发 E-stop                        |
| joint position limit | 关节位置限幅                                 |
| joint velocity limit | 速度限幅                                   |
| torque-aware clamp   | 根据 Kp 和 torque limit 限制目标位置            |

README 也列出了 joint limits、tilt detection、frame drop、wireless E-stop、hardware fallback、exception handling、E-stop latching 等安全机制。([GitHub][1])

源码里 `SafetyController` 明确有 `IDLE/RUNNING/STOPPED/ESTOP` 状态机，并且 `clamp_command()` 会限制 position、velocity、torque，还会根据 `Kp * (q_target - q_actual)` 避免隐含 PD torque 超限。([GitHub][7])

**你要有一个判断：这个项目的价值不只是“跑通”，而是“尽量别把真机跑炸”。**

---

# 8. SimRobot 和 RealRobot 的关键区别

## SimRobot

SimRobot 是纯 MuJoCo 后端，不走 DDS，不走 Unitree SDK。它读取 MuJoCo 里的 `qpos/qvel/sensordata`，把 `RobotCommand` 写到 MuJoCo position actuators，再进行多个 physics substeps。([GitHub][8])

它的逻辑是：

```text
send_command(cmd)
        ↓
保存 pending command

step()
        ↓
把 target joint position 写入 data.ctrl
设置 kp / kd
mj_step 多次
```

## RealRobot

RealRobot 走 C++ `unitree_cpp` binding。源码注释说它包装了 `unitree_cpp.UnitreeController`，由 C++ 层处理 DDS 通信、CRC、motor mode、后台 command republishing。([GitHub][9])

关键区别：

| 项目         | SimRobot         | RealRobot         |
| ---------- | ---------------- | ----------------- |
| `step()`   | 推进 MuJoCo 物理     | 基本 no-op          |
| 控制执行       | MuJoCo actuator  | G1 电机控制板          |
| 状态来源       | qpos/qvel/sensor | DDS LowState      |
| base state | 仿真可直接拿           | 需要 estimator      |
| 风险         | 仿真崩              | 真机摔 / 电机保护 / 人身安全 |

---

# 9. State Estimator 是 sim2real 的关键补丁

真机没有 MuJoCo 那种完美 base position / base velocity，所以项目加入了 InEKF 状态估计器。

README 说：InEKF state estimator 融合 IMU prediction 和 contact-foot kinematics；real mode 总是开启，sim mode 可以用 `--estimator` 提前验证 estimator-in-the-loop。([GitHub][1])

心智模型：

```text
真机只有：
IMU + 关节编码器 + 接触判断

但 policy 可能需要：
base_velocity / base_position

所以需要：
IMU prediction + foot contact FK
        ↓
估计 base state
        ↓
填回 RobotState
        ↓
给 policy 构造 observation
```

你以后做真机部署时，这块很关键。很多 sim 成功、real 失败，问题不一定在 policy，也可能在 **状态估计误差 / 观测分布偏移**。

---

# 10. 这个项目的运行模式怎么选？

| 你要做什么                    | 用什么模式                                       |
| ------------------------ | ------------------------------------------- |
| 看 policy 能不能在 MuJoCo 跑起来 | `uv run sim --gui --policy xxx.onnx`        |
| 浏览器远程看仿真                 | `uv run sim --viser --policy xxx.onnx`      |
| 大量测试稳定性                  | `uv run eval --steps 500 --policy xxx.onnx` |
| 真机部署                     | `uv run real --policy xxx.onnx`             |
| 只看真机状态，不发控制              | `uv run mirror --viser`                     |
| 分析失败日志                   | `uv run replay logs/run_name/ --gui`        |
| sim2real 单关节测试           | `uv run sim/real --gantry`                  |

README 给出的 quick start 包括 `uv sync`、MuJoCo GUI、Viser、headless eval、replay、pytest 等命令。([GitHub][1])

---

# 11. 你真正该按什么顺序学？

## 第一阶段：先会用，不急着读源码

目标：确认项目能跑起来。

```bash
git clone https://github.com/KyleM73/unitree_launcher.git
cd unitree_launcher
uv sync
uv run pytest tests/ -x
```

然后跑仿真：

```bash
uv run sim --viser --policy assets/policies/stance_29dof.onnx
```

注意：README 里说 policy files gitignored，不会 baked into Docker image；也就是说你本地可能需要自己准备 ONNX policy。([GitHub][1])

---

## 第二阶段：读 4 个核心文件

按这个顺序读，不要乱：

```text
1. robot/base.py
2. policy/base.py
3. control/safety.py
4. control/runtime.py
```

为什么？

| 文件               | 你要抓住的问题                         |
| ---------------- | ------------------------------- |
| `robot/base.py`  | RobotState / RobotCommand 长什么样？ |
| `policy/base.py` | Policy 输入输出协议是什么？               |
| `safety.py`      | 命令怎么被安全限制？                      |
| `runtime.py`     | 一个控制 tick 到底发生了什么？              |

这 4 个读懂，你就已经掌握 60%。

---

## 第三阶段：再读具体 policy

你应该重点读：

```text
policy/isaaclab_policy.py
policy/beyondmimic_policy.py
policy/joint_mapper.py
```

重点不是看 Python 语法，而是搞清楚：

```text
ONNX 输入是什么？
ONNX 输出是什么？
action 怎么变成 target joint position？
policy joint order 怎么映射到 G1 native joint order？
Kp/Kd 从哪里来？
default pose 从哪里来？
```

尤其 `joint_mapper.py` 很重要。
真机部署最容易出事的地方之一就是：

```text
训练时 joint order ≠ 真机 joint order
```

只要顺序错，轻则动作怪，重则直接摔。

---

## 第四阶段：读后端

然后再读：

```text
robot/sim_robot.py
robot/real_robot.py
```

你要对比：

```text
同一个 RobotCommand
在 MuJoCo 里怎么执行？
在真机上怎么发送？
```

这一步能帮你建立 sim2real 的工程直觉。

---

## 第五阶段：读 estimator 和 logging

最后读：

```text
estimation/state_estimator.py
estimation/inekf.py
estimation/contact.py
datalog/logger.py
datalog/replay.py
```

因为这不是最先影响你“跑起来”的东西，但它会影响你“为什么真机失败”。

---

# 12. 这个项目对你当前 G1 / mjlab 路线的价值

结合你现在做 G1、mjlab、BeyondMimic、特技动作部署，我会这么判断：

## 它最有价值的地方

| 价值                 | 原因                       |
| ------------------ | ------------------------ |
| **ONNX 部署框架**      | 你可以把训练好的 policy 接进去      |
| **sim/real 统一接口**  | 同一套 Runtime 跑 MuJoCo 和真机 |
| **安全机制完整**         | 对真机更重要                   |
| **BeyondMimic 支持** | 和你当前动作跟踪方向相关             |
| **replay/logging** | 方便定位 sim2real 失败         |
| **gantry test**    | 单关节 sim2real 对比很实用       |

README 还专门提供了 `--gantry` 测试，用右肩 pitch 正弦测试做 sim2real 对比，同一个测试可在 sim 和 real 上运行，并可比较日志。([GitHub][1])

---

# 13. 但它不是万能的，别误判

你要保持怀疑：

## 它不是训练框架

它不会帮你训练：

```text
PPO
AMP
BeyondMimic
FPO++
recovery policy
diffusion motion prior
```

它主要解决：

```text
我已经有 policy.onnx，怎么安全部署到 G1？
```

## 它不是通用 humanoid 框架

它明显围绕 Unitree G1 写，README 也说机器人资产在 `assets/robots/g1/`，配置支持 G1 29DOF / 23DOF。([GitHub][1])

所以如果你拿非 G1 模型来套，需要改：

```text
joint constants
joint mapper
MuJoCo XML
actuator limits
torque limits
home pose
policy observation
real backend
```

## 真机部署仍然很危险

RealRobot 源码提醒：软件 E-stop 只有 Python 控制循环还在跑时才有效；如果 Python hang 住，C++ 层会继续 republish last command，硬件级 fallback 是无线手柄 L2+B。([GitHub][9])

这句话非常关键。
意思是：**软件安全不是绝对安全。真机必须准备硬件阻尼/吊绳/旁路急停。**

---

# 14. 你可以这样记住整个项目

最短心智模型：

```text
unitree_launcher =
    ONNX Policy Runner
  + G1 Robot Abstraction
  + MuJoCo/Real Dual Backend
  + Safety State Machine
  + Logging/Replay/Viz
```

更具体一点：

```text
main.py
  解析命令：sim/eval/real/mirror/replay
        ↓
load_config()
        ↓
创建 RobotBackend：SimRobot or RealRobot
        ↓
load_policy()：IsaacLab or BeyondMimic
        ↓
创建 SafetyController
        ↓
创建 Runtime
        ↓
while running:
    state = robot.get_state()
    cmd = policy.step(state, user_cmd)
    cmd = safety.clamp_command(cmd)
    robot.send_command(cmd)
    robot.step()
```

---

# 15. 我建议你的学习路线

## 你现在最该先掌握 3 个点

1. **RobotState / RobotCommand 是什么**
   这是所有模块交流的语言。

2. **Runtime.step() 一帧干了什么**
   这是整个系统的主循环。

3. **Policy 怎么把 ONNX 输出变成关节目标**
   这是你接入 mjlab / BeyondMimic policy 的关键。

---

## 给你一个最小阅读任务

你下一步可以只读这 4 个文件：

```text
src/unitree_launcher/robot/base.py
src/unitree_launcher/policy/base.py
src/unitree_launcher/control/safety.py
src/unitree_launcher/control/runtime.py
```

读的时候只回答 4 个问题：

```text
1. RobotState 里有哪些字段？
2. RobotCommand 里有哪些字段？
3. Policy.step() 输入输出是什么？
4. Runtime.step() 的执行顺序是什么？
```

这 4 个问题回答出来，你就已经真正入门这个项目了。
不要一上来就钻 DDS、InEKF、Docker，那样会乱。

[1]: https://github.com/KyleM73/unitree_launcher "GitHub - KyleM73/unitree_launcher · GitHub"
[2]: https://github.com/KyleM73/unitree_launcher/raw/refs/heads/main/src/unitree_launcher/control/runtime.py "raw.githubusercontent.com"
[3]: https://github.com/KyleM73/unitree_launcher/raw/refs/heads/main/src/unitree_launcher/robot/base.py "raw.githubusercontent.com"
[4]: https://github.com/KyleM73/unitree_launcher/raw/refs/heads/main/src/unitree_launcher/policy/base.py "raw.githubusercontent.com"
[5]: https://github.com/KyleM73/unitree_launcher/raw/refs/heads/main/src/unitree_launcher/policy/isaaclab_policy.py "raw.githubusercontent.com"
[6]: https://github.com/KyleM73/unitree_launcher/raw/refs/heads/main/src/unitree_launcher/policy/beyondmimic_policy.py "raw.githubusercontent.com"
[7]: https://github.com/KyleM73/unitree_launcher/raw/refs/heads/main/src/unitree_launcher/control/safety.py "raw.githubusercontent.com"
[8]: https://github.com/KyleM73/unitree_launcher/raw/refs/heads/main/src/unitree_launcher/robot/sim_robot.py "raw.githubusercontent.com"
[9]: https://github.com/KyleM73/unitree_launcher/raw/refs/heads/main/src/unitree_launcher/robot/real_robot.py "raw.githubusercontent.com"
