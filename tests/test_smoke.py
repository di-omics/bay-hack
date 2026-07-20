"""Smoke tests — the CI gate. Deterministic, stdlib-only, fast."""
from bayhack import (
    DBTLLoop, Bench, WorldModel, rhodamine_gate, cv_checkpoint, conformal_gate,
)


def test_version():
    import bayhack
    assert bayhack.__version__


def test_loop_recovers_planted_optimum():
    loop = DBTLLoop(Bench(x_star=0.62), tol=0.03, budget=25)
    loop.run(verbose=False)
    bx, _ = loop.wm.best()
    assert abs(bx - 0.62) <= 0.05, f"world model missed the optimum: {bx}"


def test_loop_beats_grid_on_runs():
    loop = DBTLLoop(Bench(x_star=0.62), tol=0.03, budget=25)
    loop.run(verbose=False)
    assert loop.runs_used < 26, "should recover in fewer runs than a 26-pt grid"


def test_rhodamine_gate_passes_linear_series():
    series = [(v, 12.5 * v) for v in (2, 5, 10, 20, 50)]
    assert rhodamine_gate(series)["passed"]


def test_rhodamine_gate_fails_nonlinear_series():
    series = [(2, 1), (5, 30), (10, 32), (20, 33), (50, 200)]
    assert not rhodamine_gate(series)["passed"]


def test_cv_checkpoint_flags_fault():
    assert cv_checkpoint(fault=False)["passed"]
    assert not cv_checkpoint(fault=True)["passed"]


def test_conformal_gate_labels():
    assert conformal_gate(0.1) == "ACCEPT"
    assert conformal_gate(0.7) == "ESCALATE"
    assert conformal_gate(0.95) == "REJECT"
