"""Tests for the T4 onboard ROS2 robot backend."""
from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from unitree_launcher.config import load_config
from unitree_launcher.robot.base import RobotCommand
from unitree_launcher.robot.t4_ros2_robot import T4Ros2Robot


def _make_t4_ros2_config():
    config = load_config("configs/real.yaml")
    config.robot.variant = "t4_29dof"
    config.robot.backend = "t4_ros2"
    return config


class FakeNode:
    def __init__(self):
        self.subscriptions = {}
        self.publisher_created = False
        self.destroyed = False

    def create_subscription(self, msg_type, topic, callback, qos):
        self.subscriptions[topic] = {
            "msg_type": msg_type,
            "callback": callback,
            "qos": qos,
        }
        return SimpleNamespace(topic=topic)

    def create_publisher(self, *args, **kwargs):
        self.publisher_created = True
        return SimpleNamespace()

    def destroy_node(self):
        self.destroyed = True


class FakeRclpy(ModuleType):
    def __init__(self):
        super().__init__("rclpy")
        self.node = FakeNode()
        self.init_called = False
        self.shutdown_called = False
        self.spin_once_calls = 0
        self.spin_once_hook = None

    def init(self, args=None):
        self.init_called = True

    def create_node(self, name):
        self.node_name = name
        return self.node

    def spin_once(self, node, timeout_sec=0.0):
        self.spin_once_calls += 1
        if self.spin_once_hook is not None:
            self.spin_once_hook(node, timeout_sec)

    def shutdown(self):
        self.shutdown_called = True


class FakeJointCmd:
    def __init__(self):
        self.joint_pos = 0.0
        self.joint_vel = 0.0
        self.joint_torque = 0.0
        self.kp = 0.0
        self.kd = 0.0


class FakeAllJointCmd:
    def __init__(self):
        self.timestamp = 0
        self.index = 0
        self.cmd_type = -1
        self.joint_cmds = []


class FakeAllJointState:
    pass


class FakeRobotStateMsg:
    pass


class FakeNavAll:
    pass


def _install_fake_ros_modules(monkeypatch):
    rclpy = FakeRclpy()

    robot_msgs = ModuleType("robot_msgs")
    robot_msgs_msg = ModuleType("robot_msgs.msg")
    robot_msgs_msg.AllJointState = FakeAllJointState
    robot_msgs_msg.AllJointCmd = FakeAllJointCmd
    robot_msgs_msg.JointCmd = FakeJointCmd
    robot_msgs_msg.RobotState = FakeRobotStateMsg
    robot_msgs.msg = robot_msgs_msg

    yesense_interface = ModuleType("yesense_interface")
    yesense_interface_msg = ModuleType("yesense_interface.msg")
    yesense_interface_msg.NavAll = FakeNavAll
    yesense_interface.msg = yesense_interface_msg

    monkeypatch.setitem(sys.modules, "rclpy", rclpy)
    monkeypatch.setitem(sys.modules, "robot_msgs", robot_msgs)
    monkeypatch.setitem(sys.modules, "robot_msgs.msg", robot_msgs_msg)
    monkeypatch.setitem(sys.modules, "yesense_interface", yesense_interface)
    monkeypatch.setitem(sys.modules, "yesense_interface.msg", yesense_interface_msg)
    return rclpy


def _joint_state_msg(n_joints: int = 29):
    return SimpleNamespace(
        timestamp=123456,
        joint_states=[
            SimpleNamespace(
                joint_pos=i + 0.1,
                joint_vel=i + 0.2,
                joint_torque=i + 0.3,
                model_id=i,
                motor_id=100 + i,
                joint_error=0,
            )
            for i in range(n_joints)
        ],
    )


def _nav_msg():
    return SimpleNamespace(
        quat=SimpleNamespace(q0=1.0, q1=0.0, q2=0.0, q3=0.0),
        gyro=SimpleNamespace(x=0.01, y=0.02, z=0.03),
        acc=SimpleNamespace(x=0.1, y=0.2, z=9.81),
    )


def test_t4_ros2_robot_converts_ros2_state_without_creating_publisher(monkeypatch):
    rclpy = _install_fake_ros_modules(monkeypatch)
    robot = T4Ros2Robot(_make_t4_ros2_config())

    robot.connect()

    assert rclpy.init_called is True
    assert set(rclpy.node.subscriptions) == {
        "/all_joint_state",
        "/nav_all",
        "/robot_state",
    }
    assert rclpy.node.publisher_created is False

    rclpy.node.subscriptions["/all_joint_state"]["callback"](_joint_state_msg())
    rclpy.node.subscriptions["/nav_all"]["callback"](_nav_msg())
    rclpy.node.subscriptions["/robot_state"]["callback"](
        SimpleNamespace(robot_state=2, err_info="")
    )

    state = robot.get_state()

    np.testing.assert_allclose(state.joint_positions, np.arange(29) + 0.1)
    np.testing.assert_allclose(state.joint_velocities, np.arange(29) + 0.2)
    np.testing.assert_allclose(state.joint_torques, np.arange(29) + 0.3)
    np.testing.assert_allclose(state.imu_quaternion, [1.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(state.imu_angular_velocity, [0.01, 0.02, 0.03])
    np.testing.assert_allclose(state.imu_linear_acceleration, [0.1, 0.2, 9.81])
    assert np.all(np.isnan(state.base_position))
    assert np.all(np.isnan(state.base_velocity))
    assert robot.last_robot_state.robot_state == 2

    robot.disconnect()
    assert rclpy.node.destroyed is True
    assert rclpy.shutdown_called is True


def test_t4_ros2_robot_waits_for_first_joint_state(monkeypatch):
    rclpy = _install_fake_ros_modules(monkeypatch)
    robot = T4Ros2Robot(_make_t4_ros2_config())
    robot.connect()

    def publish_first_state(node, timeout_sec):
        node.subscriptions["/all_joint_state"]["callback"](_joint_state_msg())

    rclpy.spin_once_hook = publish_first_state

    state = robot.get_state()

    assert rclpy.spin_once_calls >= 1
    np.testing.assert_allclose(state.joint_positions, np.arange(29) + 0.1)


def test_t4_ros2_robot_builds_all_joint_cmd_without_publishing(monkeypatch):
    rclpy = _install_fake_ros_modules(monkeypatch)
    robot = T4Ros2Robot(_make_t4_ros2_config())
    robot.connect()
    cmd = RobotCommand(
        joint_positions=np.arange(29, dtype=np.float64) + 0.1,
        joint_velocities=np.arange(29, dtype=np.float64) + 0.2,
        joint_torques=np.arange(29, dtype=np.float64) + 0.3,
        kp=np.arange(29, dtype=np.float64) + 10.0,
        kd=np.arange(29, dtype=np.float64) + 1.0,
    )

    msg = robot.build_command_message(cmd)

    assert msg.cmd_type == 0
    assert msg.index == 0
    assert len(msg.joint_cmds) == 29
    for i, joint_cmd in enumerate(msg.joint_cmds):
        assert joint_cmd.joint_pos == pytest.approx(i + 0.1)
        assert joint_cmd.joint_vel == pytest.approx(i + 0.2)
        assert joint_cmd.joint_torque == pytest.approx(i + 0.3)
        assert joint_cmd.kp == pytest.approx(i + 10.0)
        assert joint_cmd.kd == pytest.approx(i + 1.0)
    assert rclpy.node.publisher_created is False


def test_t4_ros2_robot_rejects_wrong_length_command(monkeypatch):
    _install_fake_ros_modules(monkeypatch)
    robot = T4Ros2Robot(_make_t4_ros2_config())
    robot.connect()
    cmd = RobotCommand(
        joint_positions=np.zeros(23),
        joint_velocities=np.zeros(23),
        joint_torques=np.zeros(23),
        kp=np.zeros(23),
        kd=np.zeros(23),
    )

    with pytest.raises(ValueError, match="expected 29"):
        robot.build_command_message(cmd)


def test_t4_ros2_robot_command_publication_remains_disabled(monkeypatch):
    _install_fake_ros_modules(monkeypatch)
    robot = T4Ros2Robot(_make_t4_ros2_config())

    with pytest.raises(NotImplementedError, match="command publishing"):
        robot.send_command(RobotCommand.damping(robot.n_dof))
