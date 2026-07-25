"""Fail-closed Google ADK function tools for the TEM-1 file workflow."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from bayhack.tem1 import (
    ExpressionEvidence,
    KineticPlate,
    TEM1AssaySpec,
    TEM1Error,
    TEM1RoundPlan,
    analyze_round,
    build_round1_plan,
    build_round2_plan,
    confirm_expression,
    load_compounds,
    save_analysis,
)
from bayhack.tem1_cli import initialize_packet


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ERRORS = (
    TEM1Error,
    OSError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    json.JSONDecodeError,
)


def _artifact_root() -> Path:
    configured = Path(os.environ.get("BAYHACK_RUN_DIR", "run_artifacts"))
    root = configured if configured.is_absolute() else REPOSITORY_ROOT / configured
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _artifact_path(relative_path: str, *, must_exist: bool = False) -> Path:
    """Resolve a path inside the configured event-artifact directory."""
    supplied = Path(relative_path)
    if supplied.is_absolute():
        raise TEM1Error("ADK tool paths must be relative to BAYHACK_RUN_DIR")
    root = _artifact_root()
    resolved = (root / supplied).resolve()
    if resolved != root and root not in resolved.parents:
        raise TEM1Error("ADK tool path escapes BAYHACK_RUN_DIR")
    if must_exist and not resolved.is_file():
        raise TEM1Error(f"required event artifact does not exist: {relative_path}")
    return resolved


def _relative(path: str | Path) -> str:
    return str(Path(path).resolve().relative_to(_artifact_root()))


def _run_tool(operation: str, action: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return {"ok": True, "operation": operation, **action()}
    except EXPECTED_ERRORS as exc:
        return {
            "ok": False,
            "operation": operation,
            "error": str(exc),
            "physical_execution_allowed": False,
        }


def initialize_track_a_packet(output_directory: str = "tem1") -> dict[str, Any]:
    """Create the unconfirmed Track A assay config and 95-row compound template.

    Args:
        output_directory: Directory relative to BAYHACK_RUN_DIR.

    Returns:
        Structured paths for the new packet. Physical execution remains locked.
    """

    def action() -> dict[str, Any]:
        destination = _artifact_path(output_directory)
        packet = initialize_packet(destination)
        return {
            "packet": {name: _relative(path) for name, path in packet.items()},
            "physical_execution_allowed": False,
            "next_required_fact": (
                "replace compound placeholders and fill only organizer-confirmed "
                "physical protocol fields"
            ),
        }

    return _run_tool("initialize_track_a_packet", action)


def inspect_track_a_inputs(
    config_file: str,
    compounds_file: str,
) -> dict[str, Any]:
    """Validate assay configuration and compound-library files before planning.

    Args:
        config_file: Assay JSON path relative to BAYHACK_RUN_DIR.
        compounds_file: Compound CSV path relative to BAYHACK_RUN_DIR.

    Returns:
        Validation, library size, prioritization coverage, and physical readiness.
    """

    def action() -> dict[str, Any]:
        spec = TEM1AssaySpec.load(_artifact_path(config_file, must_exist=True))
        compounds = load_compounds(
            _artifact_path(compounds_file, must_exist=True)
        )
        priorities = [
            compound for compound in compounds
            if compound.priority_score is not None
        ]
        valid_sources = [
            compound for compound in compounds
            if compound.source_well is not None
        ]
        return {
            "assay_spec_valid": spec.verify()["passed"],
            "compound_count": len(compounds),
            "priority_scores_present": len(priorities),
            "priority_scores_complete": len(priorities) == len(compounds),
            "valid_source_wells": len(valid_sources),
            "physical_missing": spec.physical_missing(),
            "physical_execution_allowed": spec.physical_ready,
        }

    return _run_tool("inspect_track_a_inputs", action)


def confirm_tem1_expression(
    config_file: str,
    evidence_file: str,
    output_file: str = "tem1/expression-confirmation.json",
) -> dict[str, Any]:
    """Evaluate replicated sfGFP evidence against the no-template control.

    Args:
        config_file: Assay JSON path relative to BAYHACK_RUN_DIR.
        evidence_file: CSV with role, replicate, and value columns.
        output_file: JSON result path relative to BAYHACK_RUN_DIR.

    Returns:
        The expression verdict. A failed gate explicitly blocks screening.
    """

    def action() -> dict[str, Any]:
        spec = TEM1AssaySpec.load(_artifact_path(config_file, must_exist=True))
        evidence = ExpressionEvidence.from_csv(
            _artifact_path(evidence_file, must_exist=True)
        )
        verdict = confirm_expression(evidence, spec)
        destination = save_analysis(verdict, _artifact_path(output_file))
        return {
            "output_file": _relative(destination),
            "screening_allowed": verdict["passed"],
            "physical_execution_allowed": False,
            "verdict": verdict,
        }

    return _run_tool("confirm_tem1_expression", action)


def design_round_1(
    config_file: str,
    compounds_file: str,
    output_file: str = "tem1/round1-plan.json",
    selection_count: int = 0,
) -> dict[str, Any]:
    """Build and verify a balanced first-round TEM-1 plate map.

    Args:
        config_file: Assay JSON path relative to BAYHACK_RUN_DIR.
        compounds_file: Compound CSV path relative to BAYHACK_RUN_DIR.
        output_file: Plate-plan JSON path relative to BAYHACK_RUN_DIR.
        selection_count: Number of compounds, or zero for plate capacity.

    Returns:
        The saved plate map, selection rationale, and execution gate.
    """

    def action() -> dict[str, Any]:
        if selection_count < 0:
            raise TEM1Error("selection_count must be zero or positive")
        spec = TEM1AssaySpec.load(_artifact_path(config_file, must_exist=True))
        compounds = load_compounds(
            _artifact_path(compounds_file, must_exist=True)
        )
        plan = build_round1_plan(
            compounds,
            spec,
            n_select=selection_count or None,
        )
        verdict = plan.verify(compounds, spec)
        destination = plan.save(_artifact_path(output_file))
        return {
            "output_file": _relative(destination),
            "round_id": 1,
            "candidate_wells": sum(
                assignment.role == "candidate"
                for assignment in plan.assignments
            ),
            "selection_rationale": plan.selection_rationale,
            "verification": verdict,
            "physical_execution_allowed": verdict["execution_allowed"],
        }

    return _run_tool("design_round_1", action)


def analyze_reader_kinetics(
    config_file: str,
    compounds_file: str,
    plan_file: str,
    reader_file: str,
    output_file: str = "tem1/round1-analysis.json",
) -> dict[str, Any]:
    """Analyze timestamped A490 reader evidence against a saved plate plan.

    Args:
        config_file: Assay JSON path relative to BAYHACK_RUN_DIR.
        compounds_file: Compound CSV path relative to BAYHACK_RUN_DIR.
        plan_file: Verified plate-plan JSON path relative to BAYHACK_RUN_DIR.
        reader_file: CSV with well, time_s, and value columns.
        output_file: Analysis JSON path relative to BAYHACK_RUN_DIR.

    Returns:
        Assay QC, ranked candidates, provenance, and the round-2 gate.
    """

    def action() -> dict[str, Any]:
        spec = TEM1AssaySpec.load(_artifact_path(config_file, must_exist=True))
        compounds = load_compounds(
            _artifact_path(compounds_file, must_exist=True)
        )
        plan = TEM1RoundPlan.load(_artifact_path(plan_file, must_exist=True))
        plate = KineticPlate.from_csv(
            _artifact_path(reader_file, must_exist=True)
        )
        analysis = analyze_round(plan, compounds, spec, plate)
        destination = save_analysis(analysis, _artifact_path(output_file))
        qc = analysis["assay_qc"]
        return {
            "output_file": _relative(destination),
            "round_id": plan.round_id,
            "measurement": analysis["measurement"],
            "assay_qc": qc,
            "top_candidates": analysis["candidates"][:5],
            "round2_allowed": (
                plan.round_id == 1
                and qc["passed"]
                and analysis["world_model"]["updated"]
            ),
            "physical_execution_allowed": False,
        }

    return _run_tool("analyze_reader_kinetics", action)


def design_round_2(
    config_file: str,
    compounds_file: str,
    round1_analysis_file: str,
    output_file: str = "tem1/round2-plan.json",
    top_compounds: int = 3,
) -> dict[str, Any]:
    """Build confirmation doses only from a passing round-1 analysis file.

    Args:
        config_file: Assay JSON path relative to BAYHACK_RUN_DIR.
        compounds_file: Compound CSV path relative to BAYHACK_RUN_DIR.
        round1_analysis_file: Saved round-1 analysis JSON.
        output_file: Round-2 plate-plan JSON path relative to BAYHACK_RUN_DIR.
        top_compounds: Number of measured candidates to confirm.

    Returns:
        A verified adaptive plate map or a fail-closed error.
    """

    def action() -> dict[str, Any]:
        spec = TEM1AssaySpec.load(_artifact_path(config_file, must_exist=True))
        compounds = load_compounds(
            _artifact_path(compounds_file, must_exist=True)
        )
        analysis_path = _artifact_path(
            round1_analysis_file, must_exist=True
        )
        round1_analysis = json.loads(analysis_path.read_text())
        plan = build_round2_plan(
            round1_analysis,
            compounds,
            spec,
            top_k=top_compounds,
        )
        verdict = plan.verify(compounds, spec)
        destination = plan.save(_artifact_path(output_file))
        return {
            "output_file": _relative(destination),
            "round_id": 2,
            "selection_rationale": plan.selection_rationale,
            "verification": verdict,
            "physical_execution_allowed": verdict["execution_allowed"],
        }

    return _run_tool("design_round_2", action)
