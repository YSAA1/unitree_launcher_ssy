"""Tests for the read-only T4 ROS2 state probe."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = PROJECT_ROOT / "scripts" / "t4_ros2_probe_state.py"


def _load_probe_module():
    spec = importlib.util.spec_from_file_location("t4_ros2_probe_state", PROBE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeNode:
    def __init__(self):
        self.subscriptions = {}
        self.publisher_created = False
        self.destroyed = False
        self.delivered = False

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

    def deliver_once(self):
        if self.delivered:
            return
        self.delivered = True
        self.subscriptions["/all_joint_state"]["callback"](
            SimpleNamespace(
                timestamp=123456,
                index=9,
                used_for_ctrl=1,
                joint_states=[
                    SimpleNamespace(
                        model_id=i,
                        motor_id=100 + i,
                        joint_pos=0.1 * i,
                        joint_vel=0.2 * i,
                        joint_torque=0.3 * i,
                        joint_error=0,
                    )
                    for i in range(29)
                ],
            )
        )
        self.subscriptions["/robot_state"]["callback"](
            SimpleNamespace(robot_state=3, err_info="robot is ok")
        )
        self.subscriptions["/nav_all"]["callback"](
            SimpleNamespace(
                acc=SimpleNamespace(x=0.0, y=0.0, z=9.81),
                gyro=SimpleNamespace(x=0.1, y=0.2, z=0.3),
                euler=SimpleNamespace(pitch=0.4, roll=0.5, yaw=0.6),
                quat=SimpleNamespace(q0=1.0, q1=0.0, q2=0.0, q3=0.0),
            )
        )


class FakeRclpy:
    def __init__(self):
        self.node = FakeNode()
        self.init_called = False
        self.shutdown_called = False

    def init(self, args=None):
        self.init_called = True

    def create_node(self, name):
        self.node_name = name
        return self.node

    def spin_once(self, node, timeout_sec=0.1):
        node.deliver_once()

    def shutdown(self):
        self.shutdown_called = True


class StaggeredFakeNode(FakeNode):
    def __init__(self):
        super().__init__()
        self.spin_count = 0

    def deliver_once(self):
        self.spin_count += 1
        if self.spin_count == 1:
            self.subscriptions["/all_joint_state"]["callback"](
                SimpleNamespace(
                    timestamp=1,
                    index=1,
                    used_for_ctrl=0,
                    joint_states=[SimpleNamespace(model_id=0, motor_id=11)],
                )
            )
            return
        self.subscriptions["/robot_state"]["callback"](
            SimpleNamespace(robot_state=3, err_info="robot is ok")
        )
        self.subscriptions["/nav_all"]["callback"](
            SimpleNamespace(acc=SimpleNamespace(x=0.0, y=0.0, z=9.81))
        )


class StaggeredFakeRclpy(FakeRclpy):
    def __init__(self):
        super().__init__()
        self.node = StaggeredFakeNode()


class RepeatedBeforeReadyNode(FakeNode):
    def __init__(self):
        super().__init__()
        self.spin_count = 0

    def deliver_once(self):
        self.spin_count += 1
        self.subscriptions["/all_joint_state"]["callback"](
            SimpleNamespace(
                timestamp=self.spin_count,
                index=self.spin_count,
                used_for_ctrl=0,
                joint_states=[SimpleNamespace(model_id=0, motor_id=11)],
            )
        )
        self.subscriptions["/nav_all"]["callback"](
            SimpleNamespace(acc=SimpleNamespace(x=0.0, y=0.0, z=9.81))
        )
        if self.spin_count >= 3:
            self.subscriptions["/robot_state"]["callback"](
                SimpleNamespace(robot_state=2, err_info="")
            )


class RepeatedBeforeReadyRclpy(FakeRclpy):
    def __init__(self):
        super().__init__()
        self.node = RepeatedBeforeReadyNode()


def test_ros2_probe_is_read_only_and_reports_t4_state(capsys):
    module = _load_probe_module()
    fake_rclpy = FakeRclpy()

    module.probe_ros2_state(
        rclpy_module=fake_rclpy,
        message_types={
            "all_joint_state": object,
            "nav_all": object,
            "robot_state": object,
        },
        samples=1,
        timeout=0.2,
    )

    out = capsys.readouterr().out

    assert fake_rclpy.init_called is True
    assert fake_rclpy.shutdown_called is True
    assert fake_rclpy.node.destroyed is True
    assert fake_rclpy.node.publisher_created is False
    assert set(fake_rclpy.node.subscriptions) == {
        "/all_joint_state",
        "/nav_all",
        "/robot_state",
    }
    assert "read_only: true" in out
    assert "subscribed: /all_joint_state" in out
    assert "subscribed_nav: /nav_all" in out
    assert "subscribed_robot_state: /robot_state" in out
    assert "joint_count: 29" in out
    assert "joint[0]: model_id=0 motor_id=100 joint_pos=0.0" in out
    assert "robot_state: 3" in out
    assert "err_info: robot is ok" in out
    assert "nav: found" in out


def test_ros2_probe_prints_only_first_sample_per_topic(capsys):
    module = _load_probe_module()

    module.probe_ros2_state(
        rclpy_module=RepeatedBeforeReadyRclpy(),
        message_types={
            "all_joint_state": object,
            "nav_all": object,
            "robot_state": object,
        },
        samples=1,
        timeout=0.2,
    )

    out = capsys.readouterr().out

    assert out.count("joint_count:") == 1
    assert out.count("nav: found") == 1
    assert out.count("\nrobot_state:") == 1


def test_ros2_probe_waits_for_nav_and_robot_state_after_joint_sample(capsys):
    module = _load_probe_module()
    fake_rclpy = StaggeredFakeRclpy()

    module.probe_ros2_state(
        rclpy_module=fake_rclpy,
        message_types={
            "all_joint_state": object,
            "nav_all": object,
            "robot_state": object,
        },
        samples=1,
        timeout=0.2,
    )

    out = capsys.readouterr().out

    assert fake_rclpy.node.spin_count >= 2
    assert "joint_count: 1" in out
    assert "robot_state: 3" in out
    assert "nav: found" in out


class SilentFakeRclpy(FakeRclpy):
    def spin_once(self, node, timeout_sec=0.1):
        return None


def test_ros2_probe_reports_timeout_without_samples(capsys):
    module = _load_probe_module()

    module.probe_ros2_state(
        rclpy_module=SilentFakeRclpy(),
        message_types={
            "all_joint_state": object,
            "nav_all": object,
            "robot_state": object,
        },
        timeout=0.01,
    )

    out = capsys.readouterr().out

    assert "read_only: true" in out
    assert "timeout: no joint samples received within 0.0s" in out


def test_ros2_probe_rejects_unbounded_invocations():
    module = _load_probe_module()

    try:
        module.probe_ros2_state(
            rclpy_module=FakeRclpy(),
            message_types={
                "all_joint_state": object,
                "nav_all": object,
                "robot_state": object,
            },
            samples=0,
        )
    except ValueError as exc:
        assert "samples must be positive" in str(exc)
    else:
        raise AssertionError("expected samples validation error")

    try:
        module.probe_ros2_state(
            rclpy_module=FakeRclpy(),
            message_types={
                "all_joint_state": object,
                "nav_all": object,
                "robot_state": object,
            },
            timeout=0,
        )
    except ValueError as exc:
        assert "timeout must be positive" in str(exc)
    else:
        raise AssertionError("expected timeout validation error")
