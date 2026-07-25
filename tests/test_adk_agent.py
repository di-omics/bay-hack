"""The optional Google ADK package exposes a loadable root agent."""
import pytest


pytest.importorskip("google.adk")

from bayhack_adk.agent import root_agent


def test_adk_root_agent_has_only_file_contract_tools():
    assert root_agent.name == "tem1_closed_loop_agent"
    tool_names = {
        getattr(tool, "__name__", type(tool).__name__)
        for tool in root_agent.tools
    }
    assert tool_names == {
        "initialize_track_a_packet",
        "inspect_track_a_inputs",
        "confirm_tem1_expression",
        "design_round_1",
        "analyze_reader_kinetics",
        "design_round_2",
        "prove_round_1_changed_round_2",
        "finalize_measured_campaign_receipt",
    }
