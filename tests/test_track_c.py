"""Track C tube access stays verified, recoverable, and fail-closed."""
import json

import pytest

from bayhack.track_c import (
    CapState,
    EvidenceFileCapVerifier,
    SimulatedTubeCell,
    TrackCError,
    VerifiedTubeAccessController,
    run_simulated_tube_access,
    save_track_c_receipt,
    seal_track_c_receipt,
    verify_track_c_receipt,
)


def test_nominal_tube_access_verifies_open_and_closed():
    receipt = run_simulated_tube_access("none")
    assert receipt["status"] == "VERIFIED_COMPLETE"
    assert receipt["gates"] == {
        "open_verified": True,
        "pipetting_allowed": True,
        "closed_verified": True,
    }
    assert receipt["verification"]["open"]["state"] == "uncapped"
    assert receipt["verification"]["closed"]["state"] == "capped"
    assert receipt["execution"]["physical_hardware_commands"] == 0
    assert verify_track_c_receipt(receipt)


def test_partial_uncapping_is_seen_and_recovered_before_pipetting():
    receipt = run_simulated_tube_access("partial_uncap")
    assert receipt["status"] == "VERIFIED_COMPLETE"
    assert receipt["recoveries"] == 1
    open_checks = [
        event for event in receipt["events"]
        if event["state"] == "verify_open"
        and event["kind"] == "physical_verification"
    ]
    assert [event["passed"] for event in open_checks] == [False, True]
    handoff = next(
        event for event in receipt["events"]
        if event["detail"].startswith("verified tube opening unlocked")
    )
    assert handoff["sequence"] > open_checks[-1]["sequence"]


@pytest.mark.parametrize(
    "fault",
    ["cap_slip", "rotated_tube", "ambiguous_close"],
)
def test_recoverable_faults_finish_with_verified_closure(fault):
    receipt = run_simulated_tube_access(fault)
    assert receipt["status"] == "VERIFIED_COMPLETE"
    assert receipt["recoveries"] >= 1
    assert receipt["gates"]["closed_verified"]
    assert verify_track_c_receipt(receipt)


def test_persistent_open_ambiguity_blocks_liquid_handling():
    receipt = run_simulated_tube_access("persistent_open_ambiguity")
    assert receipt["status"] == "STOPPED_SAFE"
    assert not receipt["gates"]["open_verified"]
    assert not receipt["gates"]["pipetting_allowed"]
    assert not receipt["gates"]["closed_verified"]
    assert not any(
        event["state"] == "present_for_pipetting"
        for event in receipt["events"]
    )
    assert verify_track_c_receipt(receipt)


def test_receipt_integrity_and_invariants_detect_tampering(tmp_path):
    receipt = run_simulated_tube_access("none")
    receipt["gates"]["open_verified"] = False
    assert not verify_track_c_receipt(receipt)
    receipt = seal_track_c_receipt(receipt)
    assert not verify_track_c_receipt(receipt)
    with pytest.raises(TrackCError, match="invalid integrity"):
        save_track_c_receipt(receipt, tmp_path / "not-written.json")
    assert not verify_track_c_receipt({"events": ["not-an-event"]})


def test_evidence_file_observer_preserves_measured_provenance(tmp_path):
    evidence = tmp_path / "cap-observations.json"
    evidence.write_text(json.dumps({
        "observations": [
            {
                "checkpoint": "initial",
                "state": "capped",
                "confidence": 0.97,
                "provenance": "measured:camera",
                "evidence": {"image_sha256": "abc"},
            },
            {
                "checkpoint": "open",
                "state": "uncapped",
                "confidence": 0.95,
                "provenance": "measured:camera",
                "evidence": {"image_sha256": "def"},
            },
            {
                "checkpoint": "closed",
                "state": "capped",
                "confidence": 0.96,
                "provenance": "measured:camera",
                "evidence": {"image_sha256": "ghi"},
            },
        ]
    }))
    cell = SimulatedTubeCell()
    receipt = VerifiedTubeAccessController(
        cell,
        EvidenceFileCapVerifier(evidence),
    ).run()
    assert receipt["status"] == "VERIFIED_COMPLETE"
    assert receipt["verification"]["open"]["provenance"] == "measured:camera"
    assert receipt["verification"]["closed"]["evidence"]["image_sha256"] == "ghi"


def test_evidence_file_observer_rejects_wrong_checkpoint(tmp_path):
    evidence = tmp_path / "wrong.json"
    evidence.write_text(json.dumps({
        "observations": [{
            "checkpoint": "open",
            "state": CapState.UNCAPPED.value,
            "confidence": 0.99,
            "provenance": "measured:camera",
        }]
    }))
    verifier = EvidenceFileCapVerifier(evidence)
    with pytest.raises(TrackCError, match="expected initial"):
        verifier.observe("initial")


def test_camera_exception_becomes_ambiguous_safe_stop():
    class BrokenCamera:
        def observe(self, checkpoint):
            raise OSError("camera disconnected")

    cell = SimulatedTubeCell()
    receipt = VerifiedTubeAccessController(cell, BrokenCamera()).run()
    assert receipt["status"] == "STOPPED_SAFE"
    assert not receipt["gates"]["pipetting_allowed"]
    first = receipt["events"][0]
    assert first["evidence"]["provenance"] == "system:observer-error"
    assert verify_track_c_receipt(receipt)


def test_fixture_stays_parametric():
    source = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "hardware"
        / "tube_nest.scad"
    ).read_text()
    for parameter in (
        "tube_od_mm",
        "radial_clearance_mm",
        "split_width_mm",
        "cap_park_d_mm",
    ):
        assert parameter in source
