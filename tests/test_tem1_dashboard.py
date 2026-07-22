"""The Track A stage surface stays specific, safe, and dependency-free."""
import json

import pytest

from bayhack.tem1 import run_simulated_closed_loop, save_closed_loop
from bayhack.tem1_dashboard import (
    PAGE,
    TEM1ReceiptError,
    replay_tem1_receipt,
    run_expression_refusal,
)


def test_page_tells_the_announced_track_a_story():
    for phrase in (
        "TEM-1 closed loop",
        "Produce the antibiotic-resistance enzyme",
        "confirm expression",
        "Round 1 plate",
        "Z-prime",
        "Round 2 confirmation",
        "Prove expression refusal",
        "uncertainty",
        "#5cae5a",
    ):
        assert phrase.lower() in PAGE.lower()


def test_expression_refusal_stops_screen_and_model_update():
    refusal = run_expression_refusal()
    assert refusal["status"] == "REFUSED"
    assert not refusal["confirmation"]["passed"]
    assert not refusal["compound_screen"]["executed"]
    assert refusal["compound_screen"]["wells_read"] == 0
    assert not refusal["world_model"]["updated"]
    assert not refusal["round2"]["planned"]
    assert refusal["robot_commands_after_failure"] == 0


def test_tem1_receipt_replay_is_zero_motion(tmp_path):
    receipt = run_simulated_closed_loop(seed=17)
    path = save_closed_loop(receipt, tmp_path / "tem1-trust.json")
    replay = replay_tem1_receipt(path)
    assert replay["mode"] == "receipt-replay"
    assert replay["hardware_commands_issued_by_replay"] == 0
    assert replay["protein_synthesis"]["confirmation"]["passed"]
    assert len(replay["rounds"]) == 2
    assert replay["follow_up"]["executed"]


def test_non_tem1_receipt_is_refused(tmp_path):
    path = tmp_path / "wrong.json"
    path.write_text(json.dumps({"target": "other", "rounds": [{}, {}]}))
    with pytest.raises(TEM1ReceiptError, match="target"):
        replay_tem1_receipt(path)


def test_tampered_tem1_receipt_is_refused(tmp_path):
    receipt = run_simulated_closed_loop(seed=17)
    receipt["follow_up"]["mean_inhibition_pct"] = 100.0
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(receipt))
    with pytest.raises(TEM1ReceiptError, match="integrity"):
        replay_tem1_receipt(path)
