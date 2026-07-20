# Judging guide

This guide maps likely judging dimensions to concrete release evidence without making claims beyond the implemented MVP.

## Technological implementation

- Two distinct deterministic engines:
  - `decision_architect/multi_criteria.py`
  - `decision_architect/sequential_exploration.py`
- Analytical fixed-sample sensitivity in `decision_architect/sensitivity.py`.
- Executable manual validation in `decision_architect/validation.py` and `decision_architect/result_serialization.py`.
- Versioned contracts in `schemas/decision-model-v1.schema.json` and `schemas/decision-result-v1.schema.json`.
- Confirmation-gated persistence in `decision_architect/session_state.py`.
- Deterministic accessible reports in `decision_architect/reporting.py`, `report_templates.py`, and `svg_charts.py`.
- One-command standard-library verification: `py -m decision_architect verify-release`.

## Product design

- Explicit Skill invocation: `$decision-analysis`.
- Adaptive small-batch interview in `.agents/skills/decision-analysis/`.
- Plain-language model selection and honest unsupported-case handling.
- User review fingerprints and exact `CONFIRM` gate.
- Separate hard constraints, weighted preferences, assumptions, uncertainty, and reproducibility settings.
- Standalone reports in `reports/` with numerical alternatives for charts, visible conditionality, and escaped audit data.

## Potential impact

- Reusable across personal one-time comparisons and finite explore-versus-exploit decisions.
- Makes subjective inputs and approximations inspectable rather than hiding them in a conversational answer.
- Runs locally without an API key or external backend for the contest version.
- Produces artifacts that a user or reviewer can reproduce and challenge.

This is decision support. High-stakes use still requires appropriate professional or domain expertise.

## Quality and originality

- Combines a conversational Codex Skill with deterministic mathematical execution rather than asking the language model to calculate.
- Supports both Monte Carlo multi-criteria analysis and finite-horizon dynamic programming.
- Reports conditions under which a recommendation changes.
- Treats confirmation as a technical gate, not a conversational formality.
- Includes two successful live human acceptance tests and a complete automated release-verification suite.

## Demonstration evidence

- Feynman-inspired dish transcript: `examples/conversations/feynman-restaurant-interview.md`.
- Job transcript: `examples/conversations/job-choice-interview.md`.
- Sanitized university acceptance transcript: `examples/conversations/university-transfer-interview.md`.
- Released models: `examples/*.json`.
- Exact stored outputs: `outputs/*.json`.
- Visual reports: `reports/index.html`.
- Release evaluation: `EVALUATION.md`.
- Contest shot list: `docs/CONTEST_DEMO.md`.
