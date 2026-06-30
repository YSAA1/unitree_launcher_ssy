"""T4 robot backend boundary for Zvalley SDK integration.

This module intentionally does not publish commands yet.  It exists to make
``robot.variant: t4_29dof`` route to a T4-specific backend instead of the G1
``unitree_cpp`` backend while the Zvalley low-level command path is being
validated.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np

from unitree_launcher.config import Config, _get_joints_for_variant
from unitree_launcher.robot.base import RobotCommand, RobotInterface, RobotState

logger = logging.getLogger(__name__)

T4_JOINT_STATE_TOPIC = "rt/all_joint_state"
T4_NAV_TOPIC = "rt/nav_all"


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
            float(_read_field(obj, "x_", default[0])),
            float(_read_field(obj, "y_", default[1])),
            float(_read_field(obj, "z_", default[2])),
        ],
        dtype=np.float64,
    )


def _read_quat(obj: Any | None) -> np.ndarray:
    if obj is None:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    return np.array(
        [
            float(_read_field(obj, "q0_", 1.0)),
            float(_read_field(obj, "q1_", 0.0)),
            float(_read_field(obj, "q2_", 0.0)),
            float(_read_field(obj, "q3_", 0.0)),
        ],
        dtype=np.float64,
    )


class T4Robot(RobotInterface):
    """T4 backend placeholder using the project RobotInterface contract."""

    def __init__(self, config: Config):
        self._joints = _get_joints_for_variant(config.robot.variant)
        self._n_dof = len(self._joints)
        self._iface_name = config.network.interface
        self._domain_id = config.network.domain_id
        self._connected = False
        self._sdk = None
        self._joint_subscriber = None
        self._nav_subscriber = None
        self._last_joint_msg = None
        self._last_nav_msg = None
        self._command_index = 0

    def connect(self) -> None:
        """Connect read-only Zvalley SDK state subscribers."""
        if self._connected:
            return

        try:
            import zv_robot_sdk_python as zv
        except ImportError as exc:
            raise ImportError(
                "zv_robot_sdk_python is not available. Run T4 real mode in "
                "the Zvalley control environment or use scripts/t4_probe_state.py "
                "with --sdk-root to validate the SDK path first."
            ) from exc

        self._sdk = zv
        zv.ChannelFactory.Instance().Init(self._domain_id, self._iface_name)

        self._joint_subscriber = zv.ChannelSubscriber_AllJointState_(
            T4_JOINT_STATE_TOPIC
        )
        self._joint_subscriber.InitChannel(self._handle_joint_state)

        nav_subscriber_cls = getattr(zv, "ChannelSubscriber_NavAll_", None)
        if nav_subscriber_cls is not None:
            self._nav_subscriber = nav_subscriber_cls(T4_NAV_TOPIC)
            self._nav_subscriber.InitChannel(self._handle_nav)

        self._connected = True
        logger.info("T4Robot connected read-only on %s", self._iface_name)

    def _handle_joint_state(self, msg: Any) -> None:
        self._last_joint_msg = msg

    def _handle_nav(self, msg: Any) -> None:
        self._last_nav_msg = msg

    def disconnect(self) -> None:
        self._connected = False
        logger.info("T4Robot disconnected")

    def get_state(self) -> RobotState:
        msg = self._last_joint_msg
        if msg is None:
            return RobotState.zeros(self._n_dof)

        joint_states = list(_read_field(msg, "joint_states_", []) or [])
        joint_states = joint_states[:self._n_dof]
        missing = self._n_dof - len(joint_states)
        if missing > 0:
            joint_states.extend([None] * missing)

        nav = self._last_nav_msg
        return RobotState(
            timestamp=float(_read_field(msg, "timestamp_", time.time())),
            joint_positions=np.array(
                [
                    float(_read_field(joint, "joint_pos_", 0.0))
                    for joint in joint_states
                ],
                dtype=np.float64,
            ),
            joint_velocities=np.array(
                [
                    float(_read_field(joint, "joint_vel_", 0.0))
                    for joint in joint_states
                ],
                dtype=np.float64,
            ),
            joint_torques=np.array(
                [
                    float(_read_field(joint, "joint_torque_", 0.0))
                    for joint in joint_states
                ],
                dtype=np.float64,
            ),
            imu_quaternion=_read_quat(_read_field(nav, "quat_", None)),
            imu_angular_velocity=_read_vector3(
                _read_field(nav, "gyro_", None), (0.0, 0.0, 0.0)
            ),
            imu_linear_acceleration=_read_vector3(
                _read_field(nav, "acc_", None), (0.0, 0.0, 0.0)
            ),
            base_position=np.full(3, np.nan),
            base_velocity=np.full(3, np.nan),
        )

    def build_command_message(self, cmd: RobotCommand) -> Any:
        """Convert a RobotCommand into a Zvalley AllJointCmd_ message.

        This only builds the SDK message object.  It intentionally does not
        create a publisher or write to ``rt/all_joint_cmd``.
        """
        sdk = self._sdk
        if sdk is None:
            try:
                import zv_robot_sdk_python as sdk
            except ImportError as exc:
                raise ImportError(
                    "zv_robot_sdk_python is required to build a T4 command message."
                ) from exc

        self._validate_command_shape(cmd)
        msg = sdk.AllJointCmd_()
        msg.timestamp_ = int(time.time() * 1_000_000)
        msg.index_ = self._command_index
        msg.cmd_type_ = 0
        self._command_index += 1

        joint_cmds = msg.joint_cmds_
        joint_cmds.clear()
        for i in range(self._n_dof):
            joint_cmd = sdk.JointCmd_()
            joint_cmd.joint_pos_ = float(cmd.joint_positions[i])
            joint_cmd.joint_vel_ = float(cmd.joint_velocities[i])
            joint_cmd.joint_torque_ = float(cmd.joint_torques[i])
            joint_cmd.kp_ = float(cmd.kp[i])
            joint_cmd.kd_ = float(cmd.kd[i])
            joint_cmds.append(joint_cmd)
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
                    f"T4 command {name} has length {len(value)}, "
                    f"expected {self._n_dof}"
                )

    def send_command(self, cmd: RobotCommand) -> None:
        raise NotImplementedError(
            "T4 command publishing is not implemented yet."
        )

    def step(self) -> None:
        """Hardware loop is external; no simulation step is performed."""
        return None

    def reset(self, initial_state: RobotState | None = None) -> None:
        logger.warning("T4Robot.reset() is not available on physical hardware")

    @property
    def n_dof(self) -> int:
        return self._n_dof
