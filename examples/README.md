# Sanitized release examples

Every JSON model in this directory conforms to `schemas/decision-model-v1.schema.json` and is confirmed for deterministic demonstration use.

## Job choice

`job-choice.json` contains three alternatives, four weighted criteria, one salary hard constraint, user-confirmed anchors, and triangular estimates.

For a triangular distribution:

```text
mean = (minimum + most likely + maximum) / 3
utility = (value - worst_anchor) / (best_anchor - worst_anchor)
```

The deterministic output is `outputs/job-choice-result.json`. Remote startup has Monte Carlo mean utility approximately `0.663545` and modeled first-place frequency `98.76%`; Local nonprofit is excluded by the salary constraint. This frequency is not a real-life success probability.

## Feynman-inspired dish exploration

`feynman-restaurant.json` preserves the approved live-test structure: eight visits, ten unseen dishes, best-known value `6.5`, 0–10 net-utility scale, triangular new-dish estimate `2 / 6 / 10`, and `101` quadrature points.

`feynman-restaurant-short-horizon.json` keeps the same inputs except for two visits. The dynamic program recommends EXPLORE at eight visits and EXPLOIT at one–two visits; the policy switches at three.

## Sanitized university acceptance test

`university-transfer.json` is a sanitized copy of the approved live human multi-criteria test. It has three alternatives, five weighted criteria, a separate zero-weight near-home hard-constraint indicator, swing weights, and triangular estimates.

`outputs/university-transfer-result.json` preserves the exact calculated values: Postpone approximately `0.6900 / 85.49%`, Transfer now `0.6368 / 14.35%`, and Stay `0.5787 / 0.16%`. The closest information-and-reversibility switch is approximately `0.02618`. Postponement is explicitly an approximate full-horizon strategy, not a staged sequential solution.

## Conversations and provenance

`conversations/` contains condensed sanitized interview demonstrations, including the two approved live human acceptance-test structures. Numerical statements come from the released result JSON.

`source-maps/` records field-by-field provenance for the three reproducible `demo_sessions/` examples. Skill-authored values remain `system_proposal`; genuine user inputs are mapped as `user_statement` or `user_estimate`.

Rebuild the sanitized end-to-end demo sessions with:

```powershell
py -m scripts.generate_demo_sessions
```

Arbitrary live work stays under ignored `sessions/` and is never part of the release set.
