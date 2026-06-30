"""Tests for the T4 robot backend boundary."""
from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pytest

from unitree_launcher.config import load_config
from unitree_launcher.robot.base import RobotCommand
from unitree_launcher.robot.t4_robot import T4Robot


def _make_t4_config():
    config = load_config("configs/real.yaml")
    config.robot.variant = "t4_29dof"
    config.network.domain_id = 7
    config.network.interface = "eth0"
    return config


class FakeChannelFactory:
    def __init__(self):
        self.init_calls = []

    def Init(self, domain_id, interface=""):
        self.init_calls.append((domain_id, interface))


class FakeSubscriber:
    instances = []

    def __init__(self, topic):
        self.topic = topic
        self.handler = None
        FakeSubscriber.instances.append(self)

    def InitChannel(self, handler, queuelen=0):
        self.handler = handler
        self.queuelen = queuelen


class FakePublisher:
    created = False
    writes = []

    def __init__(self, *args, **kwargs):
        FakePublisher.created = True

    def InitChannel(self):
        return None

    def Write(self, msg, wait_microsec=0):
        FakePublisher.writes.append((msg, wait_microsec))


class FakeJointCmd:
    def __init__(self):
        self.joint_pos_ = 0.0
        self.joint_vel_ = 0.0
        self.joint_torque_ = 0.0
        self.kp_ = 0.0
        self.kd_ = 0.0


class FakeAllJointCmd:
    def __init__(self):
        self.timestamp_ = 0
        self.index_ = 0
        self.cmd_type_ = 0
        self.joint_cmds_ = []


class FakeSdk:
    def __init__(self):
        self.factory = FakeChannelFactory()

        class FactoryAccessor:
            @staticmethod
            def Instance():
                return self.factory

        self.ChannelFactory = FactoryAccessor
        self.ChannelSubscriber_AllJointState_ = FakeSubscriber
        self.ChannelSubscriber_NavAll_ = FakeSubscriber
        self.ChannelPublisher_AllJointCmd_ = FakePublisher
        self.JointCmd_ = FakeJointCmd
        self.AllJointCmd_ = FakeAllJointCmd


class FakeJointState:
    def __init__(self, idx: int):
        self.joint_pos_ = idx + 0.1
        self.joint_vel_ = idx + 0.2
        self.joint_torque_ = idx + 0.3


class FakeAllJointState:
    timestamp_ = 123456

    def __init__(self, n_joints: int):
        self.joint_states_ = [FakeJointState(i) for i in range(n_joints)]


def test_t4_robot_converts_sdk_joint_and_nav_messages_to_robot_state(monkeypatch):
    FakeSubscriber.instances = []
    FakePublisher.created = False
    sdk = FakeSdk()
    monkeypatch.setitem(sys.modules, "zv_robot_sdk_python", sdk)

    robot = T4Robot(_make_t4_config())
    robot.connect()

    assert sdk.factory.init_calls == [(7, "eth0")]
    assert [sub.topic for sub in FakeSubscriber.instances] == [
        "rt/all_joint_state",
        "rt/nav_all",
    ]
    assert FakePublisher.created is False

    joint_sub, nav_sub = FakeSubscriber.instances
    joint_sub.handler(FakeAllJointState(29))
    nav_sub.handler(
        SimpleNamespace(
            quat_=SimpleNamespace(q0_=1.0, q1_=0.0, q2_=0.0, q3_=0.0),
            gyro_=SimpleNamespace(x_=0.01, y_=0.02, z_=0.03),
            acc_=SimpleNamespace(x_=0.1, y_=0.2, z_=9.81),
        )
    )

    state = robot.get_state()

    assert state.joint_positions.shape == (29,)
    np.testing.assert_allclose(state.joint_positions, np.arange(29) + 0.1)
    np.testing.assert_allclose(state.joint_velocities, np.arange(29) + 0.2)
    np.testing.assert_allclose(state.joint_torques, np.arange(29) + 0.3)
    np.testing.assert_allclose(state.imu_quaternion, [1.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(state.imu_angular_velocity, [0.01, 0.02, 0.03])
    np.testing.assert_allclose(state.imu_linear_acceleration, [0.1, 0.2, 9.81])
    assert np.all(np.isnan(state.base_position))
    assert np.all(np.isnan(state.base_velocity))


def test_t4_robot_command_publication_remains_disabled():
    robot = T4Robot(_make_t4_config())
    cmd = RobotCommand.damping(robot.n_dof)

    with pytest.raises(NotImplementedError, match="command publishing"):
        robot.send_command(cmd)


def test_t4_robot_builds_all_joint_cmd_without_publishing(monkeypatch):
    FakeSubscriber.instances = []
    FakePublisher.created = False
    FakePublisher.writes = []
    sdk = FakeSdk()
    monkeypatch.setitem(sys.modules, "zv_robot_sdk_python", sdk)

    robot = T4Robot(_make_t4_config())
    robot.connect()
    cmd = RobotCommand(
        joint_positions=np.arange(29, dtype=np.float64) + 0.1,
        joint_velocities=np.arange(29, dtype=np.float64) + 0.2,
        joint_torques=np.arange(29, dtype=np.float64) + 0.3,
        kp=np.arange(29, dtype=np.float64) + 10.0,
        kd=np.arange(29, dtype=np.float64) + 1.0,
    )

    sdk_msg = robot.build_command_message(cmd)

    assert len(sdk_msg.joint_cmds_) == 29
    for i, joint_cmd in enumerate(sdk_msg.joint_cmds_):
        assert joint_cmd.joint_pos_ == pytest.approx(i + 0.1)
        assert joint_cmd.joint_vel_ == pytest.approx(i + 0.2)
        assert joint_cmd.joint_torque_ == pytest.approx(i + 0.3)
        assert joint_cmd.kp_ == pytest.approx(i + 10.0)
        assert joint_cmd.kd_ == pytest.approx(i + 1.0)
    assert sdk_msg.cmd_type_ == 0
    assert sdk_msg.index_ == 0
    assert FakePublisher.created is False
    assert FakePublisher.writes == []


def test_t4_robot_rejects_wrong_length_command(monkeypatch):
    sdk = FakeSdk()
    monkeypatch.setitem(sys.modules, "zv_robot_sdk_python", sdk)
    robot = T4Robot(_make_t4_config())
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
