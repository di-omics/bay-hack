"""Physical volume and CV evidence must be measured, strict, and traceable."""
import csv
import json

import pytest

from bayhack.assay import LiquidHandlingAssay
from bayhack.loop import Bench, DBTLLoop
from bayhack.verification import (
    CsvVolumeGate,
    JsonCvCheckpoint,
    VerificationError,
)


def write_volume_csv(path, *, noisy=False):
    rows = [
        ("standard", "A1", 2, 140),
        ("standard", "A2", 5, 200),
        ("standard", "A3", 10, 300),
        ("standard", "A4", 20, 500),
        ("standard", "A5", 50, 1100),
    ]
    test_signals = (120, 300, 520) if noisy else (296, 300, 304)
    rows.extend(
        ("test", f"{row}1", 10, signal)
        for row, signal in zip("BCD", test_signals)
    )
    rows.extend([
        ("test", "B2", 20, 492),
        ("test", "C2", 20, 500),
        ("test", "D2", 20, 508),
    ])
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["kind", "well", "target_ul", "rfu"])
        writer.writerows(rows)
    return path


def write_cv_json(path, *, passed=True, confidence=0.97):
    path.write_text(json.dumps({
        "checkpoint": "plate-present-no-spill",
        "passed": passed,
        "note": "plate seated and wells intact",
        "inspector": "lab-cv",
        "confidence": confidence,
        "trace_id": "zeon-frame-0042",
    }))
    return path


def test_volume_csv_gate_checks_linearity_accuracy_and_cv(tmp_path):
    verdict = CsvVolumeGate(write_volume_csv(tmp_path / "volume.csv")).evaluate()
    assert verdict["passed"]
    assert verdict["r2"] == pytest.approx(1.0)
    assert verdict["tier"] == "liquid_tested"
    assert verdict["provenance"] == "measured:volume-csv"
    assert all(group["passed"] for group in verdict["groups"])
    assert verdict["evidence"]["standard_points"] == 5
    assert verdict["evidence"]["test_points"] == 6
    assert len(verdict["evidence"]["sha256"]) == 64


def test_volume_csv_gate_fails_high_variance_dispenses(tmp_path):
    verdict = CsvVolumeGate(
        write_volume_csv(tmp_path / "bad-volume.csv", noisy=True)
    ).evaluate()
    assert not verdict["passed"]
    assert verdict["tier"] == "failed"
    assert any("10 uL" in reason for reason in verdict["reasons"])


def test_volume_csv_gate_refuses_incomplete_standards(tmp_path):
    path = tmp_path / "short.csv"
    path.write_text(
        "kind,target_ul,rfu\nstandard,2,140\nstandard,5,200\n"
        "test,2,140\ntest,2,141\ntest,2,139\n"
    )
    with pytest.raises(VerificationError, match="three distinct"):
        CsvVolumeGate(path).evaluate()


def test_cv_json_requires_traceable_evidence_and_confidence(tmp_path):
    path = write_cv_json(tmp_path / "cv.json")
    verdict = JsonCvCheckpoint(path).evaluate()
    assert verdict["passed"]
    assert verdict["provenance"] == "measured:cv-json"
    assert verdict["evidence"]["trace_id"] == "zeon-frame-0042"
    assert len(verdict["evidence"]["sha256"]) == 64

    low_path = write_cv_json(tmp_path / "low.json", confidence=0.4)
    low = JsonCvCheckpoint(low_path).evaluate()
    assert not low["passed"]
    assert any("confidence" in reason for reason in low["reasons"])

    no_evidence = tmp_path / "no-evidence.json"
    no_evidence.write_text(json.dumps({
        "checkpoint": "plate-present",
        "passed": True,
        "note": "plate visible",
        "inspector": "operator",
    }))
    with pytest.raises(VerificationError, match="image or a trace_id"):
        JsonCvCheckpoint(no_evidence).evaluate()


def test_cv_path_pattern_uses_verified_plan_context(tmp_path):
    path = write_cv_json(tmp_path / "cv_B1_1.json")
    plan = LiquidHandlingAssay().plan(1, "seed", 0.2)
    adapter = JsonCvCheckpoint(tmp_path / "cv_{well}_{run_id}.json")
    assert adapter(plan=plan)["evidence"]["path"] == str(path)


def test_measured_gates_earn_hardware_validated_ledger_label(tmp_path):
    volume = CsvVolumeGate(write_volume_csv(tmp_path / "volume.csv"))
    cv = JsonCvCheckpoint(write_cv_json(tmp_path / "cv.json"))
    bench = Bench()
    bench.measurement_provenance = "measured:fixture-reader"
    loop = DBTLLoop(bench, budget=3, rhodamine_fn=volume, cv_fn=cv)
    loop.run(verbose=False)
    assert all(
        record.physical_verification["provenance"] == "hardware-validated"
        for record in loop.ledger.records
    )
    assert loop.ledger.records[0].physical_verification["rhodamine"][
        "evidence"
    ]["destination"] == "B1"


def test_manual_hardware_label_cannot_bypass_measured_gates():
    bench = Bench(verification_provenance="hardware-validated")
    loop = DBTLLoop(bench, budget=3)
    loop.run(verbose=False)
    assert all(
        record.physical_verification["provenance"] == "unverified"
        for record in loop.ledger.records
    )
