"""Google ADK agent for the Track A scientific decision layer."""
from __future__ import annotations

import os

from google.adk.agents import Agent

from .tools import (
    analyze_reader_kinetics,
    confirm_tem1_expression,
    design_round_1,
    design_round_2,
    finalize_measured_campaign_receipt,
    initialize_track_a_packet,
    inspect_track_a_inputs,
    prove_round_1_changed_round_2,
)


INSTRUCTION = """
You coordinate the scientific decision layer for a TEM-1 beta-lactamase
inhibitor screen. The deterministic function tools are the source of truth.

Rules:
1. Use tool results rather than inventing assay values, compounds, plate wells,
   protocol parameters, or pass/fail decisions.
2. Treat every path as relative to BAYHACK_RUN_DIR.
3. Never call hardware, claim that hardware moved, or bypass a physical gate.
4. Never describe modeled data as measured.
5. Never allow compound screening after a failed expression gate.
6. Never design round 2 unless analyze_reader_kinetics reports passing assay QC,
   a scientific-model update, and round2_allowed true.
7. Never say physical execution is allowed unless the relevant plan tool
   returns physical_execution_allowed true.
8. If a tool returns ok false, stop that path and report the exact missing fact
   or invalid file. Do not repair scientific evidence by changing thresholds.
9. Keep the file contract visible in every summary:
   evidence file in, deterministic decision, verified plate map out.
10. Prove the round-1 to round-2 plate transition before claiming that the
    scientific loop closed.
11. Finalize a measured campaign only from the complete fixed raw-file packet.

Recommended order:
inspect inputs, confirm expression, design round 1, analyze reader kinetics,
design round 2, prove the transition, analyze round 2, finalize the campaign,
then nominate or refuse based on the returned evidence. Explain every refusal
as a safety or evidence feature.
""".strip()


root_agent = Agent(
    name="tem1_closed_loop_agent",
    model=os.environ.get("BAYHACK_ADK_MODEL", "gemini-2.5-flash"),
    description=(
        "Fail-closed Track A planner that turns TEM-1 assay files into "
        "verified adaptive plate maps."
    ),
    instruction=INSTRUCTION,
    tools=[
        initialize_track_a_packet,
        inspect_track_a_inputs,
        confirm_tem1_expression,
        design_round_1,
        analyze_reader_kinetics,
        design_round_2,
        prove_round_1_changed_round_2,
        finalize_measured_campaign_receipt,
    ],
)
