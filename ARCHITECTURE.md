# Decision Architect — Architecture

## Design goals

The architecture keeps conversational judgment separate from mathematical calculation. Every recommendation must be traceable through confirmed input data, validation results, formulas, and deterministic output.

The MVP runs locally and has five logical layers.

## 1. Adaptive interview layer

Location: `.agents/skills/decision-analysis/`

Responsibility:

- Interpret the user's natural-language decision.
- Determine whether `multi_criteria` or `sequential_exploration` fits.
- Ask only relevant follow-up questions.
- Explain unfamiliar concepts in plain language.
- Detect missing, contradictory, or low-confidence answers.
- Present the assembled model as a readable confirmation summary.
- Require explicit user confirmation before requesting calculations.
- Explain results conditionally after the engine returns them.

This layer may suggest structures and surface ambiguity, but it must not invent missing preferences or become the source of calculated numbers.

The `decision-analysis` Skill implements this layer operationally. `SKILL.md` holds the short control flow; focused references cover selection, small-batch questioning, each model interview, swing weighting, confirmation/execution, and limitations. The first response invites natural language rather than JSON.

Deterministic support remains separate:

- `decision_architect/interview.py` creates safe IDs, checks explicit structural signals, separates hard constraints from preferences, validates three-point ordering, and converts user-provided swing points.
- `decision_architect/model_draft.py` reports validation issues, tracks material leaf values, and renders a complete confirmation review.
- `decision_architect/session_state.py` confines safe session paths, atomically persists state, blocks calculation drafts, and creates confirmed models only after exact `CONFIRM`.

These modules never ask questions or calculate recommendations.

## 2. Structured decision-model layer

Locations: `schemas/` for contracts and `examples/` for representative instances.

Responsibility:

- Provide a versioned JSON representation of confirmed user inputs.
- Use a shared envelope for model identity, version, title, time horizon, assumptions, and user confirmation state.
- Use model-specific fields for alternatives, constraints, criteria, three-point estimates, or sequential state and distributions.
- Preserve user-entered values separately from any normalized values computed later.
- Provide stable identifiers so reports can link inputs to results.

The JSON model is the boundary between probabilistic language-model work and deterministic program behavior.

## 3. Validation layer

Location: `decision_architect/validation.py` plus documented JSON Schema contracts in `schemas/`.

Responsibility:

- Validate shared structure and the selected model-specific structure.
- Enforce numeric bounds and relationships, such as 2–4 alternatives and ordered three-point estimates.
- Reject unsupported model types and schema versions.
- Check that required confirmations and assumptions are present.
- Return structured errors with a field path, code, and plain-language message.
- Reject invalid data without silently normalizing weights, inventing anchors, or repairing estimates.
- Perform no recommendation or ranking.

Validation will happen before every calculation even if the interview already checked the same fields. This protects the engine when JSON is supplied directly.

The executable validator uses only the Python standard library. The JSON Schema files are interoperability contracts; cross-field rules are enforced manually in Python.

## 4. Deterministic Python engine

Implemented locations:

- `decision_architect/engine.py` — validated dispatch to both implemented model engines.
- `decision_architect/multi_criteria.py` — implemented feasibility, utility, Monte Carlo, and recommendation classification.
- `decision_architect/statistics.py` — implemented population summary and interpolated percentiles.
- `decision_architect/result_serialization.py` — implemented result-v1 serialization and dependency-free output checks.
- `decision_architect/sensitivity.py` — fixed-sample analytical one-weight sensitivity and verified winner-switch thresholds.
- `decision_architect/cli.py` and `decision_architect/__main__.py` — implement `analyze`, `report`, `report-index`, session commands, and `verify-release`.
- `decision_architect/sequential_exploration.py` — implemented memoized finite-horizon policy calculation and triangular quadrature.
- `decision_architect/models.py` — typed validated input structures.

Responsibility:

- Accept only validated structured models.
- Apply documented formulas and explicit decision rules.
- Use a local random-number generator initialized from the input seed, never hidden global randomness.
- Return JSON-compatible results with intermediate values, assumptions, algorithm/version identifiers, warnings, and recommendation-change conditions.
- Avoid user-facing persuasion or interpretation.

The engine must not call an LLM, access a network, read private files, or modify the confirmed input model.

For `multi_criteria`, Phase 3 implements triangular estimates, user-confirmed raw-value anchors, mandatory 0-1 utility clamping, Monte Carlo mean utility as the primary ranking, analytical utility as a cross-check, equal split credit for simulation ties within `1e-12`, and a 60 percent close-call threshold.

Phase 5 retains the normalized criterion utilities from that single Monte Carlo run and computes their mean for every feasible alternative/criterion pair. When one criterion weight becomes `x`, every other weight is multiplied by `(1-x)/(1-original_target_weight)`. Each alternative’s fixed-sample mean utility is therefore linear in `x`, so `sensitivity.py` solves winner-line equalities analytically rather than resampling or searching a grid. It filters crossings to `[0,1]`, preserves feasibility, uses the same `1e-12` top-mean tie rule, verifies both sides, and reports the nearest lower and upper switch plus the open/closed robust interval. A target originally weighted exactly 1 is not analyzed because other-weight proportions are undefined.

Sensitivity considers changes in the mean-utility winner only. The separate 60 percent win-probability threshold may change `recommended` to `close_call`, but that classification change is not a sensitivity winner switch.

Hard constraints are executable rules with a criterion ID, operator, and threshold. Upper-bound rules inspect the estimate maximum; lower-bound rules inspect its minimum; equality and inequality inspect all three triangular values. The engine cross-checks the computed outcome against the confirmed boolean stored on each alternative and stops on disagreement.

All sampling uses a function-local `random.Random(seed)` instance. The engine reports population standard deviation and percentiles interpolated at index `(n - 1) * p`. Feasible results are ordered by descending Monte Carlo mean utility, descending win probability, then stable ID for display only.

For `sequential_exploration`, the implemented state is `(remaining_opportunities, unseen_options_remaining, best_known_value)`. Both actions consume one opportunity. Exploration also consumes one unseen option, receives the explored net utility immediately, and updates the reusable best known value. The Bellman base is `V(0,u,b)=0`; exploit is `b + V(t-1,u,b)` and explore is `E[X + V(t-1,u-1,max(b,X))]`. There is no discount factor, exploration cost, distribution learning, or random sampling.

The expectation uses midpoint quantile quadrature over the triangular inverse CDF. The default grid has 101 points; an explicitly supplied count must be positive and odd. Memoized best-known keys use 12 decimal places, and action values within `1e-10` are classified as `indifferent`. The engine also recalculates every horizon from 1 through the requested horizon while holding the other initial-state inputs fixed, then records action-switch points.

## 5. Report generator

Implemented locations:

- `decision_architect/reporting.py` — result loading, dependency-free validation, model dispatch, atomic output, and demo-index summaries.
- `decision_architect/report_templates.py` — escaped semantic HTML, one coherent visual system, model-specific report sections, and the demo landing page.
- `decision_architect/svg_charts.py` — deterministic accessible inline SVG created only from stored result values.

Responsibility:

- Consume one already-saved `decision-result-v1` JSON file and preserve its exact text in an escaped audit view.
- Present alternatives, constraints, preferences, uncertainty, results, sensitivity or horizon policy, and caveats visually.
- Clearly distinguish user input, derived values, and conclusions.
- Include the exact conditional recommendation produced from the engine result.
- Escape user-provided text to prevent HTML injection.
- Work locally without a web server or network connection.

The report generator validates before rendering, HTML-escapes every JSON-originated string, contains no JavaScript or external resources, and writes through a sibling temporary file followed by an atomic replace. The same source bytes and generator version produce byte-identical HTML: rendering adds no clock time, randomness, machine path, or unstable ordering. It may format and visualize stored values but does not import the analysis dispatcher, independently rank options, rerun Monte Carlo simulation or dynamic programming, or recompute policy.

Charts have SVG titles and descriptions plus complete numerical table alternatives. The shared CSS provides high contrast, responsive layouts, visible focus states, and print rules. Where result-v1 lacks an original multi-criteria display label, a stable ID is humanized for presentation only; no analytical value changes.

## Data flow

```text
Natural-language decision
        |
        v
Adaptive interview (Codex Skill)
        |
        v
Draft structured model
        |
        v
Plain-language review + explicit user confirmation
        |
        v
Versioned input JSON
        |
        v
Validation ---- failure ----> actionable corrections -> interview/review
        |
      success
        v
Deterministic Python engine
        |
        v
Versioned calculation-output JSON
        |                         \
        v                          v
HTML report generator          Codex explanation
        |                          |
        +------------+-------------+
                     v
 Conditional recommendation under stated assumptions
```

The implemented persisted path around the confirmation boundary is:

```text
session-state.json + proposed-model.json (confirmed_by_user = false)
        |
        v
session-check -> complete plain-language review -> exact CONFIRM
        |
        v
session-finalize -> confirmed-model.json (validated, confirmed_by_user = true)
        |
        v
existing analyze -> result.json -> existing report -> report.html
```

Changing a material value returns the session to proposal review. `session-check` records proposal and rendered-review fingerprints; finalization requires those exact fingerprints, so staging cannot skip display of the review. Per-field source maps distinguish user input from Skill proposals and defaults. The three finalization artifacts are written with rollback protection so a failed write does not leave a partly confirmed session. Session helpers do not import or invoke the calculation engines.

## Command-line boundary

The command-line boundary preserves calculation and reporting separation:

```powershell
python -m decision_architect analyze examples\job-choice.json
python -m decision_architect analyze examples\job-choice.json --output outputs\job-choice-result.json
python -m decision_architect analyze examples\feynman-restaurant.json --output outputs\feynman-restaurant-result.json
python -m decision_architect analyze examples\feynman-restaurant-short-horizon.json --output outputs\feynman-restaurant-short-horizon-result.json
python -m decision_architect report outputs\job-choice-result.json --output reports\job-choice-report.html
python -m decision_architect report outputs\feynman-restaurant-result.json --output reports\feynman-restaurant-report.html
python -m decision_architect report outputs\feynman-restaurant-short-horizon-result.json --output reports\feynman-restaurant-short-horizon-report.html
python -m decision_architect report-index reports --results-dir outputs
```

`report --open` uses the Python standard library to open the completed local file in the default browser. Rendering failures return non-zero and do not leave a partial output file.

## Data contracts

Input documents conform to `schemas/decision-model-v1.schema.json`; future results conform to `schemas/decision-result-v1.schema.json`. Both include `model_version: "1.0"` and use `model_type` as the discriminator. Calculation output additionally includes `result_version`, `engine_version`, method details, and model-specific reproducibility information.

Recommended output sections:

- `status` and structured validation warnings.
- `model_type`, `schema_version`, and `engine_version`.
- `method` with formula/algorithm identifiers and decision rule.
- `reproducibility` with seed and simulation count when applicable.
- `alternative_results` containing analytical means, analytical utility, Monte Carlo mean utility, win probability, distribution summaries, and clamping diagnostics for feasible alternatives only.
- `excluded_alternatives` containing detailed hard-constraint failures and no utility scores.
- Multi-criteria results contain per-criterion fixed-sample means, baseline contributions, robust weight intervals, and verified switch thresholds.
- Sequential results contain current action values, the complete policy by remaining opportunities, switch points, and deterministic quadrature metadata.
- `recommendation` with selected action or alternative and conditional wording data.

## Testing strategy

- Use `unittest` initially.
- Test pure calculation functions with small hand-checkable cases.
- Fix random seeds and assert stable simulation summaries within explicitly chosen tolerances.
- Include edge cases: infeasible alternatives, equal utilities, zero-width uncertainty, one remaining opportunity, and distributions entirely above or below the known best.
- Keep end-to-end fixture tests from input JSON to result JSON and focused HTML structure tests.
- Keep report rendering tests separate from mathematical correctness tests.

## Deferred implementation choices

- A later result-contract revision may preserve original multi-criteria display labels, eliminating the report-only ID humanization fallback.
- A future reviewed version may add dependency-aware uncertainty through validated correlation matrices, copulas, Bayesian networks, or influence diagrams. None is implemented in `1.0.0-rc1`.

These choices must preserve the approved contracts and require their corresponding reviewed phase.
