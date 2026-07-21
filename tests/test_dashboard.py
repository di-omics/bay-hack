"""Dashboard tests -- stdlib only, so these run in CI as part of the sim gate."""
from bayhack.dashboard import run_loop, PAGE


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


def test_page_carries_house_style_and_grounded_facts():
    for s in ("bay-hack", "world model", "liquid-handling", "Rhodamine", "plr-mcp",
              "conformal", "follow-up", "#5cae5a", "lh-plate"):
        assert s.lower() in PAGE.lower(), f"dashboard page missing {s!r}"
