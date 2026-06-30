"""Tests for the read-only T4 SDK state probe."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = PROJECT_ROOT / "scripts" / "t4_probe_state.py"


def _load_probe_module():
    spec = importlib.util.spec_from_file_location("t4_probe_state", PROBE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeJointState:
    def __init__(self, idx: int):
        self.model_id_ = 100 + idx
        self.motor_id_ = 200 + idx
        self.joint_pos_ = 0.1 * idx
        self.joint_vel_ = 0.2 * idx
        self.joint_torque_ = 0.3 * idx
        self.joint_error_ = idx % 2


class FakeAllJointState:
    timestamp_ = 123456
    index_ = 7
    used_for_ctrl_ = 1

    def __init__(self):
        self.joint_states_ = [FakeJointState(0), FakeJointState(1)]
        self.imu_state_ = SimpleNamespace(
            quaternion_=[1.0, 0.0, 0.0, 0.0],
            gyroscope_=[0.1, 0.2, 0.3],
            accelerometer_=[0.0, 0.0, 9.81],
        )


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


class FakeNavSubscriber(FakeSubscriber):
    instances = []

    def __init__(self, topic):
        self.topic = topic
        self.handler = None
        FakeNavSubscriber.instances.append(self)


class FakePublisher:
    created = False

    def __init__(self, *args, **kwargs):
        FakePublisher.created = True


class FakeSdk:
    def __init__(self):
        self.factory = FakeChannelFactory()

        class FactoryAccessor:
            @staticmethod
            def Instance():
                return self.factory

        self.ChannelFactory = FactoryAccessor
        self.ChannelSubscriber_AllJointState_ = FakeSubscriber
        self.ChannelSubscriber_NavAll_ = FakeNavSubscriber
        self.ChannelPublisher_AllJointCmd_ = FakePublisher


def test_probe_state_is_read_only_and_prints_available_fields(capsys):
    module = _load_probe_module()
    sdk = FakeSdk()
    FakePublisher.created = False

    module.probe_state(sdk=sdk, domain_id=3, interface="eth0", samples=1, timeout=0.1)

    subscriber = FakeSubscriber.instances[-1]
    assert subscriber.topic == "rt/all_joint_state"
    assert subscriber.handler is not None

    subscriber.handler(FakeAllJointState())
    out = capsys.readouterr().out

    assert "joint_count: 2" in out
    assert "timestamp: 123456" in out
    assert "joint[0]" in out
    assert "model_id=100" in out
    assert "motor_id=200" in out
    assert "joint_pos=0.0" in out
    assert "imu: found" in out
    assert sdk.factory.init_calls == [(3, "eth0")]
    assert FakePublisher.created is False


def test_probe_state_handles_missing_optional_fields(capsys):
    module = _load_probe_module()

    class MinimalState:
        joint_states_ = [object()]

    module._print_state(MinimalState())
    out = capsys.readouterr().out

    assert "timestamp: missing" in out
    assert "joint_count: 1" in out
    assert "joint[0]: no known fields" in out
    assert "imu: not found" in out


def test_load_sdk_can_use_local_sdk_root(tmp_path, monkeypatch):
    module = _load_probe_module()
    sdk_root = tmp_path / "zv_robot_sdk"
    sdk_lib = sdk_root / "libs" / "python"
    sdk_lib.mkdir(parents=True)
    (sdk_lib / "zv_robot_sdk_python.py").write_text("__version__ = 'fake'\n")
    monkeypatch.delitem(sys.modules, "zv_robot_sdk_python", raising=False)

    sdk = module._load_sdk(sdk_root=str(sdk_root))

    assert sdk.__version__ == "fake"
    assert str(sdk_lib) in sys.path


def test_probe_state_subscribes_to_nav_topic_when_available(capsys):
    module = _load_probe_module()
    sdk = FakeSdk()

    module.probe_state(sdk=sdk, samples=1, timeout=0.1)

    nav_subscriber = FakeNavSubscriber.instances[-1]
    assert nav_subscriber.topic == "rt/nav_all"
    assert nav_subscriber.handler is not None

    nav_msg = SimpleNamespace(
        acc_=SimpleNamespace(x_=0.0, y_=0.0, z_=9.81),
        euler_=SimpleNamespace(pitch_=0.1, roll_=0.2, yaw_=0.3),
    )
    nav_subscriber.handler(nav_msg)
    out = capsys.readouterr().out

    assert "nav: found" in out
    assert "acc=[0.0, 0.0, 9.81]" in out
    assert "euler=[0.1, 0.2, 0.3]" in out
