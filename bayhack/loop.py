"""bay-hack DBTL orchestrator -- the glue that composes @di-omics repos.

This is NOT a reimplementation of your stack. It is the thin cross-repo loop
that none of the individual repos owns: it wires your planner, world model,
MCP execution, physical validation, and conformal gate into ONE Track-A run.

Every stage has a SEAM comment naming the real module to swap in on your
machine (where those repos are installed). Out of the box this file runs a
stdlib-only simulation so you can feel the whole loop tonight:

    python -m bayhack.loop

The loop:  Design (world model proposes) -> Build/Test (MCP executes + reads)
           -> Verify (Rhodamine gate + CV checkpoint) -> Learn (conformal gate
           + surrogate update) -> repeat, until it recovers a planted optimum.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN — the world model proposes the next experiment
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

    def propose(self, grid: int = 101) -> float:
        best_x, best_ucb = 0.5, -1e9
        for i in range(grid):
            x = i / (grid - 1)
            mean, unc = self.predict(x)
            ucb = mean + self.kappa * unc
            if ucb > best_ucb:
                best_ucb, best_x = ucb, x
        return best_x

    def best(self) -> tuple[float, float]:
        i = max(range(len(self.ys)), key=lambda k: self.ys[k])
        return self.xs[i], self.ys[i]


# ─────────────────────────────────────────────────────────────────────────────
# BUILD / TEST — execute the design on the bench and read it out
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

    def true_response(self, x: float) -> float:
        return math.exp(-((x - self.x_star) / self.width) ** 2)

    def run_design(self, x: float) -> float:
        """Execute one experiment, return a fluorescence reading (0..1)."""
        # SEAM: agent calls plr_transfer to build the reaction at ratio x,
        #       then plr_read_plate to measure fluorescence.
        signal = self.true_response(x) * (1 - self.pipetting_bias)
        return max(0.0, signal + self.rng.uniform(-self.noise, self.noise))

    def rhodamine_series(self) -> list[tuple[float, float]]:
        """A Rhodamine-B dispense ladder: (commanded_uL, measured_signal)."""
        # SEAM: real dispense series read on the plate reader.
        out = []
        for v in (2.0, 5.0, 10.0, 20.0, 50.0):
            actual = v * (1 - self.pipetting_bias) * (1 + self.rng.uniform(-0.01, 0.01))
            out.append((v, 12.5 * actual))       # reader counts ∝ volume
        return out


# ─────────────────────────────────────────────────────────────────────────────
# VERIFY — did the robot dispense what the code said? did the step execute?
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
# LEARN — decide accept / escalate, then update the world model
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
    x: float
    fluor: float
    r2: float
    decision: str
    best_x: float
    best_y: float


class DBTLLoop:
    """Design-Build-Test-Learn, composed across the repos, with a QC gate."""

    def __init__(self, bench: Bench | None = None, tol: float = 0.03, budget: int = 20,
                 rhodamine_fn=None, cv_fn=None):
        self.bench = bench or Bench()
        self.wm = WorldModel()
        self.tol = tol
        self.budget = budget
        # SEAM hooks: default to the stdlib gates; bayhack.seams swaps in the real
        # tipseq_plr Rhodamine + SimVision gates. Both take the same call shape.
        self.rhodamine_fn = rhodamine_fn or rhodamine_gate
        self.cv_fn = cv_fn or cv_checkpoint
        self.history: list[RoundLog] = []
        self.runs_used: int = 0

    def run(self, verbose: bool = True) -> list[RoundLog]:
        # seed with two spread-out probes so the surrogate isn't blind
        for x0 in (0.2, 0.8):
            self.wm.observe(x0, self.bench.run_design(x0))

        for k in range(1, self.budget + 1):
            # DESIGN
            x = self.wm.propose()
            # BUILD / TEST
            fluor = self.bench.run_design(x)
            # VERIFY
            rhod = self.rhodamine_fn(self.bench.rhodamine_series())
            cv = self.cv_fn(fault=False)
            trustworthy = rhod["passed"] and cv["passed"]
            # LEARN — a physically trustworthy measurement always trains the
            # world model; the conformal gate decides promote vs. escalate.
            if trustworthy:
                self.wm.observe(x, fluor)
            _, unc = self.wm.predict(x)
            decision = conformal_gate(unc) if trustworthy else "ESCALATE"
            bx, by = self.wm.best()
            self.history.append(RoundLog(k, x, fluor, rhod["r2"], decision, bx, by))

            if verbose:
                print(f"[R{k:02d}] propose x={x:.3f}  fluor={fluor:.3f}  "
                      f"Rhodamine R²={rhod['r2']:.4f} {'PASS' if rhod['passed'] else 'FAIL'}  "
                      f"CV:{'ok' if cv['passed'] else 'FAULT'}  gate:{decision}  "
                      f"best x={bx:.3f}")

            # converged only when the model is BOTH accurate and confident
            # (a promoted result), not merely lucky on one reading.
            if abs(bx - self.bench.x_star) <= self.tol and decision == "ACCEPT":
                self.runs_used = k + 2   # + 2 seed probes
                return self.history

        self.runs_used = self.budget + 2
        return self.history
