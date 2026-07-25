"""Offline smoke test for the ADK tool contract without an LLM or API key."""
from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path

from bayhack.tem1 import (
    TEM1AssaySpec,
    TEM1RoundPlan,
    save_compounds,
    simulate_kinetic_plate,
    simulation_compounds,
)

from .tools import (
    analyze_reader_kinetics,
    design_round_1,
    design_round_2,
    inspect_track_a_inputs,
    prove_round_1_changed_round_2,
)


def _write_reader_csv(path: Path, plan: TEM1RoundPlan) -> None:
    plate = simulate_kinetic_plate(plan, seed=17)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["well", "time_s", "value"])
        for well, points in sorted(plate.values.items()):
            for time_s, value in points:
                writer.writerow([well, time_s, value])


def run_smoke() -> dict:
    previous_run_dir = os.environ.get("BAYHACK_RUN_DIR")
    result: dict | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="bayhack-adk-") as temporary:
            os.environ["BAYHACK_RUN_DIR"] = temporary
            root = Path(temporary)
            spec = TEM1AssaySpec(expression_min_fold_over_background=2.0)
            spec.save(root / "assay-spec.json")
            compounds = simulation_compounds()
            save_compounds(compounds, root / "compounds.csv")

            inspection = inspect_track_a_inputs(
                "assay-spec.json", "compounds.csv"
            )
            round1 = design_round_1(
                "assay-spec.json",
                "compounds.csv",
                selection_count=8,
            )
            plan = TEM1RoundPlan.load(root / round1["output_file"])
            _write_reader_csv(root / "round1-reader.csv", plan)
            analysis = analyze_reader_kinetics(
                "assay-spec.json",
                "compounds.csv",
                round1["output_file"],
                "round1-reader.csv",
            )
            round2 = design_round_2(
                "assay-spec.json",
                "compounds.csv",
                analysis["output_file"],
            )
            proof = prove_round_1_changed_round_2(
                "assay-spec.json",
                "compounds.csv",
                analysis["output_file"],
                round2["output_file"],
            )

            result = {
                "tool_contract": "evidence file in -> decision -> plate map out",
                "input_validation": inspection["ok"],
                "round1_plan": round1["ok"],
                "round1_qc": analysis["assay_qc"]["passed"],
                "round2_plan": round2["ok"],
                "round2_uses_measurement": (
                    round2["selection_rationale"]["measurement_used"]
                ),
                "round_transition_proved": proof["loop_closed"],
                "physical_execution_allowed": round2[
                    "physical_execution_allowed"
                ],
            }
    finally:
        if previous_run_dir is None:
            os.environ.pop("BAYHACK_RUN_DIR", None)
        else:
            os.environ["BAYHACK_RUN_DIR"] = previous_run_dir
    expected = {
        "tool_contract": "evidence file in -> decision -> plate map out",
        "input_validation": True,
        "round1_plan": True,
        "round1_qc": True,
        "round2_plan": True,
        "round2_uses_measurement": True,
        "round_transition_proved": True,
        "physical_execution_allowed": False,
    }
    if result != expected:
        raise SystemExit(f"ADK tool smoke failed: {result}")
    return result


if __name__ == "__main__":
    print(json.dumps(run_smoke(), indent=2))
