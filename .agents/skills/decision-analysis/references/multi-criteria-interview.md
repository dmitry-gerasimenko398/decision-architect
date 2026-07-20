# Multi-criteria interview

Ask in adaptive batches rather than following this list mechanically.

## Decision and alternatives

Confirm a title, the one choice, and time horizon. Collect 2–4 real alternatives. Ask once whether delay, negotiation, continued search, or a small test belongs in scope. Add nothing without approval.

## Constraints versus preferences

Ask:

> If this condition is violated, should the option be eliminated completely, or should it merely receive a lower score?

Represent elimination as a hard constraint with criterion, operator, threshold, and per-alternative result. Represent compensation as a weighted criterion. If every option fails, pause for correction.

## Criteria and anchors

Prefer roughly 3–7 distinct criteria. Preserve user language, define units, and check overlap. For each, confirm ID, name, unit, maximize/minimize direction, worst meaningful anchor (utility 0), and best meaningful anchor (utility 1). Anchors must be distinct and are never inferred from alternatives.

## Alternative estimates

For every alternative/criterion pair record minimum, most likely, and maximum in the confirmed unit. Use equal values for certainty. Ask in manageable groups and restate translated ranges.

## Defaults and assumptions

Propose, then confirm: `monte_carlo_samples: 10000`, a fixed recorded `random_seed`, and `clamp_utility: true`. Never use the current clock as seed. Record interpretations such as gross/net salary, commute unit, time horizon, and independent criterion sampling.

## Review

Show alternatives, hard constraints, criteria and units, anchors, weights, every three-point estimate, assumptions, sample count, and seed. Do not calculate before exact `CONFIRM`.

Keep any zero-weight indicator used only to evaluate a hard constraint with the constraint review; do not describe it as an ordinary weighted preference. After analysis, define simulated win probability as modeled first-place frequency, not the chance of real-life success.
