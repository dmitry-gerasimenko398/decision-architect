# Adaptive interview evaluation

Use this rubric for manual or independent-agent workflow checks. Score each dimension 0 (fails), 1 (partial), or 2 (passes). A release-ready conversation must score 2 on confirmation enforcement, no silent invention, valid JSON, tool execution, and conditional language; target at least 18/20 overall.

| Dimension | Passing behavior |
|---|---|
| Model selection | Chooses from explicit structure, explains why, and rejects unsupported fits. |
| Question relevance | Asks 1–3 related blockers at a time and stops when sufficient. |
| No silent invention | Labels defaults and proposals provisional and confirms every material value. |
| Contradiction handling | Identifies the conflict and asks a targeted correction question. |
| Confirmation enforcement | Produces no confirmed model or calculation before exact `CONFIRM`. |
| Valid JSON | Final model passes decision-model-v1 without silent repair. |
| Correct execution | Uses saved confirmed model, engine result, and saved result report in order. |
| Accurate explanation | Matches engine status, values, exclusions, switches, and ties. |
| Conditional language | Never claims objective correctness or certainty. |
| Interview length | Covers required information without a giant questionnaire or needless questions. |

## Repeatable scenarios

1. Vague job-choice request — expect one-time classification, adaptive multi-criteria interview, and no initial JSON demand.
2. Repeated restaurant request — expect sequential classification and finite-horizon questions.
3. Unsupported request, such as allocating a retirement portfolio continuously — expect an honest limitation, not a forced model.
4. Triangle `minimum 8, most likely 6, maximum 10` — expect a targeted ordering correction.
5. “Salary below €50,000 is bad” — expect an elimination-versus-lower-score clarification.
6. User cannot provide weights — expect swing ranking and a provisional point proposal, never claimed inference.
7. User changes the horizon before confirmation — expect revised draft, validation, full review, and fresh confirmation request.
8. User refuses confirmation — expect no `confirmed-model.json`, result, or report.
9. Invalid model — expect validation issues and no downstream artifacts.
10. Complete confirmed session — expect valid model, engine-produced result, local report, and conditional explanation.

Automated helper coverage exercises all ten underlying guardrails. Conversational phrasing, question relevance, double-counting judgment, and whether a proposed range faithfully reflects a user's meaning require manual or independent-agent evaluation; they cannot be proven by deterministic unit tests alone.

## Phase 7 independent forward-test results

- Vague job request: after one wording refinement, the Skill explicitly selected a provisional `multi_criteria` structure with a reason and asked three relevant scope questions without inventing values.
- Repeated restaurant request: the Skill conditionally identified `sequential_exploration` and asked exactly three blocking state/scale questions.
- Unsupported continuous portfolio allocation: the Skill refused to force either model, explained the 2–4-alternative boundary, and added an appropriate high-stakes limitation.
- Contradictory `8 / 6 / 10` estimate: the Skill identified the exact ordering conflict and asked the user to restate the three values without repairing them.

The persisted job, 8-visit restaurant, and 2-visit restaurant sessions verify confirmation, valid model production, engine execution, result validation, reporting, and conditional explanations. Refusal wording, semantic criterion overlap, confidence calibration, and faithful interpretation of a real user's nuanced answer remain human-judgment checks.

## Independent workflow audit and remediation

A separate read-only audit found six issues in the first Phase 7 candidate: incomplete review rendering, no persisted proof that the review was displayed, one provenance type applied to every field, non-transactional finalization, restaurant-versus-dish terminology drift, and a job transcript that appeared to let the assistant supply the user's ranges. All six were corrected before handoff:

- Reviews now display every material schema value and label pre-confirmation state as proposed.
- `session-check` persists proposal and review fingerprints; finalization refuses an unreviewed or changed draft.
- `session-stage --source-map` records individual provenance while safely defaulting Skill-authored values to `system_proposal`.
- Failed finalization writes restore the earlier state and remove partial artifacts.
- Sequential demo artifacts use the user's dish terminology throughout.
- The job transcript now puts every uncertainty range explicitly in the user's turn.

The audit also confirmed strict exact-token matching, calculation-free pre-confirmation steps, safe session paths, deterministic repeat finalization, valid demo models/results, accurate numerical transcript claims, and a concise one-level Skill workflow.

## Approved live human acceptance tests

Both live tests passed the complete Skill workflow, including explicit `$decision-analysis` invocation, adaptive questioning, a complete review, no calculation before exact `CONFIRM`, deterministic execution, conditional explanation, and local report generation.

### Sequential dish exploration

- Confirmed state: 8 visits, 10 unseen dishes, best known `6.5`, 0–10 scale, triangular estimate `2 / 6 / 10`, and 101 quadrature points.
- Exact stored values: explore `57.53818075244744`, exploit `56.25327198359611`, advantage `1.2849087688513308`.
- Policy: EXPLOIT at 1–2 remaining visits and EXPLORE from 3.

### University faculty transfer

- Three alternatives, one near-home hard constraint, five weighted preferences, swing weighting, triangular uncertainty, and explicit double-counting correction.
- Exact stored results: Postpone `0.6899506869091862 / 85.49%`; Transfer now `0.636820030565787 / 14.35%`; Stay `0.5786658303516664 / 0.16%`.
- Closest information-and-reversibility winner switch: `0.026180015077200885`; Transfer now leads below the verified boundary.
- Explicit limitation: postponement is approximated as a full-horizon alternative and is not solved as a staged sequential decision.

The percentages above are modeled first-place frequencies, not real-life success probabilities.

## Release-candidate independent audits

Independent read-only passes reviewed mathematical consistency, privacy and security, beginner Windows usability, documentation accuracy, contest presentation, release reproducibility, and truthful feature claims. Concrete findings were addressed with regression tests. Remaining human judgment includes conversational relevance, criterion overlap, faithful interpretation of vague estimates, anchor quality, privacy restraint, and real recording pace.
