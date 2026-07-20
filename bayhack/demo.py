"""Runnable end-to-end demo of the bay-hack loop (pure simulation).

    python -m bayhack.demo

Narrates one Track-A run: a world model proposes experiments, an agent executes
them (MCP seam), Rhodamine + CV verify them physically, a conformal gate decides,
and it recovers a planted optimum in far fewer runs than a grid sweep.
"""
from __future__ import annotations

from .loop import DBTLLoop, Bench


def main():
    print("=" * 68)
    print("bay-hack — a world model runs the bench   (simulation)")
    print("Design → Build/Test (MCP) → Verify (Rhodamine + CV) → Learn (conformal)")
    print("=" * 68 + "\n")

    loop = DBTLLoop(Bench(), tol=0.03, budget=20)
    loop.run(verbose=True)

    bx, by = loop.wm.best()
    hit = abs(bx - loop.bench.x_star) <= loop.tol
    grid = 26   # a 1-knob exhaustive sweep, for contrast
    print()
    if hit:
        print(f"✓ recovered optimum x*≈{loop.bench.x_star:.2f} at x={bx:.3f} "
              f"(fluor {by:.3f}) in {loop.runs_used} runs — vs ~{grid} for a grid sweep.")
    else:
        print(f"best x={bx:.3f} (target {loop.bench.x_star:.2f}) after {loop.runs_used} runs.")

    print("\nEvery stage above is a SEAM to a real @di-omics repo:")
    print("  Design  → ml-bio-eval/lab-world-model (GP + ParEGO)")
    print("  Execute → plr-mcp (plr_transfer, plr_read_plate)")
    print("  Verify  → plr-epigenome validation/rhodamine.py + lab-cv")
    print("  Learn   → ml-bio-eval split-conformal accept/escalate gate")
    print("Swap them in on your machine, then swap the arm backend for")
    print("ZeonArmBackend (zeon_bridge.py) to drive Zeon's platform.")


if __name__ == "__main__":
    main()
