# Paste-ready on-site coding-agent prompt

Paste everything below into the coding agent after opening it inside the
`bay-hack` repository.

```text
You are my build partner for bay-hack, a Track A entry for the 24hr AI for
Science World Models Hack at Zeon Systems. The announced target is TEM-1
beta-lactamase. The required story is: produce enzyme, confirm expression,
screen compounds on robots, read kinetics, let round 1 evidence design round 2,
determine dose response, and nominate or refuse.

House rules are mandatory:
- Read HOUSE_RULES.md first.
- Git author and committer must be di-omics with the repository email.
- Never add assistant attribution, generated-by text, or co-author trailers.
- Never alter the GitHub profile or avatar.
- Never use em dashes in public text.
- Push only green commits.
- Never describe modeled values as measured.

Orient before editing:
1. Discover the repository root with git rev-parse --show-toplevel. Do not assume
   a home-directory path.
2. Read README.md, OFFICIAL_TRACK_A_MATERIALS.md,
   ZEON_NATIVE_INTEGRATION.md, TEM1_TRACK_A.md, ADK_PREP.md,
   structures/README.md, STRATEGY.md, ACCEPTANCE.md, ONSITE_RUNBOOK.md,
   HARDWARE_KIT.md, CONVENTIONS.md, and HOUSE_RULES.md.
3. Run git status -sb and git log -5 --oneline.
4. Run python -m bayhack.preflight, python -m bayhack.tem1_demo,
   python scripts/validate_tem1_structures.py, python -m bayhack_adk.smoke,
   python -m bayhack.safety, python -m bayhack.benchmark, and
   python -m pytest -q.
5. Inspect bayhack/tem1.py, bayhack/tem1_cli.py,
   bayhack/tem1_dashboard.py, bayhack/seams.py, and bayhack/zeon_bridge.py.
6. Find optional repositories in either supported relative layout:
   ../plr-mcp, ../plr-epigenome, ../plr-lab-robot,
   ../ml-bio-eval/lab-world-model, or the categorized paths under
   ../../lab-automation and ../../research-and-ml. Report which exist. Never
   hard-code an absolute home path.
7. Confirm whether .venv/bin/adk exists and whether GOOGLE_API_KEY is present
   without printing its value. If ADK is missing, install only from
   requirements-adk.txt. Never commit .env.
8. Restate in five bullets: the two world models, the biological gates, the
   physical gates, the round 1 to round 2 decision, and the exact venue seam.
Do not edit until the baseline is green.

Primary goal:
Make the smallest complete Track A loop physically real while preserving the
deterministic simulator as the guaranteed fallback.

Execution order:
1. Find the shared-hardware booking system and reserve the earliest 60-minute
   expression block. Write the slot time into the run notes. Do not reserve a
   screen block before the organizer records a passing GFP gate. The reader is
   included in the screen block.
2. Run python -m bayhack.tem1_cli init --output-dir run_artifacts/tem1.
3. Keep the published defaults already encoded in assay-spec.json: sfGFP
   fluorescence, Ex 485 nm, Em 528 nm, nitrocefin, A490, and a 30-second
   cadence. Fill the remaining volumes, durations, compositions, compound
   source wells, and Zeon parameters only from the official event protocol and
   track-lead answers.
4. Start the single allowed expression batch as soon as the slot opens. Leave
   it in the incubator if approved and use the incubation window for Zeon,
   reader, compound-library, and agent integration.
5. Use confirm-expression with replicated TEM-1 and no-template evidence.
   Refuse the compound screen and screen booking if it fails.
6. Ask the track lead whether round 1 should prioritize duplicate evidence or
   library breadth. The default fits 45 compounds in duplicate plus six
   controls. Setting candidate_replicates to 1 fits 90 unique compounds plus
   six controls, while round 2 remains replicated. Generate and verify the
   chosen round-1 plan before any backend dispatch.
7. Use bayhack_adk only as the decision coordinator. The shipped tools enforce
   the contract results file in, deterministic decision, verified plate map
   out. The agent must not calculate its own inhibition values, weaken a gate,
   dispatch hardware, or claim physical execution unless the plan tool returns
   physical_execution_allowed true.
8. Map the verified assignments into the organizer's native Zeon project
   through one narrow JSON handoff. Inspect the supplied Python skill
   signatures, workflow graph, world, objects, and well anchors. Do not invent a
   generic SDK client or hard-code coordinates. Run the exact workflow in Zeon
   simulation before physical motion.
9. Export reader kinetics as well,time_s,value and analyze them with the shipped
   KineticPlate adapter. Preserve the raw file and SHA-256 digest.
10. If the vehicle-control slope is not above no-enzyme background or Z-prime
   fails, quarantine the data and stop. Do not relax thresholds to rescue a
   failed plate.
11. Generate round 2 only with build_round2_plan from the saved round-1 analysis.
12. Run and analyze round 2. Show the four-factor curve, uncertainty-aware
   monotonicity, relative 50 percent inhibition crossing, and final gate.
13. Save one successful receipt and one expression-refusal proof. Present the
    successful receipt through safe replay with zero hardware commands.
14. Update only the minimum dashboard text needed to display the measured
    provenance, real Z-prime, adaptive selection, and confirmed follow-up.
15. Record the successful physical run immediately. Do not postpone recording
    for extra features.

Safety invariants:
- No confirmed expression means no compound screen.
- No organizer-recorded GFP pass means no screen booking.
- Only one expression batch may be active for the team.
- No organizer-confirmed protocol means no physical execution.
- No valid compound source wells means no physical execution.
- No plan verification means no backend dispatch.
- No clear deck, E-stop owner, and human confirmation means no motion.
- Never reuse a wet tip unless the official workflow defines and verifies an
  approved wash policy.
- No passing control QC means no scientific-model update.
- No round 1 QC means no round 2.
- No round 2 confirmation means no nomination.
- Venue hardware must never become a dependency of bayhack.tem1_demo.
- Every Zeon electronic-pipette and operator-message call used in a
  simulation-capable skill must be guarded with is_sim_mode().
- Use Zeon's native liquid-transfer resume ledger. Record a transfer only after
  its dispense succeeds.
- The registered zeon verify command is not implemented and is not evidence of
  safety or correctness.
- ADK is outside the safety boundary. A persuasive agent sentence never
  overrides a returned file verdict.
- Treat the pinned 1XPB and 1ERO files as validated references, not prepared
  docking receptors. Record every preparation and scoring version before
  writing priority_score.

Git workflow for every coherent change:
1. Keep main green. Use a short feat/<name> branch if the change is risky.
2. Run the Track A demo, preflight, full tests, benchmark, and compileall.
3. Inspect git diff --check and scan the staged diff for secrets and unsupported
   claims.
4. Commit with a factual Conventional Commit subject.
5. Confirm the author and committer are di-omics.
6. Push only after all gates pass. Do not rewrite public history.

After each step report:
- what changed
- evidence label reached
- exact test result
- commit hash
- remaining physical limitation

Start now with orientation. If the organizer protocol is not yet present, make
progress on adapters and file validation but leave physical execution locked.
```
