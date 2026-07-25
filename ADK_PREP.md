# Google ADK Track A preparation

The updated Track A guide asks teams to arrive with Google ADK installed, a
basic agent running, and prioritization and analysis exposed as function tools.
bay-hack keeps ADK optional so the deterministic simulator and physical safety
gates never depend on an LLM.

## What is ready

- Google ADK is pinned in `requirements-adk.txt`.
- `bayhack_adk/agent.py` exposes the loadable `root_agent`.
- Eight plain-Python function tools wrap the fixed Track A file contract.
- Every tool path is restricted to `BAYHACK_RUN_DIR`.
- No ADK tool can command hardware.
- A failed expression or assay-quality gate remains authoritative.
- The offline tool smoke proves that round 1 reader evidence creates a
  measurement-driven round 2 plate map.
- A transition tool seals the exact compounds, doses, and wells changed by
  round 1 evidence.
- A finalizer recomputes the measured campaign from raw fixed files before
  sealing its replay receipt.

## Install and validate

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-adk.txt
.venv/bin/python -m bayhack_adk.smoke
```

The smoke requires no API key and must end with:

```text
"round2_uses_measurement": true
"round_transition_proved": true
"physical_execution_allowed": false
```

That last refusal is expected because the smoke never invents venue protocol
values.

## Run the real ADK agent

Copy the environment template and add a Google AI Studio key locally. Never
commit `.env`.

```bash
cp .env.example .env
.venv/bin/adk run bayhack_adk
```

Suggested first prompt:

```text
Initialize a Track A packet in tem1. Then inspect it and tell me exactly which
organizer facts block physical execution. Do not invent any missing value.
```

For the browser interface:

```bash
.venv/bin/adk web bayhack_adk --port 8002 --no-reload
```

## Function tools

| Tool | Deterministic consequence |
|---|---|
| `initialize_track_a_packet` | writes an unconfirmed assay config and 95-row compound template |
| `inspect_track_a_inputs` | validates schemas and reports missing physical facts |
| `confirm_tem1_expression` | gates screening on replicated sfGFP evidence |
| `design_round_1` | emits a balanced, verified round 1 plate map |
| `analyze_reader_kinetics` | computes slopes, controls, Z-prime, ranking, and the round 2 gate |
| `design_round_2` | emits confirmation doses only from passing saved round 1 evidence |
| `prove_round_1_changed_round_2` | seals the measured plate transition and its source digests |
| `finalize_measured_campaign_receipt` | recomputes raw evidence and seals the measured campaign |

The boundary is intentionally simple:

```text
results file in -> deterministic tool decision -> verified plate map out
```

The LLM decides which tool to call and explains the result. It does not perform
the numerical analysis, override a gate, or dispatch a robot.

## Why the default is not an autonomous `LoopAgent`

The official guide lists `LoopAgent` and session state as useful ADK pieces.
This campaign has long physical waits, shared 60-minute hardware slots, a human
motion gate, and files arriving from a plate reader. Automatically looping an
LLM while no new evidence exists would add failure modes without closing the
physical loop.

The shipped `LlmAgent` therefore uses immutable files as durable state and
stops at every physical boundary. If the event flow and data adapters are
stable, a two-iteration `LoopAgent` can orchestrate the same tools later. It
must preserve the same file checkpoints and hard stops.

## On-site prompts

After real files are copied under `run_artifacts/tem1/`:

```text
Inspect tem1/assay-spec.json and tem1/compounds.csv. Report whether the plan is
scientifically valid and whether physical execution is allowed. Do not fix or
guess missing fields.
```

```text
Analyze tem1/round1-reader.csv against tem1/round1-plan.json. If QC passes,
write tem1/round1-analysis.json, design tem1/round2-plan.json, and prove the
plate transition. If QC fails, stop and explain the control failure.
```

```text
After tem1/round2-reader.csv has been analyzed, finalize the campaign from the
tem1 directory. Refuse if any saved plan or analysis differs from the raw
files. Report the receipt digest and measured nomination.
```

Every stage claim must cite the returned file, provenance label, and gate.
