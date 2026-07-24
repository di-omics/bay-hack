"""The announced Track A TEM-1 loop stays adaptive, gated, and venue-neutral."""
import csv
import json

import pytest

from bayhack.tem1 import (
    AssayQCError,
    Compound,
    ExpressionEvidence,
    KineticPlate,
    TEM1AssaySpec,
    TEM1Error,
    analyze_round,
    build_round1_plan,
    build_round2_plan,
    confirm_expression,
    load_compounds,
    run_simulated_closed_loop,
    save_closed_loop,
    select_initial_compounds,
    simulate_kinetic_plate,
    simulation_compounds,
    verify_receipt_integrity,
)
from bayhack.tem1_cli import initialize_packet


def confirmed_fixture_spec():
    return TEM1AssaySpec(
        expression_confirmation_method="organizer-confirmed fixture method",
        expression_min_fold_over_background=2.0,
        expression_instrument="fixture fluorescence reader",
        expression_reaction_volume_ul=30,
        expression_plate_type="fixture 96-well plate",
        expression_incubation_temperature_c=29,
        expression_incubation_s=3600,
        expression_shaking_rpm=1200,
        expression_shaking_orbit_mm=3,
        substrate_name="organizer-confirmed fixture",
        read_wavelength_nm=500,
        kinetic_interval_s=30,
        kinetic_duration_s=300,
        reaction_volume_ul=100,
        assay_mix_volume_ul=60,
        compound_volume_ul=20,
        substrate_volume_ul=20,
        preincubation_s=120,
        vehicle_control_composition="fixture buffer, enzyme, and vehicle",
        no_enzyme_control_composition="fixture buffer and vehicle, no enzyme",
        protocol_confirmed_by_organizer=True,
    )


def test_default_spec_refuses_physical_execution_until_organizer_confirmation():
    spec = TEM1AssaySpec()
    assert spec.verify()["passed"]
    assert not spec.physical_ready
    assert "expression_min_fold_over_background" in spec.physical_missing()
    assert "expression_instrument" in spec.physical_missing()
    assert "expression_reaction_volume_ul" in spec.physical_missing()
    assert "kinetic_duration_s" in spec.physical_missing()
    assert "vehicle_control_composition" in spec.physical_missing()
    assert "protocol_confirmed_by_organizer" in spec.physical_missing()


def test_confirmed_spec_and_sources_unlock_plan_execution():
    spec = confirmed_fixture_spec()
    compounds = [
        Compound(
            compound_id=f"FIXTURE-{index}",
            name=f"fixture {index}",
            source_well=f"A{index}",
            screen_concentration=10.0,
            concentration_unit="uM",
        )
        for index in range(1, 5)
    ]
    plan = build_round1_plan(compounds, spec)
    verdict = plan.verify(compounds, spec)
    assert spec.physical_ready
    assert verdict["passed"]
    assert verdict["physical_ready"]
    assert verdict["execution_allowed"]


def test_physical_plan_requires_concentration_and_units():
    spec = confirmed_fixture_spec()
    compounds = [
        Compound(
            compound_id="C01",
            name="missing concentration",
            source_well="A1",
        )
    ]
    plan = build_round1_plan(compounds, spec)
    verdict = plan.verify(compounds, spec)
    assert verdict["passed"]
    assert not verdict["execution_allowed"]
    assert "screen_concentration:C01" in verdict["physical_missing"]
    assert "concentration_unit:C01" in verdict["physical_missing"]


def test_compound_csv_loads_features_and_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "compounds.csv"
    path.write_text(
        "compound_id,name,source_well,screen_concentration,concentration_unit,"
        "feature_mass,feature_charge\n"
        "C01,one,A1,1.0,relative,0.2,-1\n"
        "C02,two,B1,1.0,relative,0.8,1\n"
    )
    compounds = load_compounds(path)
    assert compounds[0].features == (0.2, -1.0)
    assert compounds[1].source_well == "B1"

    path.write_text(
        "compound_id,name\nC01,one\nC01,duplicate\n"
    )
    with pytest.raises(TEM1Error, match="unique"):
        load_compounds(path)


def test_round1_uses_diversity_and_balanced_replicates():
    compounds = simulation_compounds()
    selected, rationale = select_initial_compounds(compounds, 6)
    assert len(selected) == 6
    assert len({compound.compound_id for compound in selected}) == 6
    assert "farthest-point" in rationale["method"]
    assert rationale["measurement_used"] is False

    spec = TEM1AssaySpec()
    plan = build_round1_plan(compounds, spec, n_select=6)
    verdict = plan.verify(compounds, spec)
    assert verdict["passed"]
    assert not verdict["execution_allowed"]
    roles = [assignment.role for assignment in plan.assignments]
    assert roles.count("vehicle_control") == 3
    assert roles.count("no_enzyme_control") == 3
    candidate_counts = {}
    for assignment in plan.assignments:
        if assignment.role == "candidate":
            candidate_counts[assignment.compound_id] = (
                candidate_counts.get(assignment.compound_id, 0) + 1
            )
    assert set(candidate_counts.values()) == {2}


def test_complete_agent_priority_scores_drive_round1_selection():
    compounds = [
        Compound(
            compound_id=f"C{index:02d}",
            name=f"candidate {index}",
            priority_score=float(index),
            priority_source="organizer-approved docking score",
        )
        for index in range(1, 7)
    ]
    selected, rationale = select_initial_compounds(compounds, 3)
    assert [compound.compound_id for compound in selected] == [
        "C06",
        "C05",
        "C04",
    ]
    assert rationale["priority_scores_complete"]
    assert rationale["priority_scores_present"] == 6
    assert rationale["priority_sources"] == [
        "organizer-approved docking score"
    ]
    assert "priority score" in rationale["method"]


def test_good_controls_allow_learning_and_measured_round2_design():
    compounds = simulation_compounds()
    spec = TEM1AssaySpec()
    plan = build_round1_plan(compounds, spec, n_select=8)
    plate = simulate_kinetic_plate(plan, seed=17)
    analysis = analyze_round(plan, compounds, spec, plate)
    assert analysis["assay_qc"]["passed"]
    assert analysis["assay_qc"]["z_prime"] >= 0.5
    assert analysis["world_model"]["updated"]
    assert analysis["measurement"]["provenance"] == "modeled:tem1-kinetics"

    round2 = build_round2_plan(analysis, compounds, spec, top_k=3)
    assert round2.round_id == 2
    assert round2.selection_rationale["measurement_used"]
    assert len(round2.selection_rationale["selected"]) == 3
    assert round2.selection_rationale["selected"][0]["compound_id"] == "CMPD-07"
    candidate_conditions = {
        (assignment.compound_id, assignment.concentration_factor)
        for assignment in round2.assignments
        if assignment.role == "candidate"
    }
    assert len(candidate_conditions) == 12
    with pytest.raises(TEM1Error, match="at least one"):
        build_round2_plan(analysis, compounds, spec, top_k=0)


def test_expression_gate_requires_replicated_signal_over_background(tmp_path):
    path = tmp_path / "expression.csv"
    path.write_text(
        "role,replicate,value\n"
        "tem1_expression,1,9.8\n"
        "tem1_expression,2,10.1\n"
        "tem1_expression,3,10.0\n"
        "no_template_control,1,1.0\n"
        "no_template_control,2,1.1\n"
        "no_template_control,3,0.9\n"
    )
    evidence = ExpressionEvidence.from_csv(path)
    verdict = confirm_expression(evidence, confirmed_fixture_spec())
    assert verdict["passed"]
    assert verdict["fold_over_background"] > 2.0
    assert verdict["provenance"] == "measured:expression-csv"
    assert len(verdict["evidence"]["sha256"]) == 64

    failed = ExpressionEvidence(
        {
            "tem1_expression": [1.0, 1.1, 0.9],
            "no_template_control": [1.0, 1.1, 0.9],
        },
        provenance="measured:fixture",
    )
    failed_verdict = confirm_expression(failed, confirmed_fixture_spec())
    assert not failed_verdict["passed"]
    assert any("not above" in reason for reason in failed_verdict["reasons"])


def test_bad_control_separation_quarantines_data_and_blocks_round2():
    compounds = simulation_compounds()[:4]
    spec = TEM1AssaySpec()
    plan = build_round1_plan(compounds, spec)
    good = simulate_kinetic_plate(plan, seed=3)
    values = {well: list(points) for well, points in good.values.items()}
    activity_points = values["A1"]
    for well in ("A2", "A11", "H12"):
        values[well] = list(activity_points)
    plate = KineticPlate(values, provenance="modeled:bad-controls")
    analysis = analyze_round(plan, compounds, spec, plate)
    assert not analysis["assay_qc"]["passed"]
    assert not analysis["world_model"]["updated"]
    assert all(not candidate["hit"] for candidate in analysis["candidates"])
    with pytest.raises(AssayQCError, match="refusing"):
        build_round2_plan(analysis, compounds, spec)


def test_kinetic_csv_records_measured_provenance_and_digest(tmp_path):
    path = tmp_path / "reader.csv"
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["well", "time_s", "absorbance"])
        for well, slope in (("A1", 0.5), ("B1", 0.2)):
            for time_s in (0, 30, 60):
                writer.writerow([well, time_s, 0.1 + slope * time_s / 60])
    plate = KineticPlate.from_csv(path)
    assert plate.provenance == "measured:kinetic-reader-csv"
    assert len(plate.evidence["sha256"]) == 64
    assert plate.slope("A1") == pytest.approx(0.5 / 60.0)


def test_missing_kinetic_well_fails_closed():
    compounds = simulation_compounds()[:2]
    spec = TEM1AssaySpec()
    plan = build_round1_plan(compounds, spec)
    plate = simulate_kinetic_plate(plan, seed=2)
    plate.values.pop(plan.assignments[-1].well)
    with pytest.raises(TEM1Error, match="missing wells"):
        analyze_round(plan, compounds, spec, plate)


def test_full_two_round_simulation_nominates_a_confirmed_condition():
    receipt = run_simulated_closed_loop(seed=17)
    assert receipt["track"] == "Track A: Close the Loop"
    assert receipt["target"] == "TEM-1 beta-lactamase"
    assert receipt["protein_synthesis"]["confirmation"]["passed"]
    assert receipt["protein_synthesis"]["screening_allowed"]
    assert len(receipt["rounds"]) == 2
    assert all(round_data["assay_qc"]["passed"] for round_data in receipt["rounds"])
    assert receipt["follow_up"]["executed"]
    assert receipt["follow_up"]["provenance"] == "modeled"
    assert receipt["follow_up"]["dose_response_monotonic"]
    assert receipt["follow_up"]["inhibition_50_factor_estimate"] > 0
    assert all(
        curve["monotonic_with_uncertainty"]
        for curve in receipt["rounds"][1]["dose_response"]
    )
    assert verify_receipt_integrity(receipt)
    assert not receipt["assay_spec"]["physical_ready"]


@pytest.mark.parametrize("seed", [1, 7, 17, 31])
def test_seeded_fallback_is_stable(seed):
    receipt = run_simulated_closed_loop(seed=seed)
    assert all(round_data["assay_qc"]["passed"] for round_data in receipt["rounds"])
    assert receipt["follow_up"]["dose_response_monotonic"]
    assert verify_receipt_integrity(receipt)


def test_receipt_integrity_detects_tampering():
    receipt = run_simulated_closed_loop(seed=17)
    receipt["follow_up"]["compound_id"] = "TAMPERED"
    assert not verify_receipt_integrity(receipt)
    with pytest.raises(TEM1Error, match="invalid integrity"):
        save_closed_loop(receipt, "not-written.json")


def test_init_packet_prefills_only_published_protocol_facts(tmp_path):
    packet = initialize_packet(tmp_path / "packet")
    spec = json.loads((tmp_path / "packet" / "assay-spec.json").read_text())
    compounds = load_compounds(tmp_path / "packet" / "compounds.csv")
    assert packet["assay_spec"].endswith("assay-spec.json")
    assert spec["substrate_name"] == "nitrocefin"
    assert spec["expression_confirmation_method"] == "sfGFP fluorescence"
    assert spec["read_wavelength_nm"] == 490.0
    assert spec["kinetic_interval_s"] == 30.0
    assert spec["kinetic_duration_s"] is None
    assert len(compounds) == 95
    assert not spec["protocol_confirmed_by_organizer"]
    assert not spec["physical_ready"]


def test_95_compound_library_defaults_to_one_full_replicated_plate():
    compounds = [
        Compound(
            compound_id=f"C{index:02d}",
            name=f"candidate {index:02d}",
            source_well=f"{'ABCDEFGH'[(index - 1) % 8]}{(index - 1) // 8 + 1}",
            screen_concentration=1.0,
        )
        for index in range(1, 96)
    ]
    plan = build_round1_plan(compounds, TEM1AssaySpec())
    candidates = [
        assignment for assignment in plan.assignments
        if assignment.role == "candidate"
    ]
    assert len(plan.assignments) == 96
    assert len(candidates) == 90
    assert len({assignment.compound_id for assignment in candidates}) == 45
    assert plan.selection_rationale["library_size"] == 95
    assert plan.selection_rationale["plate_capacity"] == 45
    assert plan.selection_rationale["library_truncated_to_fit"]


def test_breadth_first_round1_can_screen_90_unique_compounds():
    compounds = [
        Compound(
            compound_id=f"C{index:02d}",
            name=f"candidate {index:02d}",
            source_well=f"{'ABCDEFGH'[(index - 1) % 8]}{(index - 1) // 8 + 1}",
            screen_concentration=1.0,
            concentration_unit="uM",
        )
        for index in range(1, 96)
    ]
    spec = TEM1AssaySpec(candidate_replicates=1)
    plan = build_round1_plan(compounds, spec)
    candidates = [
        assignment for assignment in plan.assignments
        if assignment.role == "candidate"
    ]
    assert len(plan.assignments) == 96
    assert len(candidates) == 90
    assert len({assignment.compound_id for assignment in candidates}) == 90
    assert spec.round2_candidate_replicates == 2
    analysis = analyze_round(
        plan,
        compounds,
        spec,
        simulate_kinetic_plate(plan, seed=9),
    )
    round2 = build_round2_plan(analysis, compounds, spec, top_k=3)
    round2_groups = {}
    for assignment in round2.assignments:
        if assignment.role == "candidate":
            key = (assignment.compound_id, assignment.concentration_factor)
            round2_groups[key] = round2_groups.get(key, 0) + 1
    assert set(round2_groups.values()) == {2}
