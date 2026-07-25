"""Narrated Track C demo for verified tube access and recovery."""
from __future__ import annotations

import argparse

from .track_c import (
    SimulatedTubeCell,
    run_simulated_tube_access,
    save_track_c_receipt,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="run verified tube uncapping and recapping in simulation"
    )
    parser.add_argument(
        "--fault",
        choices=sorted(SimulatedTubeCell.FAULTS),
        default="partial_uncap",
        help="fault to inject into the deterministic simulation",
    )
    parser.add_argument("--receipt")
    args = parser.parse_args()

    receipt = run_simulated_tube_access(args.fault)
    print("=" * 76)
    print("bay-hack Track C: verified tube access for liquid handling")
    print("observe -> uncap -> verify open -> pipette handoff -> recap -> verify")
    print("=" * 76)
    print("mode                  : SIMULATION")
    print(f"fault injection       : {args.fault}")
    print("fixture               : split-collar tube nest")
    print("physical commands     : 0")
    print("event trace:")
    for event in receipt["events"]:
        status = "PASS" if event["passed"] else "HOLD"
        if event["kind"] == "recovery":
            status = "RETRY"
        print(
            f"  {event['sequence']:02d}  {event['state']:24s} "
            f"{event['kind']:21s} {status:5s}  {event['detail']}"
        )
    gates = receipt["gates"]
    print("-" * 76)
    print(f"open verified         : {gates['open_verified']}")
    print(f"pipetting allowed     : {gates['pipetting_allowed']}")
    print(f"closed verified       : {gates['closed_verified']}")
    print(f"recoveries            : {receipt['recoveries']}")
    print(f"final status          : {receipt['status']}")
    print(
        "receipt integrity     : "
        f"sha256:{receipt['integrity']['digest'][:16]}..."
    )
    if args.receipt:
        destination = save_track_c_receipt(receipt, args.receipt)
        print(f"trust receipt         : {destination}")


if __name__ == "__main__":
    main()
