"""Runnable end-to-end demo of the bay-hack loop (pure simulation).

    python -m bayhack.demo

Narrates one Track-A run: a world model proposes experiments, an agent executes
them (MCP seam), Rhodamine + CV verify them physically, a conformal gate decides,
and it recovers a planted optimum in far fewer runs than a grid sweep.
"""
from __future__ import annotations

import argparse

from .loop import DBTLLoop, Bench


def real_demo():
    """Run the loop against the REAL @di-omics stack (no hardware). Each seam
    degrades gracefully to a note if its repo is not installed."""
    from . import seams
    status = seams.seam_status()
    print("=" * 68)
    print("bay-hack — a world model runs the bench   (REAL seams, no hardware)")
    print("=" * 68)
    for label, ok in status.items():
        print(f"  [{'x' if ok else ' '}] {label}")
    print()

    # BUILD/TEST + VERIFY through the real stack (short loop; chatterbox is loud).
    try:
        bench = seams.PlrMcpBench(quiet=True)
        loop = DBTLLoop(bench, tol=0.03, budget=6,
                        rhodamine_fn=seams.rhodamine_gate_real,
                        cv_fn=seams.cv_checkpoint_real)
        loop.run(verbose=True)
        bx, _ = loop.wm.best()
        print(f"\n[execute] plr-mcp chatterbox ran the build+read choreography "
              f"(real PyLabRobot; reader decoupled in sim, so signal is modeled).")
        print(f"[verify]  tipseq_plr Rhodamine gate + SimVision gated every round.")
    except seams.SeamUnavailable as e:
        print(f"[execute/verify] skipped — {e}")

    from .zeon_bridge import zeon_swap_selfcheck, ZeonBridgeUnavailable
    for label, fn in [
        ("design+learn (labworld GP + ParEGO + split-conformal)",
         lambda: seams.real_world_model_run(n_iter=30, seed=0)),
        ("plan (tipseq_plr sow: NL -> protocol)",
         lambda: seams.plan_from_text("cut and tag 8 samples, sequence to 2M reads")),
        ("dexterity (plr_lr arm move, sim)", seams.dexterity_checkpoint),
        ("zeon bridge -- swap the arm backend to ZeonArmBackend (same loop, sim)",
         zeon_swap_selfcheck),
    ]:
        try:
            print(f"\n[{label}]\n  {fn()}")
        except (seams.SeamUnavailable, ZeonBridgeUnavailable) as e:
            print(f"\n[{label}]\n  skipped — {e}")


def main():
    ap = argparse.ArgumentParser(description="bay-hack DBTL demo")
    ap.add_argument("--real", action="store_true",
                    help="run against the installed @di-omics stack (no hardware)")
    args = ap.parse_args()
    if args.real:
        real_demo()
        return

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
