"""Dashboard tests -- stdlib only, so these run in CI as part of the sim gate."""
from bayhack.dashboard import run_loop, PAGE


def test_run_loop_converges_and_has_shape():
    d = run_loop(seed=7)
    assert d["converged"] is True
    assert d["runs_used"] < 26                     # beats the grid sweep
    assert d["rounds"]
    assert all({"k", "x", "fluor", "r2", "decision"} <= set(r) for r in d["rounds"])
    assert d["rounds"][-1]["decision"] == "ACCEPT"  # ends on a promoted result


def test_page_carries_house_style_and_grounded_facts():
    for s in ("bay-hack", "world model", "Rhodamine", "plr-mcp",
              "conformal", "#5cae5a", "lh-plate"):
        assert s in PAGE, f"dashboard page missing {s!r}"
