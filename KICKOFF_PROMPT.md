# On-site coding prompt

Work inside the `bay-hack` repository. Read `HOUSE_RULES.md`, `STRATEGY.md`,
`ACCEPTANCE.md`, `HARDWARE_KIT.md`, `ONSITE_RUNBOOK.md`, and `CLAUDE.md` first.

## Orient before editing

1. Run `git status -sb` and `git log -5 --oneline`.
2. Run `python -m bayhack.demo`, `python -m bayhack.benchmark`, and `pytest -q`.
3. Inspect `bayhack/assay.py`, `bayhack/loop.py`, `bayhack/seams.py`, and
   `bayhack/zeon_bridge.py`.
4. Print the current evidence labels: modeled, simulated execution, measured,
   and hardware-validated.
5. Restate the two-world-model architecture and the exact on-site seam to wire.

Do not edit until the baseline is green.

## Goal

Make one complete Track A run physically real:

**plan -> pipette -> measure -> verify -> learn -> follow up**

Preserve the stdlib simulation as the guaranteed fallback.

## Priority order

1. **Measurement seam:** connect one camera or plate-reader value. Change its
   ledger provenance from `modeled` to `measured`. Add a test fixture that keeps
   CI hardware-free.
2. **Execution seam:** map the verified `LiquidHandlingPlan.transfers` onto the
   venue liquid handler or Zeon pipetting workflow. Use each plan's unique tip.
3. **Physical world seam:** map the enumerated `ZeonArmBackend` actions to the
   Python skill, workflow, or executor API supplied by Zeon. Do not guess names.
4. **Follow-up:** execute the accepted-well transfer to H12 through the same
   hardware path and record it in the ledger.
5. **Evidence:** save one successful trust receipt and one failed-gate receipt.
6. **Demo:** update only the minimum UI needed to show measured provenance and
   the successful follow-up.

## Safety and correctness rules

- Never run a physical action before `LiquidHandlingPlan.verify()` passes.
- Never home or move hardware without a clear deck, E-stop owner, and explicit
  human confirmation.
- Never reuse a wet tip. The simulator may return tips to rack positions, but
  the physical path must use waste or guaranteed fresh positions.
- Never label modeled data as measured.
- Never train the scientific model on a failed volume or CV gate.
- Never make venue hardware a dependency of `python -m bayhack.demo`.

## Git workflow

- Confirm `git config user.name` is `di-omics` before committing.
- Follow `HOUSE_RULES.md`.
- Use factual Conventional Commit subjects.
- Run tests, demo, and benchmark before every commit.
- Push only green commits.
- Do not rewrite public history.

## Final report

Return:

- GitHub commit hash
- Exact hardware and measurement adapters wired
- Exact evidence label shown in the ledger
- Demo command
- Trust receipt path
- Remaining fallback or safety limitations
