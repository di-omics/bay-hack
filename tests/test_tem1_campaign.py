"""Track A evidence must prove adaptation and support measured replay."""
import csv
import json

import pytest

from bayhack.tem1 import (
    ExpressionEvidence,
    KineticPlate,
    TEM1AssaySpec,
    TEM1Error,
    TEM1RoundPlan,
    analyze_round,
    build_round_transition,
    build_round1_plan,
    build_round2_plan,
    confirm_expression,
    finalize_measured_campaign,
    save_analysis,
    save_compounds,
    simulate_kinetic_plate,
    simulation_compounds,
    verify_receipt_integrity,
)
from bayhack.tem1_cli import initialize_packet


def _confirmed_spec() -> TEM1AssaySpec:
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
        read_wavelength_nm=490,
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


def _write_reader(path, plan: TEM1RoundPlan, seed: int) -> None:
    plate = simulate_kinetic_plate(plan, seed=seed)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["well", "time_s", "value"])
        for well, points in plate.values.items():
            for time_s, value in points:
                writer.writerow([well, time_s, value])


def _build_measured_packet(run_dir):
    initialize_packet(run_dir)
    spec = _confirmed_spec()
    spec.save(run_dir / "assay-spec.json")
    compounds = simulation_compounds()
    save_compounds(compounds, run_dir / "compounds.csv")

    expression_path = run_dir / "expression.csv"
    expression_path.write_text(
        "role,replicate,value\n"
        "tem1_expression,1,9.8\n"
        "tem1_expression,2,10.1\n"
        "tem1_expression,3,10.0\n"
        "no_template_control,1,1.0\n"
        "no_template_control,2,1.1\n"
        "no_template_control,3,0.9\n"
    )
    expression = confirm_expression(
        ExpressionEvidence.from_csv(expression_path),
        spec,
    )
    save_analysis(expression, run_dir / "expression-confirmation.json")

    round1_plan = build_round1_plan(compounds, spec, n_select=8)
    round1_plan.save(run_dir / "round1-plan.json")
    _write_reader(run_dir / "round1-reader.csv", round1_plan, 17)
    round1 = analyze_round(
        round1_plan,
        compounds,
        spec,
        KineticPlate.from_csv(run_dir / "round1-reader.csv"),
    )
    save_analysis(round1, run_dir / "round1-analysis.json")

    round2_plan = build_round2_plan(round1, compounds, spec, top_k=3)
    round2_plan.save(run_dir / "round2-plan.json")
    _write_reader(run_dir / "round2-reader.csv", round2_plan, 18)
    round2 = analyze_round(
        round2_plan,
        compounds,
        spec,
        KineticPlate.from_csv(run_dir / "round2-reader.csv"),
    )
    save_analysis(round2, run_dir / "round2-analysis.json")
    return spec, compounds, round1, round2_plan


def test_transition_proves_ranked_measurements_changed_the_plate():
    spec = _confirmed_spec()
    compounds = simulation_compounds()
    round1_plan = build_round1_plan(compounds, spec, n_select=8)
    round1 = analyze_round(
        round1_plan,
        compounds,
        spec,
        simulate_kinetic_plate(round1_plan, seed=17),
    )
    round2_plan = build_round2_plan(round1, compounds, spec, top_k=3)

    proof = build_round_transition(
        round1,
        round2_plan,
        compounds,
        spec,
    )

    assert proof["loop_closed"]
    assert proof["verification"]["selection_matches_ranked_evidence"]
    assert proof["plate_change"]["round1_compounds_tested"] == 8
    assert proof["plate_change"]["round2_compounds_advanced"] == 3
    assert proof["plate_change"]["round2_concentration_conditions"] == 12
    assert verify_receipt_integrity(proof)


def test_transition_refuses_a_plate_that_does_not_match_the_ranking():
    spec = _confirmed_spec()
    compounds = simulation_compounds()
    round1_plan = build_round1_plan(compounds, spec, n_select=8)
    round1 = analyze_round(
        round1_plan,
        compounds,
        spec,
        simulate_kinetic_plate(round1_plan, seed=17),
    )
    round2_plan = build_round2_plan(round1, compounds, spec, top_k=3)
    payload = round2_plan.to_dict()
    payload["selection_rationale"]["selected"][0]["compound_id"] = "CMPD-01"

    with pytest.raises(TEM1Error, match="ranking|rationale"):
        build_round_transition(
            round1,
            TEM1RoundPlan.from_dict(payload),
            compounds,
            spec,
        )


def test_measured_campaign_recomputes_raw_files_and_seals_receipt(tmp_path):
    run_dir = tmp_path / "tem1"
    _build_measured_packet(run_dir)

    receipt = finalize_measured_campaign(run_dir)

    assert receipt["mode"] == "measured-evidence"
    assert receipt["protein_synthesis"]["confirmation"]["provenance"].startswith(
        "measured:"
    )
    assert all(
        round_data["measurement"]["provenance"].startswith("measured:")
        for round_data in receipt["rounds"]
    )
    assert receipt["round_transition"]["loop_closed"]
    assert receipt["follow_up"]["provenance"] == "measured"
    assert verify_receipt_integrity(receipt)
    assert len(receipt["source_artifacts"]) == 11


def test_measured_campaign_refuses_tampered_analysis(tmp_path):
    run_dir = tmp_path / "tem1"
    _build_measured_packet(run_dir)
    path = run_dir / "round1-analysis.json"
    payload = json.loads(path.read_text())
    payload["candidates"][0]["mean_inhibition_pct"] = 100.0
    path.write_text(json.dumps(payload, indent=2) + "\n")

    with pytest.raises(TEM1Error, match="raw evidence"):
        finalize_measured_campaign(run_dir)
