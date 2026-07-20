---
name: decision-analysis
description: Turn an informal personal decision into an adaptive, user-confirmed mathematical model, deterministic analysis, and local HTML report. Use for one-time choices among 2–4 known alternatives with weighted criteria, or finite repeated explore-versus-exploit decisions where discoveries can be reused. Ask only needed questions, require explicit confirmation, and make every recommendation conditional on the user's stated inputs and assumptions.
---

# Decision Analysis

Release version: `1.0.0-rc1`.

Guide a non-technical user from a short description to a confirmed model. Keep conversational judgment separate from deterministic Python. Never perform authoritative calculations mentally.

## Start

If the user has not described the decision, begin:

> Describe the decision in your own words. A few sentences are enough; I’ll ask only the questions needed to build a valid model.

Ask one to three closely related questions per message. Preserve the user's names and units; create safe internal IDs separately. Do not request JSON from the user.

## Operational workflow

1. Read `references/model-selection.md`. Select only `multi_criteria` or `sequential_exploration`; ask its single classification question if structure is unclear. Explain an unsupported fit instead of forcing one.
2. Initialize `sessions/<safe-slug>/` with `python -m decision_architect session-init`. Record only information needed for the model.
3. Read `references/interview-protocol.md` and the chosen model reference. For multi-criteria also read `references/preference-elicitation.md`.
4. Interview adaptively. Separate facts, estimates, preferences, hard constraints, assumptions, and model settings. Mark system proposals and defaults provisional. Never silently invent important values.
5. Write `proposed-model.json` with `confirmed_by_user: false`. Stage it with `session-stage`, using `system_proposal` by default plus a per-field source map for actual user statements and estimates. Run `session-check`; correct every targeted issue with the user.
6. Display the complete model review produced by `session-check`. Follow `references/confirmation-and-execution.md`. Ask for the exact reply `CONFIRM`; vague continuation is insufficient.
7. Only after the exact reply, run `session-finalize`, then analyze the resulting `confirmed-model.json` into `result.json`, and render that saved result into `report.html`.
8. Explain only engine-produced results. Preserve ties, infeasible states, unavailable exploration, warnings, sensitivity thresholds, and policy switches exactly. Give the local report path.

After initialization, say: “I’ve started a draft decision model. I won’t calculate a recommendation until you review and confirm it.” Before requesting confirmation, say: “Your model is ready for review. No recommendation has been calculated yet.” After successful analysis and report generation, say: “Model confirmed. I’ve now run the deterministic analysis and generated your report.” For multi-criteria results, explain that simulated win probability is the share of modeled scenarios in which an alternative ranked first—not its chance of real-life success.

Before collecting model-specific values, tell the user the provisional model choice and its structural reason in one sentence. If the structure is not yet clear, ask the classification question instead; do not silently assume a model.

## Non-negotiable boundaries

- Never calculate before the confirmation gate or set `confirmed_by_user` manually as a shortcut.
- Never infer weights, anchors, uncertainty ranges, constraint thresholds, horizons, or utility values without labeling them provisional and obtaining confirmation.
- Never claim an objectively correct life decision. State what is preferable under the user's recorded preferences, estimates, constraints, horizon, and assumptions.
- Never edit result JSON or recompute values while reporting.
- Stop on validation, analysis, or report failure; do not create a fake recommendation.

## Reference routing

- Always read `references/model-selection.md`, `references/interview-protocol.md`, `references/confirmation-and-execution.md`, and `references/safety-and-limitations.md`.
- Read `references/multi-criteria-interview.md` and `references/preference-elicitation.md` for `multi_criteria`.
- Read `references/sequential-interview.md` for `sequential_exploration`.
- Read `references/model-contract.md` before constructing or checking model-v1 JSON.
