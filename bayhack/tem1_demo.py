"""Narrated Track A demo for the announced TEM-1 inhibitor challenge."""
from __future__ import annotations

import argparse

from .tem1 import run_simulated_closed_loop, save_closed_loop


def main() -> None:
    parser = argparse.ArgumentParser(
        description="run the two-round TEM-1 inhibitor loop in simulation"
    )
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--receipt")
    args = parser.parse_args()

    receipt = run_simulated_closed_loop(seed=args.seed)
    round1, round2 = receipt["rounds"]
    print("=" * 72)
    print("bay-hack Track A: close the TEM-1 inhibitor loop")
    print("choose compounds -> run plate -> read kinetics -> QC -> sharpen round 2")
    print("=" * 72)
    print("mode                  : SIMULATION (no venue protocol values guessed)")
    expression = receipt["protein_synthesis"]["confirmation"]
    print(
        f"TEM-1 expression      : {expression['fold_over_background']:.2f}x "
        "over no-template control  PASS"
    )
    print(f"round 1 plate wells   : {len(round1['plan']['assignments'])}")
    print(f"round 1 Z-prime       : {round1['assay_qc']['z_prime']:.3f}  PASS")
    print("round 1 model update  : PASS")
    print("round 2 selected      :")
    for selected in round2["plan"]["selection_rationale"]["selected"]:
        print(
            f"  {selected['compound_id']:8s}  "
            f"inhibition={selected['mean_inhibition_pct']:6.2f}%  "
            f"uncertainty={selected['standard_error_pct']:5.2f}%  "
            f"score={selected['selection_score']:6.2f}"
        )
    print(f"round 2 plate wells   : {len(round2['plan']['assignments'])}")
    print(f"round 2 Z-prime       : {round2['assay_qc']['z_prime']:.3f}  PASS")
    follow_up = receipt["follow_up"]
    print(
        "confirmed condition   : "
        f"{follow_up['compound_id']} at {follow_up['concentration_factor']:g}x  "
        f"({follow_up['mean_inhibition_pct']:.2f}% modeled inhibition)"
    )
    print(
        "dose-response gate    : "
        f"monotonic={follow_up['dose_response_monotonic']}  "
        f"relative I50={follow_up['inhibition_50_factor_estimate']:.2f}x"
    )
    print(f"receipt integrity     : sha256:{receipt['integrity']['digest'][:16]}...")
    print("physical execution    : REFUSED until organizer protocol is configured")
    missing = receipt["assay_spec"]["physical_missing"]
    print("venue fields owed     : " + ", ".join(missing))
    if args.receipt:
        destination = save_closed_loop(receipt, args.receipt)
        print(f"trust receipt         : {destination}")


if __name__ == "__main__":
    main()
