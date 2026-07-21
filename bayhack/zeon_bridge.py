"""Zeon bridge for coupling physical and scientific world models.

Zeon's physical world model tracks geometry, equipment, labware, and state.
bay-hack's scientific world model selects the next experiment. This adapter shape
maps verified PyLabRobot actions into the Python workflow or skill executor Zeon
provides on-site.

Unlike a hand-waved stub, `ZeonArmBackend` RUNS TODAY in simulation: it subclasses
plr_lr's `SimulationArmBackend` (a full `pylabrobot.arms.backend.SCARABackend`,
N_JOINTS=5), so `ExperimentalSCARA(backend=ZeonArmBackend())` drives the complete
pick / place / gripper choreography with no hardware. Every real-motion primitive
is overridden to record a Zeon-SDK SEAM (`self.zeon_calls`) marking exactly where
the on-site call goes. The demo beat "swap one backend and the same loop drives
Zeon's arm" therefore executes live -- see `zeon_swap_selfcheck()`.

ON-SITE (build #1, once you can see Zeon's SDK): replace each `# TODO: self.sdk...`
with the real call and drop the `super()` sim fallback. Nothing else changes.

This module imports pylabrobot lazily/guarded, so the pure-sim bay-hack path still
runs without it installed.
"""
from __future__ import annotations

import asyncio
import contextlib
import io

try:
    from plr_lr.arm.sim_backend import SimulationArmBackend as _Base
    _HAVE_PLR = True
except ImportError:                       # pragma: no cover - exercised in CI
    _Base = object
    _HAVE_PLR = False


class ZeonBridgeUnavailable(RuntimeError):
    """pylabrobot + plr-lab-robot aren't installed, so the Zeon backend can't run."""


class ZeonArmBackend(_Base):
    """A PyLabRobot SCARA arm backend that targets Zeon's platform.

    Runs in simulation today (inherits SimulationArmBackend); on-site, fill the
    marked seams with the real Zeon SDK. N_JOINTS = 5.
    """

    def __init__(self, *args, sdk=None, host: str | None = None,
                 speed_cap: float = 0.5, **kwargs):
        if not _HAVE_PLR:
            raise ZeonBridgeUnavailable(
                "pylabrobot + plr-lab-robot required: pip install -e ../plr-lab-robot")
        super().__init__(*args, **kwargs)
        self.sdk = sdk                # real Zeon client, injected on-site
        self.host = host
        self.speed_cap = speed_cap    # keep motion gentle for a live demo
        self.zeon_calls: list[tuple] = []

    def _seam(self, name: str, *info) -> None:
        self.zeon_calls.append((name, *info))

    # --- motion primitives: log the Zeon seam, then run the sim fallback -------
    async def home(self):
        self._seam("home")                       # TODO: self.sdk.home()
        return await super().home()

    async def move_to(self, *a, **k):
        self._seam("move_to")                    # TODO: self.sdk.move_cartesian(pose, speed=self.speed_cap)
        return await super().move_to(*a, **k)

    async def approach(self, *a, **k):
        self._seam("approach")                   # TODO: self.sdk.approach(pose, access)
        return await super().approach(*a, **k)

    async def pick_up_resource(self, *a, **k):
        self._seam("pick_up_resource")           # TODO: self.sdk.grip_plate(...)
        return await super().pick_up_resource(*a, **k)

    async def drop_resource(self, *a, **k):
        self._seam("drop_resource")              # TODO: self.sdk.release_plate(...)
        return await super().drop_resource(*a, **k)

    async def open_gripper(self, *a, **k):
        self._seam("open_gripper")               # TODO: self.sdk.gripper(open=True)
        return await super().open_gripper(*a, **k)

    async def close_gripper(self, *a, **k):
        self._seam("close_gripper")              # TODO: self.sdk.gripper(open=False)
        return await super().close_gripper(*a, **k)


def zeon_workcell(**backend_kwargs):
    """A plr_lr Workcell driven by ZeonArmBackend instead of the sim backend --
    the one-line swap that points the whole loop at Zeon's platform."""
    if not _HAVE_PLR:
        raise ZeonBridgeUnavailable("pylabrobot + plr-lab-robot required")
    from plr_lr import Workcell
    from pylabrobot.arms import ExperimentalSCARA
    return Workcell(arm=ExperimentalSCARA(backend=ZeonArmBackend(**backend_kwargs)))


def zeon_swap_selfcheck() -> dict:
    """Prove the backend swap RUNS: build a Workcell on ZeonArmBackend and move a
    plate between two taught sites in sim (no hardware). Returns the Zeon-SDK seams
    that fired -- exactly the calls to wire to the real SDK on-site."""
    if not _HAVE_PLR:
        raise ZeonBridgeUnavailable("pylabrobot + plr-lab-robot required")
    from plr_lr import Labware

    async def _go():
        wc = zeon_workcell()
        await wc.setup()
        plate = Labware(name="assay_plate")
        wc.add_site("reader_out", x=180, y=0, z=12, occupant=plate)
        wc.add_site("reader_in", x=-180, y=40, z=12)
        with contextlib.redirect_stdout(io.StringIO()):
            await wc.move_plate("reader_out", "reader_in")
        be = wc.backend
        return {
            "passed": wc.world.sites["reader_in"].occupant is not None,
            "backend": type(be).__name__,
            "commands": len(be.trace),
            "zeon_calls": len(be.zeon_calls),
            "seams": sorted({c[0] for c in be.zeon_calls}),
        }

    return asyncio.run(_go())
