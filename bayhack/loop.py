"""bay-hack DBTL orchestrator -- the glue that composes @di-omics repos.

This is NOT a reimplementation of your stack. It is the thin cross-repo loop
that none of the individual repos owns: it wires your planner, world model,
MCP execution, physical validation, and conformal gate into ONE Track-A run.

Every stage has a SEAM comment naming the real module to swap in on your
machine (where those repos are installed). Out of the box this file runs a
stdlib-only simulation so you can feel the whole loop tonight:

    python -m bayhack.loop

The loop:  Design (world model proposes) -> Build/Test (MCP executes + reads)
           -> Verify (Rhodamine gate + CV checkpoint) -> Learn (objective plus
           uncertainty gate + surrogate update) -> repeat, then follow up.

The simulator exposes a planted optimum only to benchmark scoring. The
controller stops without reading it.
"""
from __future__ import annotations

import inspect
import math
import random
from dataclasses import dataclass, field

from .assay import FollowUpAction, LiquidHandlingAssay, LiquidHandlingPlan
from .ledger import TrustLedger


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN: the world model proposes the next experiment
#   SEAM: replace WorldModel with ml-bio-eval/lab-world-model
#         (GP surrogate + multi-objective Bayesian optimization, ParEGO).
# ─────────────────────────────────────────────────────────────────────────────
class WorldModel:
    """A tiny GP-lite surrogate over a 1-D design x in [0, 1].

    Predicts mean + uncertainty by Gaussian-kernel weighting of observations,
    and proposes the next x by UCB (mean + kappa * uncertainty). Stand-in for
    the real GP + ParEGO acquisition in ml-bio-eval/lab-world-model.
    """

    def __init__(self, lengthscale: float = 0.12, kappa: float = 0.9):
        self.ls = lengthscale
        self.kappa = kappa
        self.xs: list[float] = []
        self.ys: list[float] = []

    def observe(self, x: float, y: float) -> None:
        self.xs.append(x)
        self.ys.append(y)

    def predict(self, x: float) -> tuple[float, float]:
        if not self.xs:
            return 0.0, 1.0
        ws = [math.exp(-((x - xi) / self.ls) ** 2) for xi in self.xs]
        wsum = sum(ws)
        mean = sum(w * y for w, y in zip(ws, self.ys)) / (wsum + 1e-9)
        unc = 1.0 / math.sqrt(1.0 + wsum)           # ->1 when sparse, ->0 when dense
        return mean, min(unc, 1.0)

    def propose(self, grid: int = 101, feasible_fn=None) -> float:
        best_x, best_ucb = 0.5, -1e9
        for i in range(grid):
            x = i / (grid - 1)
            if feasible_fn is not None and not feasible_fn(x):
                continue
            mean, unc = self.predict(x)
            ucb = mean + self.kappa * unc
            if ucb > best_ucb:
                best_ucb, best_x = ucb, x
        return best_x

    def best(self) -> tuple[float, float]:
        i = max(range(len(self.ys)), key=lambda k: self.ys[k])
        return self.xs[i], self.ys[i]


# ─────────────────────────────────────────────────────────────────────────────
# BUILD / TEST: execute the design on the bench and read it out
#   SEAM: replace Bench with plr-mcp tools:
#         plr_setup_deck -> plr_transfer(...) -> plr_read_plate(mode="fluorescence")
#         and plr-lab-robot Workcell.move_plate / vision_guided_pick / DecapSkill.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Bench:
    """Simulated liquid handler + fluorescence reader with realistic error.

    `pipetting_bias` makes reality diverge from the naive model, which is the
    whole reason you need measurement + a validation gate. On your machine this
    class becomes calls into the plr-mcp server (chatterbox, then `star`).
    """
    x_star: float = 0.62            # planted optimum (unknown to the loop)
    width: float = 0.16
    pipetting_bias: float = 0.06
    noise: float = 0.02
    rng: random.Random = field(default_factory=lambda: random.Random(7))
    backend_name: str = "stdlib-simulation"
    measurement_provenance: str = "modeled"
    verification_provenance: str = "modeled"
    executed_plans: list[LiquidHandlingPlan] = field(default_factory=list)
    executed_follow_ups: list[FollowUpAction] = field(default_factory=list)

    def true_response(self, x: float) -> float:
        return math.exp(-((x - self.x_star) / self.width) ** 2)

    def run_design(self, x: float) -> float:
        """Execute one experiment, return a fluorescence reading (0..1)."""
        # SEAM: agent calls plr_transfer to build the reaction at ratio x,
        #       then plr_read_plate to measure fluorescence.
        signal = self.true_response(x) * (1 - self.pipetting_bias)
        return max(0.0, signal + self.rng.uniform(-self.noise, self.noise))

    def run_plan(self, plan: LiquidHandlingPlan) -> float:
        """Execute a verified liquid-handling plan in simulation."""
        self.executed_plans.append(plan)
        return self.run_design(plan.design_x)

    def run_follow_up(self, action: FollowUpAction) -> bool:
        """Stage the accepted well for the downstream step in simulation."""
        self.executed_follow_ups.append(action)
        return True

    def rhodamine_series(self) -> list[tuple[float, float]]:
        """A Rhodamine-B dispense ladder: (commanded_uL, measured_signal)."""
        # SEAM: real dispense series read on the plate reader.
        out = []
        for v in (2.0, 5.0, 10.0, 20.0, 50.0):
            actual = v * (1 - self.pipetting_bias) * (1 + self.rng.uniform(-0.01, 0.01))
            out.append((v, 12.5 * actual))       # reader counts ∝ volume
        return out


# ─────────────────────────────────────────────────────────────────────────────
# VERIFY: did the robot dispense what the code said? did the step execute?
#   SEAM: replace with plr-epigenome tipseq_plr/validation/rhodamine.py
#         and steps/vision.py (SimVision / LabCvVision backed by lab-cv).
# ─────────────────────────────────────────────────────────────────────────────
def rhodamine_gate(series: list[tuple[float, float]], r2_min: float = 0.995) -> dict:
    """Linear-fit R^2 on the volume->signal ladder. Proof the VOLUMES are real."""
    n = len(series)
    xs = [v for v, _ in series]
    ys = [s for _, s in series]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    ss_res = sum((y - (my + slope * (x - mx))) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys) + 1e-12
    r2 = 1 - ss_res / ss_tot
    return {"passed": r2 >= r2_min, "r2": r2}


def cv_checkpoint(fault: bool = False) -> dict:
    """In-process CV guard (bead pellet formed, tips present, no spill)."""
    return {"passed": not fault, "note": "bead pellet formed" if not fault else "FAULT: bead loss"}


# ─────────────────────────────────────────────────────────────────────────────
# LEARN: decide accept / escalate, then update the world model
#   SEAM: replace with ml-bio-eval split-conformal accept/reject/escalate gate.
# ─────────────────────────────────────────────────────────────────────────────
def conformal_gate(uncertainty: float, accept_below: float = 0.55,
                   escalate_below: float = 0.85) -> str:
    if uncertainty < accept_below:
        return "ACCEPT"
    if uncertainty < escalate_below:
        return "ESCALATE"      # send to the bench / a human
    return "REJECT"


@dataclass
class RoundLog:
    k: int
    phase: str
    x: float
    fluor: float
    r2: float
    decision: str
    best_x: float
    best_y: float
    destination: str
    stock_ul: float
    diluent_ul: float
    plan_verified: bool
    measurement_provenance: str
    model_updated: bool
    uncertainty: float
    target_signal: float
    target_met: bool
    conformal_decision: str


class DBTLLoop:
    """Design-Build-Test-Learn, composed across the repos, with a QC gate."""

    def __init__(self, bench: Bench | None = None, tol: float = 0.03, budget: int = 20,
                 rhodamine_fn=None, cv_fn=None, assay: LiquidHandlingAssay | None = None,
                 target_signal: float = 0.85):
        self.bench = bench or Bench()
        self.wm = WorldModel()
        self.tol = tol
        self.budget = budget
        self.target_signal = target_signal
        self.assay = assay or LiquidHandlingAssay()
        # SEAM hooks: default to the stdlib gates; bayhack.seams swaps in the real
        # tipseq_plr Rhodamine + SimVision gates. Both take the same call shape.
        self.rhodamine_fn = rhodamine_fn or rhodamine_gate
        self.cv_fn = cv_fn or cv_checkpoint
        self.history: list[RoundLog] = []
        self.runs_used: int = 0
        self.follow_up: dict | None = None
        self.ledger = TrustLedger()

    @property
    def backend_name(self) -> str:
        return str(getattr(self.bench, "backend_name", type(self.bench).__name__))

    @property
    def measurement_provenance(self) -> str:
        return str(getattr(self.bench, "measurement_provenance", "modeled"))

    @property
    def verification_provenance(self) -> str:
        return str(getattr(self.bench, "verification_provenance", "modeled"))

    @property
    def measurement_evidence(self) -> dict:
        evidence = getattr(self.bench, "measurement_evidence", {})
        return dict(evidence) if isinstance(evidence, dict) else {
            "detail": str(evidence)
        }

    @staticmethod
    def _gate_call(function, *args, plan: LiquidHandlingPlan) -> dict:
        """Pass plan context to new adapters without breaking old gate callables."""
        try:
            parameters = inspect.signature(function).parameters.values()
            accepts_plan = any(
                parameter.name == "plan"
                or parameter.kind == inspect.Parameter.VAR_KEYWORD
                for parameter in parameters
            )
        except (TypeError, ValueError):
            accepts_plan = False
        result = function(*args, plan=plan) if accepts_plan else function(*args)
        if not isinstance(result, dict) or "passed" not in result:
            raise ValueError("physical gate must return a dict with passed")
        return result

    def _physical_verification_provenance(self, rhodamine: dict, cv: dict) -> str:
        """Promote evidence only when both measured physical gates exist."""
        labels = [str(rhodamine.get("provenance", "")),
                  str(cv.get("provenance", ""))]
        measured = [label.startswith("measured:") for label in labels]
        if all(measured):
            if rhodamine["passed"] and cv["passed"]:
                return "hardware-validated"
            return "measured:failed-physical-gates"
        if any(measured):
            return "measured:partial-physical-gates"
        fallback = self.verification_provenance
        return "unverified" if fallback == "hardware-validated" else fallback

    def _run_plan(self, plan: LiquidHandlingPlan) -> float:
        runner = getattr(self.bench, "run_plan", None)
        if callable(runner):
            return float(runner(plan))
        return float(self.bench.run_design(plan.design_x))

    def _execute_round(self, run_id: int, phase: str, x: float) -> RoundLog:
        plan = self.assay.plan(run_id, phase, x)
        plan_verification = self.assay.verify(plan)
        if not plan_verification["passed"]:
            raise ValueError(
                "world-model proposal failed physical plan verification: "
                + "; ".join(plan_verification["reasons"])
            )

        fluor = self._run_plan(plan)
        rhod = self._gate_call(
            self.rhodamine_fn,
            self.bench.rhodamine_series(),
            plan=plan,
        )
        cv = self._gate_call(self.cv_fn, False, plan=plan)
        trustworthy = rhod["passed"] and cv["passed"]
        if trustworthy:
            self.wm.observe(x, fluor)
        _, unc = self.wm.predict(x)
        bx, by = self.wm.best() if self.wm.ys else (x, 0.0)
        conformal_decision = conformal_gate(unc) if trustworthy else "ESCALATE"
        target_met = trustworthy and by >= self.target_signal
        decision = (
            "ACCEPT"
            if conformal_decision == "ACCEPT" and target_met
            else "ESCALATE"
        )
        record = RoundLog(
            k=run_id,
            phase=phase,
            x=x,
            fluor=fluor,
            r2=rhod["r2"],
            decision=decision,
            best_x=bx,
            best_y=by,
            destination=plan.destination,
            stock_ul=plan.stock_ul,
            diluent_ul=plan.diluent_ul,
            plan_verified=True,
            measurement_provenance=self.measurement_provenance,
            model_updated=trustworthy,
            uncertainty=unc,
            target_signal=self.target_signal,
            target_met=target_met,
            conformal_decision=conformal_decision,
        )
        self.history.append(record)
        self.ledger.append_round(
            plan=plan,
            plan_verification=plan_verification,
            backend=self.backend_name,
            measurement_value=fluor,
            measurement_provenance=self.measurement_provenance,
            measurement_evidence=self.measurement_evidence,
            rhodamine=rhod,
            cv=cv,
            verification_provenance=self._physical_verification_provenance(
                rhod, cv
            ),
            decision=decision,
            best_x=bx,
            best_y=by,
            model_updated=trustworthy,
            uncertainty=unc,
            target_signal=self.target_signal,
            target_met=target_met,
            conformal_decision=conformal_decision,
        )
        return record

    def _stage_follow_up(self) -> None:
        best_record = max(self.history, key=lambda record: record.fluor)
        accepted_plan = self.assay.plan(
            best_record.k, best_record.phase, best_record.x
        )
        action = self.assay.follow_up(accepted_plan)
        verification = action.verify(
            available_ul=accepted_plan.total_volume_ul,
            product_well=self.assay.product_well,
        )
        executed = False
        if verification["passed"]:
            runner = getattr(self.bench, "run_follow_up", None)
            executed = bool(runner(action)) if callable(runner) else True
        self.follow_up = {
            "action": action.to_dict(),
            "verification": verification,
            "executed": executed,
        }
        self.ledger.append_follow_up(
            action,
            verification,
            executed,
            self.backend_name,
        )

    def run(self, verbose: bool = True) -> list[RoundLog]:
        if self.budget < 3:
            raise ValueError("budget must allow two seed runs and one proposal")
        if self.history:
            raise RuntimeError("a DBTLLoop instance can only be run once")

        # Seed experiments are real experiments. They pass the same physical
        # gates and appear in the ledger before they can train the world model.
        for x0 in (0.2, 0.8):
            record = self._execute_round(len(self.history) + 1, "seed", x0)
            if verbose:
                self._print_round(record)

        while len(self.history) < self.budget:
            next_run_id = len(self.history) + 1

            def feasible(candidate: float) -> bool:
                candidate_plan = self.assay.plan(next_run_id, "optimize", candidate)
                return bool(self.assay.verify(candidate_plan)["passed"])

            record = self._execute_round(
                next_run_id,
                "optimize",
                self.wm.propose(feasible_fn=feasible),
            )
            if verbose:
                self._print_round(record)

            if record.decision == "ACCEPT":
                self.runs_used = len(self.history)
                self._stage_follow_up()
                return self.history

        self.runs_used = len(self.history)
        return self.history

    @staticmethod
    def _print_round(record: RoundLog) -> None:
        print(
            f"[R{record.k:02d} {record.phase:8s}] {record.destination}  "
            f"stock={record.stock_ul:5.1f}uL  diluent={record.diluent_ul:5.1f}uL  "
            f"x={record.x:.3f}  signal={record.fluor:.3f}  "
            f"Rhodamine R2={record.r2:.4f}  plan:PASS  "
            f"target:{'PASS' if record.target_met else 'WAIT'}  "
            f"gate:{record.decision}  best x={record.best_x:.3f}"
        )
