# bay-hack winning strategy

## Pick Track A

The announced challenge is a direct fit for di-omics:

**produce TEM-1 beta-lactamase, prove expression, screen inhibitors with
robotics, read the assay, let round 1 sharpen round 2, and determine dose
response.**

The entry should stay liquid-handling first. Robotic arm motion is useful only
when it advances this experimental loop.

## The winning thesis

> A moving robot is not autonomous science. The loop becomes autonomous only
> when physical evidence is trustworthy enough to choose the next experiment.

bay-hack couples two world models:

- Zeon's physical world model tracks geometry, labware, robot state, and safe
  execution.
- bay-hack's scientific world model tracks expression evidence, assay controls,
  inhibition, uncertainty, dose response, and the next plate.

The winning moment is not a chart. It is round 2 changing because of round 1
data, then a confirmed condition causing a visible follow-up decision.

## Why this can beat broader projects

1. **Exact challenge fit:** every announced Track A verb is visible.
2. **Real liquid handling:** wells, replicates, controls, source positions, and
   dose factors are concrete.
3. **Scientific refusal:** failed expression or failed Z-prime blocks learning
   and the next round.
4. **Adaptive evidence:** round 1 selects the compounds and doses in round 2.
5. **Honest provenance:** modeled and measured values cannot be confused.
6. **Stage reliability:** a sealed receipt can replay the physical result with
   zero robot motion.
7. **Strong personal fit:** di-omics already ships PyLabRobot, Physical MCP,
   lab-automation verification, and autonomous-omics work.

## Demo spine

Use the TEM-1 dashboard, one plate, and one real evidence file. Do not tour every
repository.

1. Point to the seven-step pipeline.
2. Click **Prove expression refusal**.
3. Say that failed expression caused zero compound reads, model updates, round 2
   plans, and robot commands after failure.
4. Run the successful two-round path.
5. Point to activity, inhibition, and blank controls across the plate.
6. Point to round 1 Z-prime and measurement provenance.
7. Show the conservative rank: inhibition minus one standard error.
8. Show the top measured candidates returning at four dose factors.
9. Point to the monotonicity gate and relative 50 percent inhibition crossing.
10. Show the final nomination and SHA-256 sealed receipt.
11. If hardware is stable, execute or show the matching Zeon workflow.

## 90-second pitch

**0:00 to 0:15**

"Antibiotic resistance is physical, noisy, and expensive. A robot that only
executes a script cannot tell whether the enzyme was made, whether the assay
worked, or what experiment should happen next."

**0:15 to 0:32**

"bay-hack couples two world models. Zeon represents the live bench and safe
robot execution. My scientific model represents TEM-1 expression, inhibitor
response, uncertainty, and the next plate."

**0:32 to 0:48**

Click the refusal.

"First, the protein signal fails against the no-template control. The system
refuses the compound screen: zero compound wells, zero model updates, zero round
2 plans, zero commands after failure. It will not turn background noise into an
inhibitor claim."

**0:48 to 1:12**

Run the loop.

"Now expression passes. The robot runs replicated candidates and three control
classes. Kinetic slopes clear the Z-prime gate. Round 1 ranks inhibition with
uncertainty, then those observations design round 2 across four dose factors."

**1:12 to 1:30**

"The final condition is nominated only after round 2 QC, a passing inhibition
gate, and a monotonic confirmation curve. Every source file and the final
receipt are hashed. Produce, verify, screen, learn, confirm, act. Two world
models, one closed scientific loop. I'm Di. I build autonomous labs."

## Priority order at the venue

1. Get the official protocol and compound map into `run_artifacts/tem1`.
2. Confirm TEM-1 expression with real evidence.
3. Export one real kinetic reader file in the shipped schema.
4. Map one verified plate plan to the venue liquid handler or Zeon workflow.
5. Complete round 1 with real controls and preserve the analysis.
6. Generate round 2 from that analysis, not by hand.
7. Complete one real round 2 confirmation if time permits.
8. Seal and replay the successful receipt.
9. Record the physical run immediately.
10. Freeze before adding extra robotics.

## Success ladder

| Level | Evidence | Demo value |
|---|---|---|
| Bronze | Full deterministic two-round TEM-1 simulation | guaranteed coherent story |
| Silver | Real organizer protocol plus one measured expression or reader file | challenge-specific evidence |
| Gold | Real robot executes round 1 and real reader data designs round 2 | complete adaptive loop |
| Win | Gold plus real round 2 confirmation, Zeon simulation-to-physical trace, sealed receipt, crisp pitch | end-to-end world-model science |

## What not to build

- A general chat agent with no assay consequence
- A second scientific controller
- A new robotics framework
- A custom computer-vision stack before the reader export works
- A full compound-property predictor with no organizer metadata
- A wet protocol inferred from papers instead of the event instructions
- A flourish that makes the deterministic fallback unreliable

## Judge questions

**Where is the world model?**

The scientific state predicts unrun assay conditions from observed response and
uncertainty, then selects the next physical plate. Zeon models the complementary
physical state and execution. The second round is generated from the first
round's observations.

**What is real?**

Say exactly which expression, robot, and reader artifacts are measured. The
repository simulator is labeled modeled. Never blur them.

**Why kinetic data?**

The analysis estimates per-well reaction slopes. That makes the decision less
dependent on a single endpoint and exposes control drift before learning.

**Why Z-prime?**

It tests whether the activity and inhibition controls are separated relative
to their variation. A failed screen is quarantined instead of becoming model
training data.

**How did round 1 sharpen round 2?**

The top conservative scores, mean inhibition minus one standard error, define
which compounds return. Each returns across four configured dose factors.

**Is the 50 percent number an IC50?**

Until organizer concentrations and a fitted pharmacology model are supplied,
call it a relative factor estimate for the 50 percent inhibition crossing. Do
not overclaim it as a definitive IC50.

**What happens after a failure?**

The model does not update, no downstream plan is created, the evidence remains
visible, and the operator gets a specific recovery target.
