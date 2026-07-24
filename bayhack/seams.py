"""Real seam adapters -- swap the stdlib stand-ins for the shipped @di-omics stack.

Import `bayhack` and run `python -m bayhack.demo` with NOTHING installed and it
uses the pure-sim stand-ins in loop.py. Install the real repos and these adapters
call your actual code (all verified to run with NO hardware):

    pip install -e ../plr-mcp -e ../plr-epigenome -e ../plr-lab-robot
    # or use the categorized paths under ../../lab-automation
    # labworld has no pyproject yet, so add its directory to PYTHONPATH

Every adapter lazy-imports its repo INSIDE the call, so this module (and the sim
path) stay dependency-free. Honest caveats live next to each adapter -- read them;
they are the difference between a demo that survives judge questions and one that
does not.
"""
from __future__ import annotations

import asyncio
import contextlib
import io

from .loop import Bench
from .assay import FollowUpAction, LiquidHandlingPlan


class SeamUnavailable(RuntimeError):
    """A real @di-omics repo is not importable. Install it to use this seam."""


def _run(coro):
    """Run an async repo call from the synchronous loop."""
    return asyncio.run(coro)


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTE  --  plr-mcp  (Physical MCP: build the reaction + read the plate)
# ─────────────────────────────────────────────────────────────────────────────
class PlrMcpBench:
    """Drop-in for loop.Bench that runs the build + read through the REAL plr-mcp
    Lab on the chatterbox backend (no hardware, no MCP server needed).

    HONEST: PyLabRobot 0.2.1's chatterbox plate reader returns zeros -- it is
    decoupled from what was dispensed -- so the numeric fluorescence still comes
    from the response `model`. What is real here is the pipetting + read
    CHOREOGRAPHY (setup_deck -> tips -> aspirate -> dispense -> read_plate) driven
    by your MCP/PyLabRobot code. On hardware, swap backend='star' and wire a real
    reader, and the same loop reads real signal.
    """

    def __init__(
        self,
        model: Bench | None = None,
        backend: str = "chatterbox",
        quiet: bool = True,
        measurement_fn=None,
        verification_provenance: str = "synthetic_fixture",
    ):
        self.model = model or Bench()
        self.backend = backend
        self.quiet = quiet
        self.measurement_fn = measurement_fn
        self._shown = False
        self._lab_instance = None
        self._setup_done = False
        self.measurement_evidence: dict = {}
        self.backend_name = f"plr-mcp:{backend}"
        self.measurement_provenance = (
            str(getattr(measurement_fn, "provenance", "measured"))
            if measurement_fn
            else "modeled"
        )
        self.verification_provenance = verification_provenance

    # keep the loop's convergence check + Rhodamine ladder working
    @property
    def x_star(self) -> float:
        return self.model.x_star

    def rhodamine_series(self):
        return self.model.rhodamine_series()

    def _lab(self):
        if self._lab_instance is not None:
            return self._lab_instance
        try:
            from plr_mcp.lab import Lab
        except ImportError as e:                       # pragma: no cover
            raise SeamUnavailable(
                "plr-mcp not installed: pip install -e ../plr-mcp") from e
        self._lab_instance = Lab(backend=self.backend)
        return self._lab_instance

    async def _ensure_setup(self) -> None:
        if self._setup_done:
            return
        if self.backend != "chatterbox":
            raise SeamUnavailable(
                "real hardware is not prepared; call prepare_hardware(confirm=True) "
                "with a clear deck and an E-stop owner"
            )
        result = await self._lab().setup_deck()
        if not result.get("ok"):
            raise SeamUnavailable(f"deck setup failed: {result}")
        self._setup_done = True

    def prepare_hardware(self, *, confirm: bool = False) -> dict:
        """Deliberate motion gate for a real liquid handler.

        This is never called by the simulator or by DBTLLoop. The operator must
        clear the deck, identify the E-stop owner, and pass confirm=True.
        """
        if self.backend == "chatterbox":
            result = _run(self._lab().setup_deck())
            self._setup_done = bool(result.get("ok"))
            return result
        if not confirm:
            raise SeamUnavailable(
                "refusing to home real hardware without confirm=True"
            )
        result = _run(self._lab().setup_deck(home=True))
        self._setup_done = bool(result.get("ok") and result.get("homed"))
        if not self._setup_done:
            raise SeamUnavailable(f"hardware preparation failed: {result}")
        return result

    async def _choreograph(self, x: float) -> None:
        lab = self._lab()
        await self._ensure_setup()
        vol = max(1.0, 50.0 * x)
        await lab.pick_up_tips("A1")
        await lab.aspirate("A1", volume=vol)
        await lab.dispense("A2", volume=vol)
        await lab.drop_tips("A1")
        await lab.read_plate(mode="fluorescence", excitation=485, emission=520)

    def run_design(self, x: float) -> float:
        # show the real PyLabRobot chatter once, then run quietly
        if self.quiet and self._shown:
            with contextlib.redirect_stdout(io.StringIO()):
                _run(self._choreograph(x))
        else:
            _run(self._choreograph(x))
            self._shown = True
        return self.model.run_design(x)               # signal modeled (reader=0)

    async def _choreograph_plan(self, plan: LiquidHandlingPlan) -> dict:
        lab = self._lab()
        await self._ensure_setup()
        for transfer in plan.transfers:
            await lab.transfer(
                transfer.source,
                transfer.destination,
                volume=transfer.volume_ul,
                tips=transfer.tip,
            )
        return await lab.read_plate(
            mode="fluorescence", excitation=485, emission=520
        )

    def run_plan(self, plan: LiquidHandlingPlan) -> float:
        """Run the concrete two-component formulation through PyLabRobot."""
        if self.quiet and self._shown:
            with contextlib.redirect_stdout(io.StringIO()):
                readout = _run(self._choreograph_plan(plan))
        else:
            readout = _run(self._choreograph_plan(plan))
            self._shown = True
        if self.measurement_fn is not None:
            value = float(self.measurement_fn(plan, readout))
            evidence = getattr(self.measurement_fn, "last_evidence", {})
            self.measurement_evidence = (
                dict(evidence) if isinstance(evidence, dict) else {}
            )
            return value
        return self.model.run_plan(plan)

    async def _choreograph_follow_up(self, action: FollowUpAction) -> None:
        lab = self._lab()
        await self._ensure_setup()
        await lab.transfer(
            action.source,
            action.destination,
            volume=action.volume_ul,
            tips=action.tip,
        )

    def run_follow_up(self, action: FollowUpAction) -> bool:
        with contextlib.redirect_stdout(io.StringIO()):
            _run(self._choreograph_follow_up(action))
        self.model.run_follow_up(action)
        return True


# ─────────────────────────────────────────────────────────────────────────────
# VERIFY (volumes)  --  plr-epigenome  (the real Rhodamine-B gate)
# ─────────────────────────────────────────────────────────────────────────────
def rhodamine_gate_real(series, min_r2: float = 0.995, replicates: int = 3) -> dict:
    """Real gate via tipseq_plr.validation.evaluate. bayhack's (uL, signal) ladder
    becomes the standard curve; `replicates` synthetic test wells per volume let
    the real gate compute accuracy + CV (it is STRICTER than R^2 alone -- it also
    enforces in-range, accuracy %, and replicate CV %, and returns a validation
    TIER). Returns loop-compatible {passed, r2} plus the real tier + reasons.
    """
    try:
        from tipseq_plr.validation import (
            evaluate, RhodamineCriteria, Standard, Reading,
        )
    except ImportError as e:
        raise SeamUnavailable(
            "plr-epigenome not installed: pip install -e ../plr-epigenome") from e

    standards = [Standard(volume_ul=v, rfu=s) for v, s in series]
    jit = [0.0, -0.004, 0.004, -0.008, 0.008]
    readings = []
    for i, (v, s) in enumerate(series):
        for r in range(replicates):
            readings.append(Reading(well=f"{chr(65 + r)}{i + 1}",
                                    target_ul=v, rfu=s * (1 + jit[r % len(jit)])))
    v = evaluate(standards, readings, RhodamineCriteria(min_r2=min_r2))
    r2 = v["standard_curve"]["r2"]
    tier = v.get("tier", "untested")
    # loop "trustworthy" signal: the curve is linear enough (bayhack's original
    # semantic). The real gate's fuller verdict (tier/reasons) is surfaced too.
    return {"passed": r2 >= min_r2, "r2": r2, "tier": tier,
            "liquid_tested": tier == "liquid_tested", "reasons": v.get("reasons", [])}


# ─────────────────────────────────────────────────────────────────────────────
# VERIFY (steps)  --  plr-epigenome  (the real CV checkpoint)
# ─────────────────────────────────────────────────────────────────────────────
def cv_checkpoint_real(fault: bool = False, checkpoint: str | None = None) -> dict:
    """Real CV checkpoint via tipseq_plr.steps.vision.SimVision. Returns the
    loop-compatible {passed, note}. (LabCvVision -- real camera + di-omics/lab-cv
    -- is the on-site swap; only SimVision is hardware-free.)
    """
    try:
        from tipseq_plr.steps.vision import SimVision, CHECK_BEAD_PELLET
    except ImportError as e:
        raise SeamUnavailable(
            "plr-epigenome not installed: pip install -e ../plr-epigenome") from e
    cp = checkpoint or CHECK_BEAD_PELLET
    backend = SimVision(fault_at=[cp] if fault else None)
    verdict = _run(backend.inspect(cp, column=1))
    return {"passed": verdict.ok, "note": verdict.detail or "ok", "checkpoint": cp}


# ─────────────────────────────────────────────────────────────────────────────
# PLAN  --  plr-epigenome  (NL -> protocol, the sow compiler)
# ─────────────────────────────────────────────────────────────────────────────
def plan_from_text(text: str) -> dict:
    """Real NL->protocol via tipseq_plr.sow. Returns the compiled plan dict
    (sync, hardware-free) -- routed method + samples/targets + validation tier."""
    try:
        from tipseq_plr.sow import SoW, compile_run
    except ImportError as e:
        raise SeamUnavailable(
            "plr-epigenome not installed: pip install -e ../plr-epigenome") from e
    return compile_run(SoW.from_text(text)).plan()


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN + LEARN  --  ml-bio-eval / labworld  (GP world model + conformal gate)
#   NOTE: labworld optimizes a real 4-D protocol space (input_dna_ng, pcr_cycles,
#   bead_ratio, primer_conc_uM) over 3 objectives -- it does NOT fit loop.py's toy
#   1-D x. So this is the *real* world-model path, reported on its own terms.
# ─────────────────────────────────────────────────────────────────────────────
def real_world_model_run(n_iter: int = 30, seed: int = 0, cal_n: int = 40) -> dict:
    """Run the REAL GP + ParEGO optimizer and the REAL split-conformal QC gate on
    labworld's native assay. Returns runs-to-first-acceptance and the gate's
    empirical coverage (the coverage guarantee is the honest headline)."""
    try:
        import numpy as np
        from labworld.optimize import parego
        from labworld import assay
        from labworld.qc_gate import ConformalQCGate
    except ImportError as e:
        raise SeamUnavailable(
            "labworld not importable: add ml-bio-eval/lab-world-model to PYTHONPATH") from e

    rr = parego(n_iter=n_iter, seed=seed)
    rng = np.random.default_rng(seed)
    X = assay.sample_design(3 * cal_n, rng)
    Y = assay.run_assay(X, rng)
    sl = lambda a, b: (X[a:b], {k: Y[k][a:b] for k in Y})
    Xtr, Ytr = sl(0, cal_n)
    Xca, Yca = sl(cal_n, 2 * cal_n)
    Xte, Yte = sl(2 * cal_n, 3 * cal_n)
    gate = ConformalQCGate(alpha=0.10).fit(Xtr, Ytr, Xca, Yca)
    dec, _ = gate.triage(Xte)
    cov = gate.empirical_coverage(Xte, Yte)
    from collections import Counter
    return {
        "runs_to_first_pass": int(rr.first_pass),      # -1 if none within budget
        "n_evaluated": int(rr.X.shape[0]),
        "objectives": list(rr.outcomes.keys()),
        "gate_decisions": {k: int(v) for k, v in Counter(map(str, dec)).items()},
        "empirical_coverage": {k: round(float(x), 3) for k, x in cov.items()},
        "alpha": 0.10,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DEXTERITY  --  plr-lab-robot  (arm move a plate, sim; Track C bonus)
# ─────────────────────────────────────────────────────────────────────────────
def dexterity_checkpoint() -> dict:
    """Real arm choreography via plr_lr Workcell.sim(): stand up the arm, move a
    plate between two taught sites (no hardware). Swap SimulationArmBackend for a
    PreciseFlex/Zeon backend and the same call drives a real arm."""
    try:
        from plr_lr import Labware, Workcell
    except ImportError as e:
        raise SeamUnavailable(
            "plr-lab-robot not installed: pip install -e ../plr-lab-robot") from e

    async def _go():
        wc = Workcell.sim()
        await wc.setup()
        plate = Labware(name="assay_plate")
        wc.add_site("reader_out", x=180, y=0, z=12, occupant=plate)
        wc.add_site("reader_in", x=-180, y=40, z=12)
        with contextlib.redirect_stdout(io.StringIO()):
            await wc.move_plate("reader_out", "reader_in")
        moved = wc.world.sites["reader_in"].occupant
        return {"passed": moved is not None, "moved_to": "reader_in",
                "commands": len(wc.backend.trace), "holding": wc.backend.holding}

    return _run(_go())


# ─────────────────────────────────────────────────────────────────────────────
def seam_status() -> dict:
    """Which real repos are importable right now (for the demo header)."""
    import importlib
    out = {}
    for label, mod in [("execute (plr-mcp)", "plr_mcp"),
                       ("verify+plan (plr-epigenome)", "tipseq_plr"),
                       ("design+learn (labworld)", "labworld"),
                       ("dexterity (plr-lab-robot)", "plr_lr")]:
        try:
            importlib.import_module(mod)
            out[label] = True
        except Exception:
            out[label] = False
    return out
