"""Zeon bridge -- make Zeon's arm speak PyLabRobot.

The winning wedge: Zeon built a proprietary NL→vision→arm stack and does NOT use
PyLabRobot. If a PyLabRobot arm backend targets Zeon's platform, then the entire
PLR protocol library -- plus your DBTL loop, Rhodamine validation, and conformal
gate -- runs on Zeon hardware unchanged.

`plr-lab-robot` already proved the pattern: it implements a *simulation* backend
for PyLabRobot's `ExperimentalSCARA` arm, and swapping it for a hardware backend
(e.g. PreciseFlex) drives a real arm with the same code. This file is the
on-site stub for a THIRD backend: Zeon.

ON-SITE PLAN (build #1, once you can see Zeon's SDK/API):
  1. Find how Zeon exposes motion (Python SDK? REST? gRPC? a socket?).
  2. Map the SCARA/arm primitives below to Zeon calls.
  3. Construct `ExperimentalSCARA(backend=ZeonArmBackend(...))` (or point
     plr-epigenome's robot_arm.RobotArmBackend at Zeon) and re-run the demo.
  4. Keep plr_lr.SimulationArmBackend as the guaranteed fallback.

Nothing here imports pylabrobot at module load, so bay-hack still runs in pure
simulation without it installed.
"""
from __future__ import annotations


class ZeonArmBackend:
    """Skeleton PyLabRobot arm backend that would drive Zeon's platform.

    Shape it to match the arm backend interface your plr_lr code already targets
    (SCARABackend: setup/stop, move_joints/move_cartesian, gripper open/close,
    home). Fill each method with the Zeon SDK call discovered on-site.
    """

    def __init__(self, sdk=None, host: str | None = None, speed_cap: float = 0.5):
        self.sdk = sdk                 # Zeon client, injected on-site
        self.host = host
        self.speed_cap = speed_cap     # keep motion gentle for a live demo
        self._connected = False

    # --- lifecycle ---------------------------------------------------------
    async def setup(self) -> None:
        raise NotImplementedError("Connect to Zeon's motion API on-site.")

    async def stop(self) -> None:
        self._connected = False

    async def home(self) -> None:
        raise NotImplementedError("Map to Zeon home/reset.")

    # --- motion (map to Zeon primitives) -----------------------------------
    async def move_cartesian(self, x: float, y: float, z: float, **kw) -> None:
        raise NotImplementedError("Map to Zeon Cartesian move (respect speed_cap).")

    async def move_joints(self, *joints: float) -> None:
        raise NotImplementedError("Map to Zeon joint move if exposed.")

    # --- gripper (needed for plate moves + DecapSkill) ---------------------
    async def gripper(self, open: bool) -> None:
        raise NotImplementedError("Map to Zeon gripper open/close.")


def bridge_notes() -> str:
    return (
        "ZeonArmBackend is a stub. On-site: discover Zeon's motion API, implement "
        "setup/home/move_cartesian/gripper, then run the same DBTL loop with the "
        "arm backend swapped from SimulationArmBackend to ZeonArmBackend."
    )
