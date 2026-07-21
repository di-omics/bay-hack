"""Pre-act fault injection for the liquid-handling safety demo.

The unsafe plan is verified, refused, and replaced before any backend receives a
command. This gives the stage demo a visible failure and recovery path without
moving hardware or contaminating the scientific model.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from .assay import LiquidHandlingAssay, LiquidHandlingPlan


FAULTS = ("tip_reuse", "sub_minimum", "destination_overlap")


def inject_fault(
    plan: LiquidHandlingPlan,
    assay: LiquidHandlingAssay,
    kind: str,
) -> LiquidHandlingPlan:
    """Return a deliberately invalid copy of a valid plan."""
    if kind == "tip_reuse":
        if len(plan.transfers) < 2:
            raise ValueError("tip reuse requires a two-transfer plan")
        first, second = plan.transfers[:2]
        return replace(
            plan,
            transfers=(first, replace(second, tip=first.tip), *plan.transfers[2:]),
        )
    if kind == "sub_minimum":
        return assay.plan(plan.run_id, plan.phase, 0.01)
    if kind == "destination_overlap":
        destination = assay.stock_well
        return replace(
            plan,
            destination=destination,
            transfers=tuple(
                replace(transfer, destination=destination)
                for transfer in plan.transfers
            ),
        )
    raise ValueError(f"unknown fault kind: {kind}")


def run_refusal(kind: str = "tip_reuse") -> dict:
    """Build a refusal receipt proving the unsafe plan never reached execution."""
    if kind not in FAULTS:
        raise ValueError(f"fault must be one of: {', '.join(FAULTS)}")
    assay = LiquidHandlingAssay()
    recovery_plan = assay.plan(run_id=1, phase="safety-check", design_x=0.2)
    unsafe_plan = inject_fault(recovery_plan, assay, kind)
    verdict = assay.verify(unsafe_plan)
    if verdict["passed"]:
        raise RuntimeError("fault injection did not produce an invalid plan")
    recovery_verdict = assay.verify(recovery_plan)
    return {
        "schema_version": "1.0",
        "status": "REFUSED",
        "fault": kind,
        "unsafe_plan": unsafe_plan.to_dict(),
        "plan_verification": verdict,
        "execution": {
            "attempted": False,
            "commands_issued": 0,
            "reason": "plan verification failed before backend dispatch",
        },
        "measurement": {"taken": False},
        "world_model": {"updated": False},
        "follow_up": {"executed": False},
        "recovery": {
            "action": "replace the invalid plan with a freshly verified plan",
            "plan": recovery_plan.to_dict(),
            "plan_verification": recovery_verdict,
        },
    }


def save_refusal(receipt: dict, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(receipt, indent=2) + "\n")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description="prove an unsafe liquid-handling plan is refused before motion"
    )
    parser.add_argument("--fault", choices=FAULTS, default="tip_reuse")
    parser.add_argument("--output")
    args = parser.parse_args()

    receipt = run_refusal(args.fault)
    print("=" * 68)
    print("bay-hack safety demo: verify before act")
    print("=" * 68)
    print(f"fault              : {receipt['fault']}")
    print(f"plan status        : {receipt['status']}")
    print(f"reason             : {receipt['plan_verification']['reasons'][0]}")
    print(f"robot commands     : {receipt['execution']['commands_issued']}")
    print(f"measurement taken  : {receipt['measurement']['taken']}")
    print(f"model updated      : {receipt['world_model']['updated']}")
    print(f"follow-up executed : {receipt['follow_up']['executed']}")
    print(
        "recovery plan      : "
        + ("PASS" if receipt["recovery"]["plan_verification"]["passed"] else "FAIL")
    )
    if args.output:
        print(f"refusal receipt     : {save_refusal(receipt, args.output)}")


if __name__ == "__main__":
    main()
