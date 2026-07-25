"""On-site file workflow for the Track A TEM-1 scientific loop."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .tem1 import (
    Compound,
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
    file_sha256,
    finalize_measured_campaign,
    load_compounds,
    save_analysis,
    save_closed_loop,
    save_compounds,
)


def _template_compounds() -> list[Compound]:
    return [
        Compound(
            compound_id=f"CANDIDATE-{index:02d}",
            name=f"replace with organizer compound {index:02d}",
        )
        for index in range(1, 96)
    ]


def _hardware_matrix_template() -> dict:
    """Published booking facts plus blank venue-specific integration fields."""
    return {
        "schema_version": "1.0",
        "track": "Track A: Close the Loop",
        "booking": {
            "slot_duration_min": 60,
            "reader_auto_reserved_inside_screen_block": True,
            "one_active_expression_batch_per_team": True,
            "gfp_gate_required_before_screen_booking": True,
            "expression_slot": None,
            "round1_screen_slot": None,
            "round2_screen_slot": None,
        },
        "zeon": {
            "project": None,
            "workflow": None,
            "world": None,
            "approved_skills": [],
            "source_plate_object": None,
            "assay_plate_object": None,
            "source_well_anchor": None,
            "destination_well_anchor": None,
        },
        "liquid_handling": {
            "volume_unit": None,
            "safe_speed": None,
            "tip_policy": None,
            "resume_policy": None,
            "waste_policy": None,
            "simulation_guard_confirmed": False,
        },
        "reader": {
            "instrument": "BioTek ELx808",
            "export_schema": None,
            "read_wavelength_nm": 490.0,
            "kinetic_interval_s": 30.0,
        },
        "safety": {
            "physical_e_stop_owner": None,
            "human_motion_gate_owner": None,
            "deck_cleared": False,
        },
        "organizer_review": {
            "reviewed_by": None,
            "reviewed_at": None,
        },
    }


def initialize_packet(output_dir: str | Path) -> dict:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    spec_path = TEM1AssaySpec().save(destination / "assay-spec.json")
    compounds_path = save_compounds(
        _template_compounds(), destination / "compounds.csv"
    )
    hardware_matrix_path = destination / "hardware-matrix.json"
    hardware_matrix_path.write_text(
        json.dumps(_hardware_matrix_template(), indent=2) + "\n"
    )
    instructions = destination / "README.txt"
    instructions.write_text(
        "TEM-1 on-site packet\n"
        "\n"
        "1. Replace every placeholder in compounds.csv with organizer data.\n"
        "2. Keep the prefilled nitrocefin, A490, 30 s cadence, and sfGFP fields\n"
        "   only if the track lead confirms the published guide is unchanged.\n"
        "3. Fill every remaining assay-spec.json field only from the official\n"
        "   track protocol.\n"
        "4. Set protocol_confirmed_by_organizer to true after confirmation.\n"
        "5. Export expression evidence as role,replicate,value.\n"
        "6. Confirm TEM-1 expression before screening compounds.\n"
        "7. Generate round-1-plan.json with the round1-plan command.\n"
        "8. Export inhibitor reader data as well,time_s,value.\n"
        "9. Analyze round 1, then generate round 2 from that observed result.\n"
        "10. Export the round transition proof before executing round 2.\n"
        "11. Finalize the measured campaign receipt from the fixed raw files.\n"
    )
    return {
        "assay_spec": str(spec_path),
        "compounds": str(compounds_path),
        "hardware_matrix": str(hardware_matrix_path),
        "instructions": str(instructions),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="prepare and analyze the bay-hack TEM-1 Track A loop"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    initialize = commands.add_parser(
        "init", help="write an unconfirmed on-site configuration packet"
    )
    initialize.add_argument("--output-dir", default="run_artifacts/tem1")

    round1 = commands.add_parser(
        "round1-plan", help="build a balanced replicated round-1 plate"
    )
    round1.add_argument("--config", required=True)
    round1.add_argument("--compounds", required=True)
    round1.add_argument("--select", type=int)
    round1.add_argument("--output", required=True)

    expression = commands.add_parser(
        "confirm-expression",
        help="gate compound screening on replicated TEM-1 production evidence",
    )
    expression.add_argument("--config", required=True)
    expression.add_argument("--evidence", required=True)
    expression.add_argument("--output", required=True)

    analyze = commands.add_parser(
        "analyze", help="analyze kinetic reader data against a saved plan"
    )
    analyze.add_argument("--config", required=True)
    analyze.add_argument("--compounds", required=True)
    analyze.add_argument("--plan", required=True)
    analyze.add_argument("--reader", required=True)
    analyze.add_argument("--output", required=True)

    round2 = commands.add_parser(
        "round2-plan", help="design confirmation from observed round-1 analysis"
    )
    round2.add_argument("--config", required=True)
    round2.add_argument("--compounds", required=True)
    round2.add_argument("--analysis", required=True)
    round2.add_argument("--top-k", type=int, default=3)
    round2.add_argument("--output", required=True)

    transition = commands.add_parser(
        "prove-loop",
        help="prove that accepted round-1 evidence changed the round-2 plate",
    )
    transition.add_argument("--config", required=True)
    transition.add_argument("--compounds", required=True)
    transition.add_argument("--analysis", required=True)
    transition.add_argument("--round2-plan", required=True)
    transition.add_argument("--output", required=True)

    finalize = commands.add_parser(
        "finalize",
        help="recompute and seal a measured campaign from fixed raw files",
    )
    finalize.add_argument("--run-dir", default="run_artifacts/tem1")
    finalize.add_argument("--output")

    args = parser.parse_args()
    try:
        if args.command == "init":
            print(json.dumps(initialize_packet(args.output_dir), indent=2))
            return
        if args.command == "finalize":
            receipt = finalize_measured_campaign(args.run_dir)
            output = args.output or str(
                Path(args.run_dir) / "campaign-receipt.json"
            )
            destination = save_closed_loop(receipt, output)
            print(json.dumps({
                "receipt": str(destination),
                "mode": receipt["mode"],
                "loop_closed": receipt["round_transition"]["loop_closed"],
                "nomination": receipt["follow_up"],
                "integrity": receipt["integrity"],
            }, indent=2))
            return

        spec = TEM1AssaySpec.load(args.config)
        if args.command == "confirm-expression":
            evidence = ExpressionEvidence.from_csv(args.evidence)
            verdict = confirm_expression(evidence, spec)
            destination = save_analysis(verdict, args.output)
            print(json.dumps({
                "confirmation": str(destination),
                "verdict": verdict,
                "screening_allowed": verdict["passed"],
            }, indent=2))
            if not verdict["passed"]:
                raise SystemExit(2)
            return

        compounds = load_compounds(args.compounds)
        if args.command == "round1-plan":
            plan = build_round1_plan(compounds, spec, n_select=args.select)
            destination = plan.save(args.output)
            verdict = plan.verify(compounds, spec)
            print(json.dumps({
                "plan": str(destination),
                "verification": verdict,
                "note": (
                    "physical execution remains blocked"
                    if not verdict["execution_allowed"]
                    else "organizer-confirmed protocol is executable"
                ),
            }, indent=2))
            return

        if args.command == "analyze":
            plan = TEM1RoundPlan.load(args.plan)
            plate = KineticPlate.from_csv(args.reader)
            analysis = analyze_round(plan, compounds, spec, plate)
            destination = save_analysis(analysis, args.output)
            print(json.dumps({
                "analysis": str(destination),
                "assay_qc": analysis["assay_qc"],
                "model_updated": analysis["world_model"]["updated"],
            }, indent=2))
            if not analysis["assay_qc"]["passed"]:
                raise SystemExit(2)
            return

        if args.command == "prove-loop":
            analysis_path = Path(args.analysis)
            round2_plan_path = Path(args.round2_plan)
            analysis = json.loads(analysis_path.read_text())
            plan = TEM1RoundPlan.load(round2_plan_path)
            proof = build_round_transition(
                analysis,
                plan,
                compounds,
                spec,
                source_artifacts={
                    "round1_analysis": {
                        "path": str(analysis_path),
                        "sha256": file_sha256(analysis_path),
                    },
                    "round2_plan": {
                        "path": str(round2_plan_path),
                        "sha256": file_sha256(round2_plan_path),
                    },
                },
            )
            destination = save_analysis(proof, args.output)
            print(json.dumps({
                "proof": str(destination),
                "loop_closed": proof["loop_closed"],
                "plate_change": proof["plate_change"],
                "verification": proof["verification"],
                "integrity": proof["integrity"],
            }, indent=2))
            return

        analysis = json.loads(Path(args.analysis).read_text())
        plan = build_round2_plan(
            analysis, compounds, spec, top_k=args.top_k
        )
        destination = plan.save(args.output)
        verdict = plan.verify(compounds, spec)
        print(json.dumps({
            "plan": str(destination),
            "selection_rationale": plan.selection_rationale,
            "verification": verdict,
        }, indent=2))
    except (TEM1Error, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"TEM-1 workflow failed closed: {exc}\n")


if __name__ == "__main__":
    main()
