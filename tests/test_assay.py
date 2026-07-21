"""Liquid-handling plans and trust receipts are part of the CI gate."""
import json
from dataclasses import replace

from bayhack.assay import LiquidHandlingAssay
from bayhack.loop import Bench, DBTLLoop


def test_plan_has_real_wells_volumes_and_unique_tips():
    assay = LiquidHandlingAssay()
    plan = assay.plan(run_id=1, phase="seed", design_x=0.2)
    assert plan.destination == "B1"
    assert plan.stock_ul == 8.0
    assert plan.diluent_ul == 32.0
    assert {transfer.source for transfer in plan.transfers} == {"A1", "A2"}
    assert len({transfer.tip for transfer in plan.transfers}) == 2
    assert assay.verify(plan)["passed"]


def test_seed_runs_pass_physical_gates_before_training():
    loop = DBTLLoop(Bench(), budget=8)
    history = loop.run(verbose=False)
    assert [record.phase for record in history[:2]] == ["seed", "seed"]
    assert len(loop.wm.xs) == len(history)
    assert all(record.plan_verified for record in history)
    assert all(record.r2 >= 0.995 for record in history)
    assert [record.destination for record in history[:2]] == ["B1", "C1"]


def test_track_a_follow_up_is_verified_and_executed():
    bench = Bench()
    loop = DBTLLoop(bench, budget=20)
    loop.run(verbose=False)
    assert loop.follow_up is not None
    assert loop.follow_up["verification"]["passed"]
    assert loop.follow_up["executed"]
    assert loop.follow_up["action"]["destination"] == "H12"
    assert len(bench.executed_follow_ups) == 1


def test_trust_ledger_labels_modeled_measurements(tmp_path):
    loop = DBTLLoop(Bench(), budget=20)
    loop.run(verbose=False)
    path = loop.ledger.save(tmp_path / "trust.json")
    payload = json.loads(path.read_text())
    assert len(payload["records"]) == loop.runs_used
    assert all(
        record["measurement"]["provenance"] == "modeled"
        for record in payload["records"]
    )
    assert all(
        record["physical_verification"]["provenance"] == "modeled"
        for record in payload["records"]
    )
    assert payload["follow_up"]["execution"]["passed"]


def test_trust_ledger_preserves_measurement_source_evidence():
    bench = Bench()
    bench.measurement_provenance = "measured:fixture"
    bench.measurement_evidence = {"well": "fixture", "source": "test reader"}
    loop = DBTLLoop(bench, budget=3)
    loop.run(verbose=False)
    measurement = loop.ledger.records[0].measurement
    assert measurement["provenance"] == "measured:fixture"
    assert measurement["evidence"]["source"] == "test reader"


def test_invalid_sub_minimum_transfer_is_rejected():
    assay = LiquidHandlingAssay(total_volume_ul=40.0, min_transfer_ul=1.0)
    plan = assay.plan(run_id=1, phase="optimize", design_x=0.01)
    verdict = assay.verify(plan)
    assert not verdict["passed"]
    assert "below 1 uL" in verdict["reasons"][0]


def test_transfer_destination_must_match_verified_plan():
    assay = LiquidHandlingAssay()
    plan = assay.plan(run_id=1, phase="safety-check", design_x=0.2)
    bad_transfer = replace(plan.transfers[0], destination="C1")
    unsafe = replace(plan, transfers=(bad_transfer, *plan.transfers[1:]))
    verdict = assay.verify(unsafe)
    assert not verdict["passed"]
    assert any("destination does not match" in reason for reason in verdict["reasons"])


def test_failed_physical_gate_never_updates_world_model():
    def failed_rhodamine(_series):
        return {"passed": False, "r2": 0.2}

    loop = DBTLLoop(Bench(), budget=4, rhodamine_fn=failed_rhodamine)
    history = loop.run(verbose=False)
    assert len(history) == 4
    assert loop.wm.xs == []
    assert all(not record.model_updated for record in history)
    assert all(record.decision == "ESCALATE" for record in history)
    assert loop.follow_up is None
    assert all(
        record.world_model["updated"] is False
        for record in loop.ledger.records
    )
