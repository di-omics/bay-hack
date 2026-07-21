"""Dashboard tests -- stdlib only, so these run in CI as part of the sim gate."""
import json

import pytest

from bayhack.dashboard import PAGE, ReceiptReplayError, replay_receipt, run_loop
from bayhack.loop import Bench, DBTLLoop


def test_run_loop_converges_and_has_shape():
    d = run_loop(seed=7)
    assert d["converged"] is True
    assert d["runs_used"] < 26                     # beats the grid sweep
    assert d["rounds"]
    assert all({"k", "x", "fluor", "r2", "decision"} <= set(r) for r in d["rounds"])
    assert d["rounds"][-1]["decision"] == "ACCEPT"  # ends on a promoted result
    assert len(d["rounds"]) == d["runs_used"]
    assert [r["phase"] for r in d["rounds"][:2]] == ["seed", "seed"]
    assert all({"well", "stock_ul", "diluent_ul", "plan_verified"} <= set(r)
               for r in d["rounds"])
    assert d["follow_up"]["executed"]
    assert d["follow_up"]["action"]["destination"] == "H12"
    assert d["rounds"][-1]["target_met"]
    assert d["ledger"]["records"][-1]["acceptance"]["target_met"]


def test_page_carries_house_style_and_grounded_facts():
    for s in ("bay-hack", "world model", "liquid-handling", "Rhodamine", "plr-mcp",
              "conformal", "follow-up", "#5cae5a", "lh-plate",
              "prove refusal", "/api/refusal", "objective + uncertainty",
              "current decision"):
        assert s.lower() in PAGE.lower(), f"dashboard page missing {s!r}"


def test_saved_receipt_replays_without_simulator_ground_truth(tmp_path):
    loop = DBTLLoop(Bench(), budget=20)
    loop.run(verbose=False)
    path = loop.ledger.save(tmp_path / "trust.json")
    payload = json.loads(path.read_text())
    payload["records"][-1]["measurement"]["provenance"] = "measured:camera"
    payload["records"][-1]["measurement"]["evidence"] = {"well": "G1"}
    path.write_text(json.dumps(payload))
    replay = replay_receipt(path)
    assert replay["mode"] == "receipt-replay"
    assert replay["x_star"] is None
    assert replay["converged"]
    assert replay["rounds"][-1]["measurement_provenance"] == "measured:camera"
    assert replay["follow_up"]["action"]["destination"] == "H12"
    assert replay["best_y"] == replay["rounds"][-1]["best_y"]


def test_empty_receipt_is_refused(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text('{"records": []}')
    with pytest.raises(ReceiptReplayError, match="no experiment records"):
        replay_receipt(path)
