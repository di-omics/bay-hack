"""benchmark.py -- the numbers behind the pitch. Stdlib-first, deterministic.

    python -m bayhack.benchmark

Reports, across many seeds:
  1. runs-to-target vs a ~26-point grid sweep (the world-model efficiency claim),
  2. convergence rate + accuracy of the recovered optimum,
  3. (optional) the real split-conformal coverage from ml-bio-eval, if installed.

It also writes a dependency-free SVG convergence chart (docs/convergence.svg) that
the README embeds.
"""
from __future__ import annotations

import random

from .loop import DBTLLoop, Bench

GRID = 26  # a 1-knob exhaustive sweep, for contrast


def run_benchmark(seeds=range(1, 31)) -> dict:
    seeds = list(seeds)
    runs, errs, converged = [], [], 0
    for s in seeds:
        loop = DBTLLoop(Bench(rng=random.Random(s)), tol=0.03, budget=25)
        loop.run(verbose=False)
        bx, _ = loop.wm.best()
        err = abs(bx - loop.bench.x_star)
        if err <= loop.tol:
            converged += 1
        runs.append(loop.runs_used)
        errs.append(err)
    n = len(seeds)
    return {
        "n_seeds": n,
        "grid": GRID,
        "avg_runs": round(sum(runs) / n, 2),
        "max_runs": max(runs),
        "converged": converged,
        "convergence_rate": round(converged / n, 3),
        "avg_x_error": round(sum(errs) / n, 4),
        "speedup_vs_grid": round(GRID / (sum(runs) / n), 1),
    }


def real_conformal_coverage(seed: int = 0) -> dict | None:
    """The real split-conformal coverage from ml-bio-eval, if it's importable."""
    try:
        from .seams import real_world_model_run
        return real_world_model_run(n_iter=30, seed=seed)
    except Exception:
        return None


def convergence_svg(seed: int = 7) -> str:
    """A dep-free matcha convergence chart: best-so-far fluorescence per round,
    with each proposed experiment as a dot. Text uses ink/matcha-deep; bright
    matcha is graphics only (the house contrast rule)."""
    loop = DBTLLoop(Bench(rng=random.Random(seed)), tol=0.03, budget=25)
    hist = loop.run(verbose=False)
    W, H, pad = 560, 280, 46
    n = len(hist)
    X = lambda i: pad + (W - 2 * pad) * (0.5 if n < 2 else i / (n - 1))
    Y = lambda v: H - pad - (H - 2 * pad) * max(0.0, min(1.0, v))
    best_line = " ".join(f"{X(i):.1f},{Y(r.best_y):.1f}" for i, r in enumerate(hist))
    proposed = "".join(
        f'<circle cx="{X(i):.1f}" cy="{Y(r.fluor):.1f}" r="3.6" fill="#c9d8f2" '
        f'stroke="#2f6fd6" stroke-width="1"/>' for i, r in enumerate(hist))
    best_dots = "".join(
        f'<circle cx="{X(i):.1f}" cy="{Y(r.best_y):.1f}" r="3.4" fill="#3c8446"/>'
        for i, r in enumerate(hist))
    gy = [0.0, 0.25, 0.5, 0.75, 1.0]
    grid = "".join(
        f'<line x1="{pad}" y1="{Y(v):.1f}" x2="{W - pad}" y2="{Y(v):.1f}" '
        f'stroke="#e6efe8" stroke-width="1"/>'
        f'<text x="{pad - 8}" y="{Y(v) + 3:.1f}" fill="#6f8274" font-size="10" '
        f'text-anchor="end" font-family="monospace">{v:.2f}</text>' for v in gy)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Manrope,system-ui,sans-serif">
<rect width="{W}" height="{H}" fill="#ffffff"/>
<text x="{pad}" y="26" fill="#3c8446" font-size="12" font-weight="800" letter-spacing="1.5">BAY-HACK &#183; CONVERGENCE</text>
<text x="{pad}" y="42" fill="#28372a" font-size="13" font-weight="800">World model recovers the optimum in {loop.runs_used} runs &#8212; vs ~{GRID} for a grid sweep</text>
{grid}
<line x1="{pad}" y1="{Y(1):.1f}" x2="{W - pad}" y2="{Y(1):.1f}" stroke="#9db8a0" stroke-dasharray="5 4" stroke-width="1.3"/>
<polyline points="{best_line}" fill="none" stroke="#5cae5a" stroke-width="2.6"/>
{proposed}{best_dots}
<text x="{W - pad}" y="{H - 14}" fill="#6f8274" font-size="10" text-anchor="end" font-family="monospace">round &#8594;</text>
<text x="{pad}" y="{H - 14}" fill="#3c8446" font-size="10" font-family="monospace" font-weight="600">best-so-far (line) &#183; proposed (dots)</text>
</svg>"""


def save_chart(path: str = "docs/convergence.svg", seed: int = 7) -> str:
    svg = convergence_svg(seed)
    with open(path, "w") as f:
        f.write(svg)
    return path


def main():
    r = run_benchmark()
    print("\nBAY-HACK benchmark  (world model vs grid sweep)")
    print("=" * 56)
    print(f"  seeds evaluated      : {r['n_seeds']}")
    print(f"  avg runs to optimum  : {r['avg_runs']}  (max {r['max_runs']})")
    print(f"  grid-sweep baseline  : {r['grid']} runs")
    print(f"  speedup vs grid      : {r['speedup_vs_grid']}x")
    print(f"  convergence rate     : {r['convergence_rate'] * 100:.0f}%  "
          f"({r['converged']}/{r['n_seeds']})")
    print(f"  avg |x - x*|         : {r['avg_x_error']}")
    cov = real_conformal_coverage()
    if cov:
        print("-" * 56)
        print(f"  real conformal gate  : coverage {cov['empirical_coverage']} "
              f"(target {1 - cov['alpha']:.2f})")
        print(f"  runs to first pass   : {cov['runs_to_first_pass']}")
    print("=" * 56)
    path = save_chart()
    print(f"  wrote convergence chart -> {path}")


if __name__ == "__main__":
    main()
