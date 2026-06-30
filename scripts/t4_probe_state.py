#!/usr/bin/env python3
"""Read-only T4 low-level state probe.

This script subscribes to Zvalley's ``rt/all_joint_state`` topic and prints
diagnostic state fields. It intentionally never creates a command publisher.
"""
from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path
from typing import Any


DEFAULT_TOPIC = "rt/all_joint_state"
DEFAULT_NAV_TOPIC = "rt/nav_all"
DEFAULT_SDK_ROOT = Path(__file__).resolve().parent.parent / "zv_robot_sdk"


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


def _print_state(msg: Any) -> None:
    timestamp = _read_field(msg, "timestamp_", "missing")
    index = _read_field(msg, "index_", "missing")
    used_for_ctrl = _read_field(msg, "used_for_ctrl_", "missing")
    print(f"timestamp: {timestamp}")
    print(f"index: {index}")
    print(f"used_for_ctrl: {used_for_ctrl}")

    joint_states = _read_field(msg, "joint_states_", [])
    if joint_states is None:
        joint_states = []
    print(f"joint_count: {len(joint_states)}")

    for idx, joint in enumerate(joint_states):
        fields = _format_field(
            joint,
            (
                "model_id_",
                "motor_id_",
                "joint_pos_",
                "joint_vel_",
                "joint_torque_",
                "joint_error_",
            ),
        )
        print(f"joint[{idx}]: {fields}")

    imu = _read_field(msg, "imu_state_", None)
    if imu is None:
        print("imu: not found")
    else:
        fields = _format_field(
            imu,
            (
                "quaternion_",
                "gyroscope_",
                "accelerometer_",
                "rpy_",
                "temperature_",
            ),
        )
        print(f"imu: found {fields}")


def _read_nested(obj: Any, path: tuple[str, ...]) -> Any:
    value = obj
    for name in path:
        value = _read_field(value, name, None)
        if value is None:
            return None
    return value


def _print_nav(msg: Any) -> None:
    acc = [
        _read_nested(msg, ("acc_", "x_")),
        _read_nested(msg, ("acc_", "y_")),
        _read_nested(msg, ("acc_", "z_")),
    ]
    euler = [
        _read_nested(msg, ("euler_", "pitch_")),
        _read_nested(msg, ("euler_", "roll_")),
        _read_nested(msg, ("euler_", "yaw_")),
    ]
    found = any(value is not None for value in acc + euler)
    if found:
        print(f"nav: found acc={acc} euler={euler}")
    else:
        print("nav: found no known fields")


def _load_sdk(sdk_root: str | None = None):
    root = Path(sdk_root) if sdk_root else DEFAULT_SDK_ROOT
    sdk_lib = root / "libs" / "python"
    if sdk_lib.exists() and str(sdk_lib) not in sys.path:
        sys.path.insert(0, str(sdk_lib))

    try:
        import zv_robot_sdk_python as zv
    except ImportError as exc:
        raise SystemExit(
            "Could not import zv_robot_sdk_python. Run this probe in the T4 "
            "official/onboard control environment or add the Zvalley SDK "
            "python libs to PYTHONPATH. You can also pass --sdk-root pointing "
            "at a zv_robot_sdk checkout."
        ) from exc
    return zv


def probe_state(
    *,
    sdk: Any | None = None,
    domain_id: int = 0,
    interface: str = "",
    topic: str = DEFAULT_TOPIC,
    nav_topic: str = DEFAULT_NAV_TOPIC,
    samples: int = 1,
    timeout: float = 5.0,
    sdk_root: str | None = None,
) -> None:
    """Subscribe to T4 joint state and print a bounded number of samples."""
    sdk = sdk or _load_sdk(sdk_root=sdk_root)
    done = threading.Event()
    seen = {"count": 0}

    def handler(msg: Any) -> None:
        _print_state(msg)
        seen["count"] += 1
        if seen["count"] >= samples:
            done.set()

    sdk.ChannelFactory.Instance().Init(domain_id, interface)
    subscriber = sdk.ChannelSubscriber_AllJointState_(topic)
    subscriber.InitChannel(handler)
    print(f"subscribed: {topic}")

    nav_subscriber_cls = getattr(sdk, "ChannelSubscriber_NavAll_", None)
    if nav_topic and nav_subscriber_cls is not None:
        nav_subscriber = nav_subscriber_cls(nav_topic)
        nav_subscriber.InitChannel(_print_nav)
        print(f"subscribed_nav: {nav_topic}")
    elif nav_topic:
        print("nav: subscriber not available")

    print("read_only: true")

    done.wait(timeout)
    if seen["count"] == 0:
        print(f"timeout: no samples received within {timeout:.1f}s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain-id", type=int, default=0)
    parser.add_argument("--interface", default="")
    parser.add_argument("--topic", default=DEFAULT_TOPIC)
    parser.add_argument("--nav-topic", default=DEFAULT_NAV_TOPIC)
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument(
        "--sdk-root",
        default=str(DEFAULT_SDK_ROOT),
        help="Path to a local zv_robot_sdk checkout; its libs/python is added to sys.path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    probe_state(
        domain_id=args.domain_id,
        interface=args.interface,
        topic=args.topic,
        nav_topic=args.nav_topic,
        samples=args.samples,
        timeout=args.timeout,
        sdk_root=args.sdk_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
