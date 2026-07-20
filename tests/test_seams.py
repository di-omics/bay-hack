"""Real-seam tests. Each is SKIPPED unless its @di-omics repo is importable, so
CI (which installs only pytest) stays green while these run locally where the
repos are installed:

    pip install -e ../plr-mcp -e ../plr-epigenome -e ../plr-lab-robot
    PYTHONPATH=../../ml-bio-eval/lab-world-model pytest -q
"""
import pytest


def test_execute_seam_runs_real_choreography():
    pytest.importorskip("plr_mcp")
    from bayhack.seams import PlrMcpBench
    b = PlrMcpBench(quiet=True)
    y = b.run_design(0.5)                      # real chatterbox build+read ran
    assert 0.0 <= y <= 1.0
    assert b.x_star == b.model.x_star          # loop convergence still works


def test_rhodamine_gate_real_reaches_liquid_tested():
    pytest.importorskip("tipseq_plr")
    from bayhack.seams import rhodamine_gate_real
    ser = [(2., 25.), (5., 62.5), (10., 125.), (20., 250.), (50., 625.)]
    r = rhodamine_gate_real(ser)
    assert r["passed"] and r["r2"] >= 0.995
    assert r["tier"] == "liquid_tested"        # the real gate certified it


def test_cv_checkpoint_real_flags_fault():
    pytest.importorskip("tipseq_plr")
    from bayhack.seams import cv_checkpoint_real
    assert cv_checkpoint_real(fault=False)["passed"]
    assert not cv_checkpoint_real(fault=True)["passed"]


def test_plan_from_text_routes():
    pytest.importorskip("tipseq_plr")
    from bayhack.seams import plan_from_text
    p = plan_from_text("cut and tag 8 samples")
    assert p["routed_to"] and p["samples"] >= 1


def test_real_world_model_coverage_near_target():
    pytest.importorskip("labworld")
    from bayhack.seams import real_world_model_run
    r = real_world_model_run(n_iter=20, seed=0)
    assert set(r["empirical_coverage"]) == {"yield_nM", "complexity", "purity"}
    # split-conformal empirical coverage should land near 1 - alpha = 0.90
    assert all(0.6 <= c <= 1.0 for c in r["empirical_coverage"].values())


def test_dexterity_checkpoint_moves_plate():
    pytest.importorskip("plr_lr")
    from bayhack.seams import dexterity_checkpoint
    r = dexterity_checkpoint()
    assert r["passed"] and r["commands"] > 0


def test_zeon_backend_is_real_scara_and_swap_runs():
    pytest.importorskip("plr_lr")
    from bayhack.zeon_bridge import ZeonArmBackend, zeon_swap_selfcheck
    from plr_lr.arm.sim_backend import SimulationArmBackend
    assert issubclass(ZeonArmBackend, SimulationArmBackend)   # a real SCARA backend
    assert ZeonArmBackend.N_JOINTS == 5
    r = zeon_swap_selfcheck()                                 # the swap actually runs
    assert r["passed"] and r["commands"] > 0 and r["zeon_calls"] > 0
    assert r["backend"] == "ZeonArmBackend"
    assert "pick_up_resource" in r["seams"]                   # SDK seams enumerated


def test_real_loop_converges_through_real_seams():
    pytest.importorskip("plr_mcp")
    pytest.importorskip("tipseq_plr")
    from bayhack.seams import PlrMcpBench, rhodamine_gate_real, cv_checkpoint_real
    from bayhack.loop import DBTLLoop
    loop = DBTLLoop(PlrMcpBench(quiet=True), tol=0.03, budget=8,
                    rhodamine_fn=rhodamine_gate_real, cv_fn=cv_checkpoint_real)
    loop.run(verbose=False)
    bx, _ = loop.wm.best()
    assert abs(bx - loop.bench.x_star) <= 0.06
