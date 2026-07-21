"""Benchmark tests -- stdlib only, run in CI. Lock the pitch numbers + the chart."""
from bayhack.benchmark import run_benchmark, convergence_svg


def test_world_model_beats_the_grid():
    r = run_benchmark(seeds=range(1, 11))
    assert r["converged"] == r["n_seeds"]        # every seed converges
    assert r["avg_runs"] < r["grid"]             # fewer runs than a grid sweep
    assert r["speedup_vs_grid"] > 1
    assert r["avg_x_error"] < 0.03               # lands on the optimum
    assert r["reaction_volume_saved_ul"] > 0
    assert r["tips_saved"] > 0


def test_convergence_svg_is_well_formed():
    s = convergence_svg(seed=7)
    assert s.startswith("<svg") and "</svg>" in s
    assert "polyline" in s                       # the best-so-far curve
    assert "#5cae5a" in s                        # house matcha graphics
