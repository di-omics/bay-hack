# bay-hack winning strategy

## Track

Choose **Track A: close the loop with robotics**.

The project is liquid-handling-first and maps directly to all four required
verbs:

1. **Planning:** compile the goal and verify concrete wells, volumes, and tips.
2. **Robotic execution:** run the formulation through Physical MCP and the
   available liquid handler or pipetting arm.
3. **Measurement:** use a plate reader or camera, then apply volume and CV gates.
4. **Follow-up:** transfer 20 uL from the accepted well to H12.

## The strongest framing

The winning story is not that one world model replaces another. It is that two
world models solve different parts of the same scientific loop:

- **Zeon's physical world model** represents geometry, equipment, labware,
  motion, and changing physical state.
- **bay-hack's scientific world model** predicts assay response, represents
  uncertainty, and selects the next liquid-handling experiment.

The physical model answers, "Can the robot execute this safely in the current
world?" The scientific model answers, "Which experiment should the robot run
next?" The trust ledger joins their evidence.

## Demo spine

Use one plate and one visible assay. Do not demo every supporting repository.

1. Show the 40 uL plate plan: A1 stock, A2 diluent, B1 onward proposals.
2. Click **Prove refusal**. A reused tip is rejected with zero robot commands.
3. Run two seed wells. Both pass plan, Rhodamine or colorimetric, and CV gates.
4. Let the scientific model choose the next formulations.
5. Show the response and uncertainty improve while concrete volumes remain visible.
6. Land on ACCEPT only after the objective and uncertainty criteria both pass.
7. Open the trust receipt and point to `measurement.provenance`.
8. Execute the 20 uL follow-up from the accepted well to H12.
9. If the Zeon adapter is live, show the physical model execute the same action.

## 90-second script

**0:00 to 0:12**

"A moving robot is not yet autonomous science. The experiment only counts when
the physical result is trustworthy enough to update the next decision."

**0:12 to 0:28**

"bay-hack couples two world models. Zeon models the physical bench and safe
execution. My scientific model predicts assay response and chooses the next
liquid-handling experiment under uncertainty."

**0:28 to 0:58**

"Here is the literal plate plan: stock from A1, diluent from A2, 40 microliters
per proposal, and a fresh tip for each liquid. Even the seed runs must pass the
volume and camera gates before the model can learn."

Click **Prove refusal**, then run the dashboard. Point to zero robot commands,
the seed rows, volumes, signal, objective threshold, and ACCEPT.

**0:58 to 1:15**

"It found the accepted formulation in about six runs instead of a 26-point
grid. That saves about 800 microliters and 40 tips in this search. Every step is
captured in a machine-readable trust receipt, including whether the signal was
modeled or measured."

**1:15 to 1:30**

Execute or show the follow-up transfer.

"Now the accepted well moves downstream. Plan, execute, measure, follow up.
Two world models, one physically verified scientific loop. I'm Di. I build
autonomous labs."

## Priority order before the event

1. Keep `python -m bayhack.preflight`, the six-run simulator, and dashboard green.
2. Rehearse camera colorimetry with food dye and the exact plate map.
3. Rehearse the measured volume CSV and CV JSON formats with fixture files.
4. Confirm venue liquid handler, tips, reader, wavelengths, and chemical policy.
5. Record one complete physical fallback run at home if possible.
6. Rehearse the pitch with the plate in hand.
7. On-site, connect one real measurement before attempting extra robotics.
8. Earn `hardware-validated` from both measured gates before adding flourishes.
9. Freeze the path by Saturday evening and record it before robots stop.

## What not to build

- A second dashboard
- A broad LLM planner with no physical consequence
- A new robotics framework
- A wet biology protocol that cannot finish inside the event
- A complex multi-objective assay before one real read works
- Any feature that makes the Zeon adapter mandatory for the fallback demo

## Judge questions to be ready for

**Why is this a world model?**

The scientific model predicts response and uncertainty for unrun experiments,
then uses those imagined outcomes to choose the next physical action. Zeon's
world model handles the complementary spatial and state representation.

**What is real today?**

The loop, plate plan, gates, ledger, follow-up, simulator paths, and repository
adapters are real code. The default numeric response is modeled. The first
on-site goal is to replace it with one real camera or reader value.

**Why not just grid search?**

The benchmark declares a 26-point baseline and reports search runs, reagent
volume, tips, convergence, and error. The current modeled benchmark averages
six runs, 240 uL, and 12 tips.

**What happens on a gate failure?**

The measurement does not train the model. The run escalates, remains visible in
the ledger, and the operator can retry or inspect the physical system.

**Does acceptance use the planted simulator optimum?**

No. The planted optimum is used only to score the modeled benchmark. The
controller accepts when the best trustworthy signal clears the declared assay
objective and the uncertainty gate clears. A physical bench does not expose
ground truth to the controller.

**What happens after acceptance?**

The accepted well is transferred to H12 with a new tip. This is the required
follow-up action, not a presentation-only banner.
