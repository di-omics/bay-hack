"""Acceptance and pre-act refusal remain independent of hidden simulator truth."""
import pytest

from bayhack.loop import Bench, DBTLLoop
from bayhack.safety import FAULTS, run_refusal


@pytest.mark.parametrize("fault", FAULTS)
def test_each_unsafe_plan_is_refused_before_backend_dispatch(fault):
    receipt = run_refusal(fault)
    assert receipt["status"] == "REFUSED"
    assert not receipt["plan_verification"]["passed"]
    assert receipt["execution"]["attempted"] is False
    assert receipt["execution"]["commands_issued"] == 0
    assert receipt["measurement"]["taken"] is False
    assert receipt["world_model"]["updated"] is False
    assert receipt["follow_up"]["executed"] is False
    assert receipt["recovery"]["plan_verification"]["passed"]


class BlindBench:
    """Bench adapter with no planted optimum exposed to the controller."""

    backend_name = "blind-simulation"
    measurement_provenance = "modeled"
    verification_provenance = "modeled"

    def __init__(self):
        self.model = Bench()
        self.follow_ups = []

    def run_plan(self, plan):
        return self.model.run_plan(plan)

    def rhodamine_series(self):
        return self.model.rhodamine_series()

    def run_follow_up(self, action):
        self.follow_ups.append(action)
        return True


def test_physical_acceptance_does_not_require_hidden_x_star():
    bench = BlindBench()
    loop = DBTLLoop(bench, budget=20, target_signal=0.85)
    history = loop.run(verbose=False)
    assert history[-1].decision == "ACCEPT"
    assert history[-1].target_met
    assert loop.follow_up["executed"]
    assert len(bench.follow_ups) == 1


def test_objective_threshold_blocks_low_quality_follow_up():
    loop = DBTLLoop(Bench(), budget=8, target_signal=0.99)
    history = loop.run(verbose=False)
    assert all(record.decision != "ACCEPT" for record in history)
    assert loop.follow_up is None
    assert loop.ledger.records[-1].acceptance["target_signal"] == 0.99
