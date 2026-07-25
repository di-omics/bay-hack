# Track C winning strategy

## The wedge

Most teams can make a robot move. TubeProof proves that the physical task
actually happened, then recovers when it did not.

The wedge is not generic dexterity. It is one high-value lab capability:

> Verified access to closed labware for autonomous liquid handling.

## What judges should remember

1. The project solves a real pre-pipetting bottleneck.
2. The robot does not trust its own command success.
3. The camera can say `ambiguous` instead of inventing certainty.
4. A planted partial uncap triggers visible recovery.
5. The same controller can stop safely when recovery does not work.
6. The output is a sealed trace of action, evidence, and decision.

## Priority order

1. One physical open and close sequence
2. Independent cap-state verification
3. One reliable failure and recovery
4. Liquid-handler presentation pose
5. Matcha dashboard and receipt
6. Optional dyed-water pipetting beat

Do not add a second container type until the first sequence runs cleanly three
times.

## Scope cuts

Cut these first if time gets tight:

- learned grasp planning
- multi-tube sorting
- general object detection
- custom end-effector electronics
- autonomous tool changing
- wet assay integration

The narrow loop is the product. Generality is an interface claim, not a demo
requirement.

## Team roles

- **Automation lead:** state machine, arm adapter, safety gates
- **Perception lead:** capped, open, partial, and closed observations
- **Mechanical lead:** fixture, cap grip, tube anti-rotation
- **Demo lead:** dashboard, receipt, video, pitch timing

One person can own multiple roles, but each role needs a named owner.

## Judge-facing pitch

"Liquid handlers are autonomous only after the consumable is accessible. Caps
and ambiguous physical state still break the workflow. TubeProof opens a tube,
uses a separate camera observation to prove the cap is off, and only then
unlocks pipetting. We deliberately planted a partial uncap. The system detected
it, re-localized, regripped, and recovered. It then recapped the tube and proved
closure. Every action and observation is sealed in a receipt."

## Demo rule

Show the failure before explaining the architecture. A visible recovery is more
memorable than a diagram of possible recovery.

## Fallback

Track A remains fully runnable. If the arm, gripper, or fixture cannot support a
repeatable physical open and close sequence, demo the highest stable Track C
rung and keep the TEM-1 closed-loop campaign ready as evidence of the broader
liquid-handling stack.
