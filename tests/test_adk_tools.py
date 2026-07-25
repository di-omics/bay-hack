"""The optional ADK tools preserve the deterministic Track A file contract."""
import csv

from bayhack.tem1 import (
    TEM1AssaySpec,
    TEM1RoundPlan,
    save_compounds,
    simulate_kinetic_plate,
    simulation_compounds,
)
from bayhack_adk.tools import (
    analyze_reader_kinetics,
    design_round_1,
    design_round_2,
    inspect_track_a_inputs,
    prove_round_1_changed_round_2,
)


def _write_reader(path, plan):
    plate = simulate_kinetic_plate(plan, seed=17)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["well", "time_s", "value"])
        for well, points in plate.values.items():
            for time_s, value in points:
                writer.writerow([well, time_s, value])


def test_adk_tools_turn_reader_file_into_adaptive_plate_map(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("BAYHACK_RUN_DIR", str(tmp_path))
    TEM1AssaySpec(
        expression_min_fold_over_background=2.0
    ).save(tmp_path / "assay-spec.json")
    save_compounds(simulation_compounds(), tmp_path / "compounds.csv")

    inspection = inspect_track_a_inputs(
        "assay-spec.json", "compounds.csv"
    )
    round1 = design_round_1(
        "assay-spec.json",
        "compounds.csv",
        selection_count=8,
    )
    plan = TEM1RoundPlan.load(tmp_path / round1["output_file"])
    _write_reader(tmp_path / "reader.csv", plan)
    analysis = analyze_reader_kinetics(
        "assay-spec.json",
        "compounds.csv",
        round1["output_file"],
        "reader.csv",
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

    assert inspection["ok"]
    assert round1["ok"]
    assert analysis["round2_allowed"]
    assert round2["ok"]
    assert round2["selection_rationale"]["measurement_used"]
    assert proof["ok"]
    assert proof["loop_closed"]
    assert proof["plate_change"]["round2_compounds_advanced"] == 3
    assert not round2["physical_execution_allowed"]


def test_adk_tool_paths_cannot_escape_event_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("BAYHACK_RUN_DIR", str(tmp_path))
    result = inspect_track_a_inputs("../secret.json", "../compounds.csv")
    assert not result["ok"]
    assert "escapes BAYHACK_RUN_DIR" in result["error"]
    assert not result["physical_execution_allowed"]
