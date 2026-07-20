# Acceptance criteria -- verification before trust

bay-hack's whole thesis is that the hard part of lab automation isn't motion, it's
**trust**: did the robot actually do what the code said? So every stage of the loop
has (1) an **acceptance criterion**, (2) a **control** that makes the criterion
checkable rather than asserted, and (3) a known **failure mode** it catches. A
measurement only trains the world model once it is physically trustworthy; the
conformal gate then decides accept vs. escalate.

The `status` column is deliberately honest -- it says exactly how far each stage is
proven today:

- **sim** -- runs in the stdlib simulation (`python -m bayhack.demo`).
- **real, no hardware** -- calls the shipped @di-omics code and was verified to run
  with no instrument (`python -m bayhack.demo --real`).
- **on-site** -- the piece that gets wired at the bench (real reader, real camera,
  real arm / Zeon SDK).

| Stage | Acceptance criterion | Control | Failure mode caught | Status |
|---|---|---|---|---|
| **Plan** (`tipseq_plr.sow`) | NL goal compiles to a routed protocol with a validation tier attached | tier defaults to `untested`; nothing claims to be validated until data clears the gate | over-claiming an unvalidated protocol | real, no hardware |
| **Design** (`labworld` GP + ParEGO) | proposes the next experiment; recovers a planted optimum | seeded spread-out probes; model trains only on trustworthy reads | chasing noise / premature convergence | sim + real (GP+ParEGO), no hardware |
| **Build / Test** (`plr_mcp.lab.Lab`) | executes the pick / aspirate / dispense / read choreography | chatterbox sim backend by default; `star`/`ot2` require a human-gated `confirm` | driving real hardware on an unverified plan | real choreography, no hardware. **Signal is MODELED** until a real reader is wired (chatterbox reader returns zeros) |
| **Verify -- volumes** (`tipseq_plr.validation.evaluate`) | Rhodamine ladder: R2 >= 0.995 **and** in-range accuracy **and** replicate CV -> `tier=liquid_tested` | the gate is stricter than R2 alone; a bare ladder without replicates stays `untested` | trusting a dispense whose volume was actually wrong | real (reaches `liquid_tested`), no hardware. Real reagents on-site |
| **Verify -- steps** (`tipseq_plr.steps.vision`) | each physical checkpoint returns `ok`; a critical fault raises | `SimVision` now, `LabCvVision` + camera on-site | reader-blind execution faults (bead loss, no pellet) | sim (`SimVision`); real camera on-site |
| **Learn** (`labworld.ConformalQCGate`) | accept / reject / escalate with a coverage guarantee (~0.90 empirical at alpha=0.10) | split-conformal calibration; only trustworthy reads promote | over-confident acceptance of a bad run | real, no hardware |
| **Move / dexterity** (`plr_lr.Workcell`) | arm moves a plate between taught sites; readiness passes | sim backend first; residual / readiness checks | crash / missed pick | real (`Workcell.sim`), no hardware. Real arm on-site |
| **Bridge** (`bayhack.zeon_bridge.ZeonArmBackend`) | `ExperimentalSCARA(backend=ZeonArmBackend())` runs the same choreography | subclasses `SimulationArmBackend` so it runs in sim today; every SDK call is an enumerated seam; pure-PLR loop is the fallback | the bridge blocking the demo | real swap runs in sim; Zeon SDK on-site |

## What is proven vs. owed

**Proven today (no hardware):** the closed loop converges (~6 runs vs ~26 for a grid
sweep, 100% over 30 seeds); the real Rhodamine gate certifies a ladder to
`liquid_tested` at R2=1.0; the real conformal gate holds ~0.90 coverage; the real arm
choreography and the Zeon-backend swap both execute in simulation.

**Owed on-site (build #1):** a real plate reader (so fluorescence is measured, not
modeled), real reagents through the Rhodamine gate, a real camera behind
`LabCvVision`, and the Zeon SDK behind the enumerated `zeon_bridge` seams. None of
these change the loop -- they replace a stand-in at a seam.

## Reproduce

```bash
python -m bayhack.demo         # sim loop
python -m bayhack.demo --real  # through the real @di-omics stack, no hardware
python -m bayhack.benchmark    # the numbers above
pytest -q                      # sim gate green; real-seam tests skip unless installed
```
