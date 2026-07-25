"""The Track C stage surface stays specific, safe, and dependency-free."""
import json

import pytest

from bayhack.track_c import run_simulated_tube_access, save_track_c_receipt
from bayhack.track_c_dashboard import (
    PAGE,
    TrackCReceiptError,
    replay_track_c_receipt,
)


def test_page_tells_the_verified_tube_access_story():
    for phrase in (
        "TUBEPROOF",
        "Track C",
        "independently verifies that it is open",
        "Inject partial uncap",
        "Prove safe stop",
        "Physical world state",
        "No verified opening, no pipetting",
        "No verified closure, no completed run",
        "VERIFY FIRST",
        "#5cae5a",
    ):
        assert phrase.lower() in PAGE.lower()


def test_track_c_receipt_replay_is_zero_motion(tmp_path):
    path = save_track_c_receipt(
        run_simulated_tube_access("partial_uncap"),
        tmp_path / "track-c.json",
    )
    replay = replay_track_c_receipt(path)
    assert replay["mode"] == "receipt-replay"
    assert replay["source_mode"] == "simulation"
    assert replay["hardware_commands_issued_by_replay"] == 0
    assert replay["gates"]["open_verified"]
    assert replay["gates"]["closed_verified"]
    assert replay["recoveries"] == 1


def test_wrong_track_receipt_is_refused(tmp_path):
    path = tmp_path / "wrong.json"
    path.write_text(json.dumps({"track": "Track A"}))
    with pytest.raises(TrackCReceiptError, match="not a Track C"):
        replay_track_c_receipt(path)


def test_tampered_track_c_receipt_is_refused(tmp_path):
    receipt = run_simulated_tube_access("none")
    receipt["gates"]["open_verified"] = False
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(receipt))
    with pytest.raises(TrackCReceiptError, match="integrity"):
        replay_track_c_receipt(path)
