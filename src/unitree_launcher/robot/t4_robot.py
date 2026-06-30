"""T4 robot backend boundary for Zvalley SDK integration.

This module intentionally does not publish commands yet.  It exists to make
``robot.variant: t4_29dof`` route to a T4-specific backend instead of the G1
``unitree_cpp`` backend while the Zvalley low-level command path is being
validated.
"""
from __future__ import annotations

import logging

from unitree_launcher.config import Config, _get_joints_for_variant
from unitree_launcher.robot.base import RobotCommand, RobotInterface, RobotState

logger = logging.getLogger(__name__)


class T4Robot(RobotInterface):
    """T4 backend placeholder using the project RobotInterface contract."""

    def __init__(self, config: Config):
        self._joints = _get_joints_for_variant(config.robot.variant)
        self._n_dof = len(self._joints)
        self._iface_name = config.network.interface
        self._domain_id = config.network.domain_id
        self._connected = False

    def connect(self) -> None:
        """Refuse control until the Zvalley command path is implemented."""
        raise NotImplementedError(
            "T4 real control is not implemented yet. "
            "Use scripts/t4_probe_state.py for read-only SDK connectivity checks."
        )

    def disconnect(self) -> None:
        self._connected = False
        logger.info("T4Robot disconnected")

    def get_state(self) -> RobotState:
        return RobotState.zeros(self._n_dof)

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
