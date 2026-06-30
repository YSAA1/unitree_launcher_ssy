"""T4 robot assets."""

from pathlib import Path

import mujoco

from mjlab import MJLAB_SRC_PATH
from mjlab.actuator import BuiltinPositionActuatorCfg
from mjlab.entity import EntityArticulationInfoCfg, EntityCfg

##
# MJCF and assets.
##

T4_XML: Path = (
  MJLAB_SRC_PATH / "asset_zoo" / "robots" / "t4" / "xmls" / "t4_std.xml"
)
assert T4_XML.exists()
T4_URDF: Path = (
  MJLAB_SRC_PATH / "asset_zoo" / "robots" / "t4" / "urdf" / "t4_std.urdf"
)
assert T4_URDF.exists()


def get_spec() -> mujoco.MjSpec:
  return mujoco.MjSpec.from_file(str(T4_XML))


##
# Actuator config.
##

NATURAL_FREQ = 10 * 2.0 * 3.1415926535  # 10Hz
DAMPING_RATIO = 2.0


def _stiffness(armature: float) -> float:
  return armature * NATURAL_FREQ**2


def _damping(armature: float) -> float:
  return 2.0 * DAMPING_RATIO * armature * NATURAL_FREQ


def _position_actuator(
  target_names_expr: tuple[str, ...],
  *,
  armature: float,
  effort_limit: float,
) -> BuiltinPositionActuatorCfg:
  return BuiltinPositionActuatorCfg(
    target_names_expr=target_names_expr,
    stiffness=_stiffness(armature),
    damping=_damping(armature),
    effort_limit=effort_limit,
    armature=armature,
  )


T4_ACTUATOR_ARM_25 = _position_actuator(
  ("J_arm_[lr]_0[1-4]",),
  armature=0.0236,
  effort_limit=25.0,
)
T4_ACTUATOR_ARM_12_LONG = _position_actuator(
  ("J_arm_[lr]_05",),
  armature=0.0236,
  effort_limit=12.0,
)
T4_ACTUATOR_ARM_12_SHORT = _position_actuator(
  ("J_arm_[lr]_0[6-7]",),
  armature=0.0055,
  effort_limit=12.0,
)
T4_ACTUATOR_WAIST_ANKLE_72 = _position_actuator(
  (
    "J_waist_pitch",
    "J_waist_roll",
    "J_ankle_[lr]_pitch",
    "J_ankle_[lr]_roll",
  ),
  armature=0.0472,
  effort_limit=72.0,
)
T4_ACTUATOR_HIP_WAIST_120 = _position_actuator(
  (
    "J_waist_yaw",
    "J_hip_[lr]_roll",
    "J_hip_[lr]_yaw",
  ),
  armature=0.0943,
  effort_limit=120.0,
)
T4_ACTUATOR_HIP_KNEE_130 = _position_actuator(
  (
    "J_hip_[lr]_pitch",
    "J_knee_[lr]_pitch",
  ),
  armature=0.0625,
  effort_limit=130.0,
)

##
# Final config.
##

T4_ARTICULATION = EntityArticulationInfoCfg(
  actuators=(
    T4_ACTUATOR_ARM_25,
    T4_ACTUATOR_ARM_12_LONG,
    T4_ACTUATOR_ARM_12_SHORT,
    T4_ACTUATOR_WAIST_ANKLE_72,
    T4_ACTUATOR_HIP_WAIST_120,
    T4_ACTUATOR_HIP_KNEE_130,
  ),
  soft_joint_pos_limit_factor=0.9,
)


def get_t4_robot_cfg() -> EntityCfg:
  """Get a fresh T4 robot configuration instance."""
  return EntityCfg(
    init_state=EntityCfg.InitialStateCfg(pos=(0.0, 0.0, 0.9)),
    spec_fn=get_spec,
    articulation=T4_ARTICULATION,
  )


T4_ACTION_SCALE: dict[str, float] = {}
for a in T4_ARTICULATION.actuators:
  assert isinstance(a, BuiltinPositionActuatorCfg)
  e = a.effort_limit
  s = a.stiffness
  names = a.target_names_expr
  assert e is not None
  for n in names:
    T4_ACTION_SCALE[n] = 0.25 * e / s


if __name__ == "__main__":
  import mujoco.viewer as viewer

  from mjlab.entity.entity import Entity

  robot = Entity(get_t4_robot_cfg())

  viewer.launch(robot.spec.compile())
