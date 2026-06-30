#!/usr/bin/env python3
"""Read-only T4 ROS2 state probe.

This probe is intended for the T4 onboard ROS2 control environment. It
subscribes to state topics and prints bounded diagnostic output. It never
creates command publishers.
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Any


DEFAULT_JOINT_TOPIC = "/all_joint_state"
DEFAULT_NAV_TOPIC = "/nav_all"
DEFAULT_ROBOT_STATE_TOPIC = "/robot_state"


def _read_field(obj: Any, name: str, default: Any = None) -> Any:
    value = getattr(obj, name, default)
    if callable(value):
        try:
            return value()
        except TypeError:
            return value
    return value


def _format_field(obj: Any, names: tuple[str, ...]) -> str:
    parts: list[str] = []
    for name in names:
        value = _read_field(obj, name, None)
        if value is not None:
            parts.append(f"{name.rstrip('_')}={value}")
    return " ".join(parts) if parts else "no known fields"


def _print_joint_state(msg: Any) -> int:
    print(f"timestamp: {_read_field(msg, 'timestamp', 'missing')}")
    print(f"index: {_read_field(msg, 'index', 'missing')}")
    print(f"used_for_ctrl: {_read_field(msg, 'used_for_ctrl', 'missing')}")

    joint_states = list(_read_field(msg, "joint_states", []) or [])
    print(f"joint_count: {len(joint_states)}")
    for idx, joint in enumerate(joint_states):
        fields = _format_field(
            joint,
            (
                "model_id",
                "motor_id",
                "joint_pos",
                "joint_vel",
                "joint_torque",
                "joint_error",
            ),
        )
        print(f"joint[{idx}]: {fields}")
    return len(joint_states)


def _read_nested(obj: Any, path: tuple[str, ...]) -> Any:
    value = obj
    for name in path:
        value = _read_field(value, name, None)
        if value is None:
            return None
    return value


def _print_nav(msg: Any) -> None:
    acc = [
        _read_nested(msg, ("acc", "x")),
        _read_nested(msg, ("acc", "y")),
        _read_nested(msg, ("acc", "z")),
    ]
    gyro = [
        _read_nested(msg, ("gyro", "x")),
        _read_nested(msg, ("gyro", "y")),
        _read_nested(msg, ("gyro", "z")),
    ]
    euler = [
        _read_nested(msg, ("euler", "pitch")),
        _read_nested(msg, ("euler", "roll")),
        _read_nested(msg, ("euler", "yaw")),
    ]
    quat = [
        _read_nested(msg, ("quat", "q0")),
        _read_nested(msg, ("quat", "q1")),
        _read_nested(msg, ("quat", "q2")),
        _read_nested(msg, ("quat", "q3")),
    ]
    found = any(value is not None for value in acc + gyro + euler + quat)
    if found:
        print(f"nav: found acc={acc} gyro={gyro} euler={euler} quat={quat}")
    else:
        print("nav: found no known fields")


def _print_robot_state(msg: Any) -> None:
    print(f"robot_state: {_read_field(msg, 'robot_state', 'missing')}")
    print(f"err_info: {_read_field(msg, 'err_info', 'missing')}")


def _load_ros2_message_types() -> dict[str, Any]:
    try:
        from robot_msgs.msg import AllJointState, RobotState
        from yesense_interface.msg import NavAll
    except ImportError as exc:
        raise SystemExit(
            "Could not import T4 ROS2 message types. Run this probe after "
            "sourcing /home/zl/work/bipedal_humanoid_pro/install/setup.bash "
            "on the T4 onboard control environment."
        ) from exc
    return {
        "all_joint_state": AllJointState,
        "nav_all": NavAll,
        "robot_state": RobotState,
    }


def _load_rclpy():
    try:
        import rclpy
    except ImportError as exc:
        raise SystemExit(
            "Could not import rclpy. Run this probe in the T4 ROS2 environment."
        ) from exc
    return rclpy


def probe_ros2_state(
    *,
    rclpy_module: Any | None = None,
    message_types: dict[str, Any] | None = None,
    joint_topic: str = DEFAULT_JOINT_TOPIC,
    nav_topic: str = DEFAULT_NAV_TOPIC,
    robot_state_topic: str = DEFAULT_ROBOT_STATE_TOPIC,
    samples: int = 1,
    timeout: float = 5.0,
) -> None:
    """Subscribe to T4 ROS2 state topics and print bounded diagnostics."""
    if samples <= 0:
        raise ValueError("samples must be positive")
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    rclpy = rclpy_module or _load_rclpy()
    types = message_types or _load_ros2_message_types()
    seen = {"joint": 0, "nav": 0, "robot_state": 0}

    def handle_joint_state(msg: Any) -> None:
        seen["joint"] += 1
        if seen["joint"] == 1:
            _print_joint_state(msg)

    def handle_nav(msg: Any) -> None:
        seen["nav"] += 1
        if seen["nav"] == 1:
            _print_nav(msg)

    def handle_robot_state(msg: Any) -> None:
        seen["robot_state"] += 1
        if seen["robot_state"] == 1:
            _print_robot_state(msg)

    rclpy.init(args=None)
    node = rclpy.create_node("t4_ros2_probe_state")
    try:
        node.create_subscription(
            types["all_joint_state"],
            joint_topic,
            handle_joint_state,
            10,
        )
        print(f"subscribed: {joint_topic}")

        if nav_topic:
            node.create_subscription(types["nav_all"], nav_topic, handle_nav, 10)
            print(f"subscribed_nav: {nav_topic}")

        if robot_state_topic:
            node.create_subscription(
                types["robot_state"], robot_state_topic, handle_robot_state, 10
            )
            print(f"subscribed_robot_state: {robot_state_topic}")

        print("read_only: true")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            joint_ready = seen["joint"] >= samples
            nav_ready = not nav_topic or seen["nav"] > 0
            robot_state_ready = (
                not robot_state_topic or seen["robot_state"] > 0
            )
            if joint_ready and nav_ready and robot_state_ready:
                break
            rclpy.spin_once(node, timeout_sec=0.1)

        if seen["joint"] == 0:
            print(f"timeout: no joint samples received within {timeout:.1f}s")
        if nav_topic and seen["nav"] == 0:
            print(f"timeout: no nav samples received within {timeout:.1f}s")
        if robot_state_topic and seen["robot_state"] == 0:
            print(f"timeout: no robot state samples received within {timeout:.1f}s")
    finally:
        node.destroy_node()
        rclpy.shutdown()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--joint-topic", default=DEFAULT_JOINT_TOPIC)
    parser.add_argument("--nav-topic", default=DEFAULT_NAV_TOPIC)
    parser.add_argument("--robot-state-topic", default=DEFAULT_ROBOT_STATE_TOPIC)
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    probe_ros2_state(
        joint_topic=args.joint_topic,
        nav_topic=args.nav_topic,
        robot_state_topic=args.robot_state_topic,
        samples=args.samples,
        timeout=args.timeout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
