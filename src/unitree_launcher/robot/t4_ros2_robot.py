"""T4 onboard ROS2 backend for read-only policy smoke dry-runs."""
from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np

from unitree_launcher.config import Config, _get_joints_for_variant
from unitree_launcher.robot.base import RobotCommand, RobotInterface, RobotState

logger = logging.getLogger(__name__)

T4_ROS2_JOINT_STATE_TOPIC = "/all_joint_state"
T4_ROS2_NAV_TOPIC = "/nav_all"
T4_ROS2_ROBOT_STATE_TOPIC = "/robot_state"
T4_ROS2_STATE_TIMEOUT_S = 5.0
T4_ROS2_SPIN_TIMEOUT_S = 0.05


def _read_field(obj: Any, name: str, default: Any = None) -> Any:
    value = getattr(obj, name, default)
    if callable(value):
        try:
            return value()
        except TypeError:
            return value
    return value


def _read_vector3(obj: Any | None, default: tuple[float, float, float]) -> np.ndarray:
    if obj is None:
        return np.array(default, dtype=np.float64)
    return np.array(
        [
            float(_read_field(obj, "x", default[0])),
            float(_read_field(obj, "y", default[1])),
            float(_read_field(obj, "z", default[2])),
        ],
        dtype=np.float64,
    )


def _read_quat(obj: Any | None) -> np.ndarray:
    if obj is None:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    return np.array(
        [
            float(_read_field(obj, "q0", 1.0)),
            float(_read_field(obj, "q1", 0.0)),
            float(_read_field(obj, "q2", 0.0)),
            float(_read_field(obj, "q3", 0.0)),
        ],
        dtype=np.float64,
    )


class T4Ros2Robot(RobotInterface):
    """T4 backend that reads the onboard ROS2 control stack.

    The backend is intentionally publish-disabled for the policy smoke slice.
    It can build ROS2 command messages, but does not create a command publisher.
    """

    def __init__(self, config: Config):
        self._joints = _get_joints_for_variant(config.robot.variant)
        self._n_dof = len(self._joints)
        self._connected = False
        self._rclpy = None
        self._node = None
        self._msg_types: dict[str, Any] = {}
        self._joint_subscription = None
        self._nav_subscription = None
        self._robot_state_subscription = None
        self._last_joint_msg = None
        self._last_nav_msg = None
        self._last_robot_state_msg = None
        self._command_index = 0
        self._state_timeout_s = T4_ROS2_STATE_TIMEOUT_S

    def connect(self) -> None:
        """Connect read-only ROS2 state subscriptions."""
        if self._connected:
            return

        try:
            import rclpy
            from robot_msgs.msg import AllJointCmd, AllJointState, JointCmd, RobotState as RobotStateMsg
            from yesense_interface.msg import NavAll
        except ImportError as exc:
            raise ImportError(
                "T4 ROS2 backend requires rclpy, robot_msgs, and "
                "yesense_interface. Source the T4 onboard ROS2 workspace first."
            ) from exc

        self._rclpy = rclpy
        self._msg_types = {
            "all_joint_state": AllJointState,
            "all_joint_cmd": AllJointCmd,
            "joint_cmd": JointCmd,
            "nav_all": NavAll,
            "robot_state": RobotStateMsg,
        }

        rclpy.init(args=None)
        self._node = rclpy.create_node("unitree_launcher_t4_ros2_robot")
        self._joint_subscription = self._node.create_subscription(
            AllJointState,
            T4_ROS2_JOINT_STATE_TOPIC,
            self._handle_joint_state,
            10,
        )
        self._nav_subscription = self._node.create_subscription(
            NavAll,
            T4_ROS2_NAV_TOPIC,
            self._handle_nav,
            10,
        )
        self._robot_state_subscription = self._node.create_subscription(
            RobotStateMsg,
            T4_ROS2_ROBOT_STATE_TOPIC,
            self._handle_robot_state,
            10,
        )
        self._connected = True
        logger.info("T4Ros2Robot connected read-only")

    def _handle_joint_state(self, msg: Any) -> None:
        self._last_joint_msg = msg

    def _handle_nav(self, msg: Any) -> None:
        self._last_nav_msg = msg

    def _handle_robot_state(self, msg: Any) -> None:
        self._last_robot_state_msg = msg

    @property
    def last_robot_state(self) -> Any | None:
        return self._last_robot_state_msg

    def disconnect(self) -> None:
        if self._node is not None:
            self._node.destroy_node()
            self._node = None
        if self._rclpy is not None:
            self._rclpy.shutdown()
        self._connected = False
        logger.info("T4Ros2Robot disconnected")

    def get_state(self) -> RobotState:
        self._wait_for_joint_state()
        msg = self._last_joint_msg
        if msg is None:
            raise TimeoutError(
                f"No T4 ROS2 joint state received from {T4_ROS2_JOINT_STATE_TOPIC} "
                f"within {self._state_timeout_s:.1f}s"
            )

        joint_states = list(_read_field(msg, "joint_states", []) or [])
        joint_states = joint_states[:self._n_dof]
        missing = self._n_dof - len(joint_states)
        if missing > 0:
            joint_states.extend([None] * missing)

        nav = self._last_nav_msg
        return RobotState(
            timestamp=float(_read_field(msg, "timestamp", time.time())),
            joint_positions=np.array(
                [
                    float(_read_field(joint, "joint_pos", 0.0))
                    for joint in joint_states
                ],
                dtype=np.float64,
            ),
            joint_velocities=np.array(
                [
                    float(_read_field(joint, "joint_vel", 0.0))
                    for joint in joint_states
                ],
                dtype=np.float64,
            ),
            joint_torques=np.array(
                [
                    float(_read_field(joint, "joint_torque", 0.0))
                    for joint in joint_states
                ],
                dtype=np.float64,
            ),
            imu_quaternion=_read_quat(_read_field(nav, "quat", None)),
            imu_angular_velocity=_read_vector3(
                _read_field(nav, "gyro", None), (0.0, 0.0, 0.0)
            ),
            imu_linear_acceleration=_read_vector3(
                _read_field(nav, "acc", None), (0.0, 0.0, 0.0)
            ),
            base_position=np.full(3, np.nan),
            base_velocity=np.full(3, np.nan),
        )

    def _wait_for_joint_state(self) -> None:
        if self._last_joint_msg is not None:
            return
        if self._rclpy is None or self._node is None:
            return

        deadline = time.monotonic() + self._state_timeout_s
        while self._last_joint_msg is None and time.monotonic() < deadline:
            spin_once = getattr(self._rclpy, "spin_once", None)
            if spin_once is None:
                break
            spin_once(self._node, timeout_sec=T4_ROS2_SPIN_TIMEOUT_S)

    def build_command_message(self, cmd: RobotCommand) -> Any:
        """Build a ROS2 AllJointCmd message without publishing it."""
        if not self._msg_types:
            try:
                from robot_msgs.msg import AllJointCmd, JointCmd
            except ImportError as exc:
                raise ImportError(
                    "robot_msgs is required to build a T4 ROS2 command message."
                ) from exc
            self._msg_types = {
                "all_joint_cmd": AllJointCmd,
                "joint_cmd": JointCmd,
            }

        self._validate_command_shape(cmd)
        msg = self._msg_types["all_joint_cmd"]()
        msg.timestamp = int(time.time() * 1_000_000)
        msg.index = self._command_index
        msg.cmd_type = 0
        self._command_index += 1

        msg.joint_cmds.clear()
        for i in range(self._n_dof):
            joint_cmd = self._msg_types["joint_cmd"]()
            joint_cmd.joint_pos = float(cmd.joint_positions[i])
            joint_cmd.joint_vel = float(cmd.joint_velocities[i])
            joint_cmd.joint_torque = float(cmd.joint_torques[i])
            joint_cmd.kp = float(cmd.kp[i])
            joint_cmd.kd = float(cmd.kd[i])
            msg.joint_cmds.append(joint_cmd)
        return msg

    def _validate_command_shape(self, cmd: RobotCommand) -> None:
        for name, value in (
            ("joint_positions", cmd.joint_positions),
            ("joint_velocities", cmd.joint_velocities),
            ("joint_torques", cmd.joint_torques),
            ("kp", cmd.kp),
            ("kd", cmd.kd),
        ):
            if len(value) != self._n_dof:
                raise ValueError(
                    f"T4 ROS2 command {name} has length {len(value)}, "
                    f"expected {self._n_dof}"
                )

    def send_command(self, cmd: RobotCommand) -> None:
        raise NotImplementedError(
            "T4 ROS2 command publishing is not implemented yet."
        )

    def step(self) -> None:
        return None

    def reset(self, initial_state: RobotState | None = None) -> None:
        logger.warning("T4Ros2Robot.reset() is not available on physical hardware")

    @property
    def n_dof(self) -> int:
        return self._n_dof
