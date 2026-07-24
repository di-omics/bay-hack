"""The readiness audit stays zero-motion, fail-closed, and reproducible."""
import json

from bayhack.loop import Bench, DBTLLoop
from bayhack.preflight import (
    local_repo_candidates,
    run_preflight,
    save_preflight,
)
from test_verification import write_cv_json, write_volume_csv


def by_name(report):
    return {check["name"]: check for check in report["checks"]}


def test_repo_candidates_cover_sibling_and_categorized_layouts(tmp_path):
    root = tmp_path / "Projects" / "apps-and-web" / "bay-hack"
    candidates = local_repo_candidates(root)
    assert root.parent / "plr-mcp" in candidates["plr-mcp"]
    assert (
        tmp_path / "Projects" / "lab-automation" / "plr-mcp"
        in candidates["plr-mcp"]
    )
    assert (
        tmp_path
        / "Projects"
        / "research-and-ml"
        / "ml-bio-eval"
        / "lab-world-model"
        in candidates["labworld"]
    )


def test_default_preflight_proves_the_guaranteed_demo_without_motion():
    report = run_preflight()
    checks = by_name(report)
    assert report["readiness"] == "SIMULATION_READY"
    assert report["ready"]
    assert report["core_ready"]
    assert not report["physical_evidence_ready"]
    assert not report["ready_for_motion"]
    assert report["motion_commands_issued"] == 0
    assert checks["pre-act-refusal"]["status"] == "PASS"
    assert checks["simulation-fallback"]["status"] == "PASS"
    assert checks["tem1-track-a-fallback"]["status"] == "PASS"
    assert checks["tem1-track-a-fallback"]["evidence"]["target"] == \
        "TEM-1 beta-lactamase"
    assert checks["physical-volume-gate"]["status"] == "WARN"


def test_preflight_accepts_complete_physical_evidence_bundle(tmp_path):
    reader = tmp_path / "reader.csv"
    reader.write_text("well,value\nB1,0.91\n")
    volume = write_volume_csv(tmp_path / "volume.csv")
    cv = write_cv_json(tmp_path / "cv.json")

    loop = DBTLLoop(Bench(), budget=20)
    loop.run(verbose=False)
    receipt = loop.ledger.save(tmp_path / "trust.json")

    report = run_preflight(
        reader_csv=reader,
        reader_well="B1",
        volume_csv=volume,
        cv_json=cv,
        receipt=receipt,
    )
    checks = by_name(report)
    assert report["readiness"] == "PHYSICAL_EVIDENCE_READY"
    assert report["physical_evidence_ready"]
    assert checks["reader-measurement"]["status"] == "PASS"
    assert checks["physical-volume-gate"]["status"] == "PASS"
    assert checks["physical-cv-gate"]["status"] == "PASS"
    assert checks["stage-receipt"]["status"] == "PASS"
    assert report["motion_commands_issued"] == 0


def test_explicit_invalid_evidence_makes_preflight_not_ready(tmp_path):
    report = run_preflight(volume_csv=tmp_path / "missing.csv")
    assert report["readiness"] == "NOT_READY"
    assert not report["ready"]
    assert by_name(report)["physical-volume-gate"]["status"] == "FAIL"


def test_preflight_report_is_saved_as_json(tmp_path):
    report = run_preflight()
    destination = save_preflight(report, tmp_path / "preflight.json")
    saved = json.loads(destination.read_text())
    assert saved["mode"] == "zero-motion"
    assert saved["motion_commands_issued"] == 0
