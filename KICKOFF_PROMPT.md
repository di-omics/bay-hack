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
   ZEON_NATIVE_INTEGRATION.md, TEM1_TRACK_A.md, STRATEGY.md, ACCEPTANCE.md,
   ONSITE_RUNBOOK.md, HARDWARE_KIT.md, CLAUDE.md, and HOUSE_RULES.md.
3. Run git status -sb and git log -5 --oneline.
4. Run python -m bayhack.preflight, python -m bayhack.tem1_demo,
   python -m bayhack.safety, python -m bayhack.benchmark, and pytest -q.
5. Inspect bayhack/tem1.py, bayhack/tem1_cli.py,
   bayhack/tem1_dashboard.py, bayhack/seams.py, and bayhack/zeon_bridge.py.
6. Find optional repositories in either supported relative layout:
   ../plr-mcp, ../plr-epigenome, ../plr-lab-robot,
   ../ml-bio-eval/lab-world-model, or the categorized paths under
   ../../lab-automation and ../../research-and-ml. Report which exist. Never
   hard-code an absolute home path.
7. Restate in five bullets: the two world models, the biological gates, the
   physical gates, the round 1 to round 2 decision, and the exact venue seam.
Do not edit until the baseline is green.

Primary goal:
Make the smallest complete Track A loop physically real while preserving the
deterministic simulator as the guaranteed fallback.

Execution order:
1. Run python -m bayhack.tem1_cli init --output-dir run_artifacts/tem1.
2. Keep the published defaults already encoded in assay-spec.json: sfGFP
   fluorescence, Ex 485 nm, Em 528 nm, nitrocefin, A490, and a 30-second
   cadence. Fill the remaining volumes, durations, compositions, compound
   source wells, and Zeon parameters only from the official event protocol and
   track-lead answers.
3. Use confirm-expression with replicated TEM-1 and no-template evidence.
   Refuse the compound screen if it fails.
4. Ask the track lead whether round 1 should prioritize duplicate evidence or
   library breadth. The default fits 45 compounds in duplicate plus six
   controls. Setting candidate_replicates to 1 fits 90 unique compounds plus
   six controls, while round 2 remains replicated. Generate and verify the
   chosen round-1 plan before any backend dispatch.
5. Map the verified assignments into the organizer's native Zeon project
   through one narrow JSON handoff. Inspect the supplied Python skill
   signatures, workflow graph, world, objects, and well anchors. Do not invent a
   generic SDK client or hard-code coordinates. Run the exact workflow in Zeon
   simulation before physical motion.
6. Export reader kinetics as well,time_s,value and analyze them with the shipped
   KineticPlate adapter. Preserve the raw file and SHA-256 digest.
7. If the vehicle-control slope is not above no-enzyme background or Z-prime
   fails, quarantine the data and stop. Do not relax thresholds to rescue a
   failed plate.
8. Generate round 2 only with build_round2_plan from the saved round-1 analysis.
9. Run and analyze round 2. Show the four-factor curve, uncertainty-aware
   monotonicity, relative 50 percent inhibition crossing, and final gate.
10. Save one successful receipt and one expression-refusal proof. Present the
    successful receipt through safe replay with zero hardware commands.
11. Update only the minimum dashboard text needed to display the measured
    provenance, real Z-prime, adaptive selection, and confirmed follow-up.
12. Record the successful physical run immediately. Do not postpone recording
    for extra features.

Safety invariants:
- No confirmed expression means no compound screen.
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
