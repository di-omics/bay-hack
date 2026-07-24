"""Zero-motion readiness audit for the bay-hack demo and physical evidence.

This command never initializes, homes, or actuates venue hardware. It proves the
fallback, refusal path, benchmark, and any supplied evidence files from one
terminal command:

    python -m bayhack.preflight --output run_artifacts/preflight.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .benchmark import GRID, run_benchmark
from .loop import Bench, DBTLLoop
from .measurements import (
    CameraWellMeasurement,
    CsvWellMeasurement,
    LinearSignalCalibration,
    PlateCalibration,
)
from .safety import run_refusal
from .tem1 import run_simulated_closed_loop, verify_receipt_integrity
from .verification import CsvVolumeGate, JsonCvCheckpoint


ROOT = Path(__file__).resolve().parents[1]


def local_repo_candidates(root: Path = ROOT) -> dict[str, tuple[Path, ...]]:
    """Return portable checkout locations without assuming a home directory."""
    project_hub = root.parents[1]
    return {
        "plr-mcp": (
            root.parent / "plr-mcp",
            project_hub / "lab-automation" / "plr-mcp",
        ),
        "plr-epigenome": (
            root.parent / "plr-epigenome",
            project_hub / "lab-automation" / "plr-epigenome",
        ),
        "labworld": (
            root.parent / "ml-bio-eval" / "lab-world-model",
            project_hub
            / "research-and-ml"
            / "ml-bio-eval"
            / "lab-world-model",
        ),
        "plr-lab-robot": (
            root.parent / "plr-lab-robot",
            project_hub / "lab-automation" / "plr-lab-robot",
        ),
    }


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    status: str
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)


def _optional_input(
    checks: list[PreflightCheck],
    name: str,
    supplied: bool,
    function,
) -> bool:
    if not supplied:
        checks.append(PreflightCheck(
            name,
            "WARN",
            "not provided; collect this evidence at the venue",
        ))
        return False
    try:
        detail, evidence = function()
    except Exception as exc:
        checks.append(PreflightCheck(name, "FAIL", str(exc)))
        return False
    checks.append(PreflightCheck(name, "PASS", detail, evidence))
    return True


def run_preflight(
    *,
    reader_csv: str | Path | None = None,
    reader_well: str = "B1",
    reader_raw_low: float | None = None,
    reader_raw_high: float | None = None,
    camera_image: str | Path | None = None,
    camera_calibration: str | Path | None = None,
    camera_well: str = "B1",
    volume_csv: str | Path | None = None,
    cv_json: str | Path | None = None,
    receipt: str | Path | None = None,
) -> dict[str, Any]:
    """Return a machine-readable audit without touching hardware."""
    checks: list[PreflightCheck] = []

    python_ok = sys.version_info >= (3, 10)
    checks.append(PreflightCheck(
        "python",
        "PASS" if python_ok else "FAIL",
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    ))

    required_files = (
        "README.md",
        "OFFICIAL_TRACK_A_MATERIALS.md",
        "ZEON_NATIVE_INTEGRATION.md",
        "TEM1_TRACK_A.md",
        "ACCEPTANCE.md",
        "HOUSE_RULES.md",
        "HARDWARE_KIT.md",
        "MEASUREMENT_ADAPTERS.md",
        "VERIFICATION_ADAPTERS.md",
        "ONSITE_RUNBOOK.md",
        "bayhack/assay.py",
        "bayhack/loop.py",
        "bayhack/safety.py",
        "bayhack/tem1.py",
        "bayhack/verification.py",
    )
    missing = [name for name in required_files if not (ROOT / name).exists()]
    checks.append(PreflightCheck(
        "repository-contract",
        "FAIL" if missing else "PASS",
        f"missing: {', '.join(missing)}" if missing else "required files present",
        {"required_files": list(required_files)},
    ))

    refusal = run_refusal("tip_reuse")
    refusal_ok = (
        refusal["status"] == "REFUSED"
        and refusal["execution"]["commands_issued"] == 0
        and refusal["measurement"]["taken"] is False
        and refusal["world_model"]["updated"] is False
    )
    checks.append(PreflightCheck(
        "pre-act-refusal",
        "PASS" if refusal_ok else "FAIL",
        "unsafe tip reuse stopped before backend dispatch",
        {
            "commands_issued": refusal["execution"]["commands_issued"],
            "measurement_taken": refusal["measurement"]["taken"],
            "model_updated": refusal["world_model"]["updated"],
        },
    ))

    try:
        loop = DBTLLoop(Bench(), budget=20)
        history = loop.run(verbose=False)
        simulation_ok = bool(
            history
            and history[-1].decision == "ACCEPT"
            and loop.follow_up
            and loop.follow_up["executed"]
            and loop.follow_up["action"]["destination"] == "H12"
            and all(
                record.measurement["provenance"] == "modeled"
                for record in loop.ledger.records
            )
        )
        checks.append(PreflightCheck(
            "simulation-fallback",
            "PASS" if simulation_ok else "FAIL",
            f"closed loop used {loop.runs_used} runs and staged H12 follow-up",
            {
                "runs": loop.runs_used,
                "final_decision": history[-1].decision,
                "measurement_provenance": "modeled",
            },
        ))
    except Exception as exc:
        checks.append(PreflightCheck("simulation-fallback", "FAIL", str(exc)))

    try:
        benchmark = run_benchmark(seeds=range(1, 11))
        benchmark_ok = (
            benchmark["convergence_rate"] == 1.0
            and benchmark["avg_runs"] < GRID
        )
        checks.append(PreflightCheck(
            "benchmark",
            "PASS" if benchmark_ok else "FAIL",
            f"{benchmark['avg_runs']} average runs vs {GRID} grid runs",
            benchmark,
        ))
    except Exception as exc:
        checks.append(PreflightCheck("benchmark", "FAIL", str(exc)))

    try:
        tem1 = run_simulated_closed_loop(seed=17)
        expression = tem1["protein_synthesis"]["confirmation"]
        rounds = tem1["rounds"]
        tem1_ok = bool(
            expression["passed"]
            and len(rounds) == 2
            and all(round_data["assay_qc"]["passed"] for round_data in rounds)
            and all(
                round_data["world_model"]["updated"] for round_data in rounds
            )
            and tem1["follow_up"]["executed"]
            and tem1["follow_up"]["dose_response_monotonic"]
            and verify_receipt_integrity(tem1)
        )
        checks.append(PreflightCheck(
            "tem1-track-a-fallback",
            "PASS" if tem1_ok else "FAIL",
            "expression confirmed, two gated rounds, condition nominated",
            {
                "target": tem1["target"],
                "expression_fold": expression["fold_over_background"],
                "round1_z_prime": rounds[0]["assay_qc"]["z_prime"],
                "round2_z_prime": rounds[1]["assay_qc"]["z_prime"],
                "nominated_compound": tem1["follow_up"]["compound_id"],
                "inhibition_50_factor": (
                    tem1["follow_up"]["inhibition_50_factor_estimate"]
                ),
                "receipt_sha256": tem1["integrity"]["digest"],
                "provenance": "modeled",
            },
        ))
    except Exception as exc:
        checks.append(PreflightCheck("tem1-track-a-fallback", "FAIL", str(exc)))

    seam_modules = {
        "plr-mcp": "plr_mcp",
        "plr-epigenome": "tipseq_plr",
        "labworld": "labworld",
        "plr-lab-robot": "plr_lr",
    }
    seam_evidence = {
        name: importlib.util.find_spec(module) is not None
        for name, module in seam_modules.items()
    }
    repo_candidates = local_repo_candidates()
    local_paths = {
        name: next((path for path in paths if path.is_dir()), None)
        for name, paths in repo_candidates.items()
    }
    local_evidence = {
        name: path is not None for name, path in local_paths.items()
    }
    seam_available = {
        name: seam_evidence[name] or local_evidence[name]
        for name in seam_modules
    }
    seam_count = sum(seam_available.values())
    checks.append(PreflightCheck(
        "optional-repo-seams",
        "PASS" if seam_count == len(seam_available) else "WARN",
        (
            f"{seam_count}/{len(seam_available)} optional seams available; "
            f"{sum(seam_evidence.values())} importable, "
            f"{sum(local_evidence.values())} local checkouts"
        ),
        {
            "importable": seam_evidence,
            "local_checkout": local_evidence,
            "local_paths": {
                name: str(path) if path is not None else None
                for name, path in local_paths.items()
            },
            "available": seam_available,
        },
    ))

    measurement_ready = False
    if reader_csv is not None:
        def check_reader():
            if (reader_raw_low is None) != (reader_raw_high is None):
                raise ValueError("reader raw low and high must be supplied together")
            calibration = (
                LinearSignalCalibration(reader_raw_low, reader_raw_high)
                if reader_raw_low is not None else None
            )
            adapter = CsvWellMeasurement(reader_csv, calibration=calibration)
            value = adapter.read_well(reader_well)
            return (
                f"reader CSV produced {value:.4f} for {reader_well.upper()}",
                {"provenance": adapter.provenance, **adapter.last_evidence},
            )
        measurement_ready = _optional_input(
            checks, "reader-measurement", True, check_reader
        )
    elif camera_image is not None or camera_calibration is not None:
        def check_camera():
            if camera_image is None or camera_calibration is None:
                raise ValueError("camera image and calibration must be supplied together")
            calibration = PlateCalibration.load(camera_calibration)
            adapter = CameraWellMeasurement(camera_image, calibration)
            value = adapter.read_well(camera_well)
            return (
                f"camera produced {value:.4f} for {camera_well.upper()}",
                {"provenance": adapter.provenance, **adapter.last_evidence},
            )
        measurement_ready = _optional_input(
            checks, "camera-measurement", True, check_camera
        )
    else:
        _optional_input(checks, "physical-measurement", False, lambda: None)

    def check_volume():
        verdict = CsvVolumeGate(volume_csv).evaluate()
        if not verdict["passed"]:
            raise ValueError("; ".join(verdict["reasons"]))
        return (
            f"R2 {verdict['r2']:.5f}; accuracy and CV passed",
            verdict,
        )

    volume_ready = _optional_input(
        checks, "physical-volume-gate", volume_csv is not None, check_volume
    )

    def check_cv():
        verdict = JsonCvCheckpoint(cv_json).evaluate()
        if not verdict["passed"]:
            raise ValueError("; ".join(verdict["reasons"]))
        return (
            f"{verdict['checkpoint']} passed via {verdict['inspector']}",
            verdict,
        )

    cv_ready = _optional_input(
        checks, "physical-cv-gate", cv_json is not None, check_cv
    )

    def check_receipt():
        from .dashboard import replay_receipt
        replay = replay_receipt(receipt)
        provenance = replay["rounds"][-1]["measurement_provenance"]
        return (
            f"safe receipt replay loaded with {provenance}",
            {
                "path": str(receipt),
                "mode": replay["mode"],
                "runs": replay["runs_used"],
                "measurement_provenance": provenance,
            },
        )

    _optional_input(checks, "stage-receipt", receipt is not None, check_receipt)

    checks.append(PreflightCheck(
        "venue-motion",
        "WARN",
        "intentionally not initialized; confirm deck, E-stop owner, and safe speed on-site",
        {"commands_issued": 0},
    ))

    counts = {
        status: sum(check.status == status for check in checks)
        for status in ("PASS", "WARN", "FAIL")
    }
    physical_evidence_ready = measurement_ready and volume_ready and cv_ready
    core_names = {
        "python",
        "repository-contract",
        "pre-act-refusal",
        "simulation-fallback",
        "benchmark",
        "tem1-track-a-fallback",
    }
    core_ready = all(
        check.status == "PASS" for check in checks if check.name in core_names
    )
    readiness = (
        "NOT_READY" if counts["FAIL"]
        else "PHYSICAL_EVIDENCE_READY" if physical_evidence_ready
        else "SIMULATION_READY"
    )
    return {
        "schema_version": "1.0",
        "mode": "zero-motion",
        "readiness": readiness,
        "ready": counts["FAIL"] == 0,
        "core_ready": core_ready,
        "physical_evidence_ready": physical_evidence_ready,
        "ready_for_motion": False,
        "motion_commands_issued": 0,
        "summary": counts,
        "checks": [asdict(check) for check in checks],
    }


def save_preflight(report: dict[str, Any], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description="run the bay-hack zero-motion readiness audit"
    )
    parser.add_argument("--reader-csv")
    parser.add_argument("--reader-well", default="B1")
    parser.add_argument("--reader-raw-low", type=float)
    parser.add_argument("--reader-raw-high", type=float)
    parser.add_argument("--camera-image")
    parser.add_argument("--camera-calibration")
    parser.add_argument("--camera-well", default="B1")
    parser.add_argument("--volume-csv")
    parser.add_argument("--cv-json")
    parser.add_argument("--receipt")
    parser.add_argument("--output", default="run_artifacts/preflight.json")
    args = parser.parse_args()

    report = run_preflight(
        reader_csv=args.reader_csv,
        reader_well=args.reader_well,
        reader_raw_low=args.reader_raw_low,
        reader_raw_high=args.reader_raw_high,
        camera_image=args.camera_image,
        camera_calibration=args.camera_calibration,
        camera_well=args.camera_well,
        volume_csv=args.volume_csv,
        cv_json=args.cv_json,
        receipt=args.receipt,
    )
    destination = save_preflight(report, args.output)
    print("=" * 68)
    print("bay-hack preflight: zero-motion readiness audit")
    print("=" * 68)
    for check in report["checks"]:
        print(f"[{check['status']:4s}] {check['name']:24s} {check['detail']}")
    print("-" * 68)
    print(f"readiness           : {report['readiness']}")
    print(f"motion commands     : {report['motion_commands_issued']}")
    print(f"report              : {destination}")
    if not report["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
