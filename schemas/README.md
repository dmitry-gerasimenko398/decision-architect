# Versioned JSON contracts

Phase 2 introduced two JSON Schema Draft 2020-12 interoperability contracts. Phases 3 and 4 extended their model-specific branches before generating calculation results:

- `decision-model-v1.schema.json` describes confirmed calculation inputs.
- `decision-result-v1.schema.json` describes calculation outputs.

Both use `model_type` as a discriminator and require `model_version` to be `1.0`.

The schemas document file interchange. Runtime input validation is implemented manually in `decision_architect/validation.py` using only Python's standard library. Cross-field rules that JSON Schema cannot conveniently express, such as weights summing to 1 and every alternative containing every criterion estimate, are enforced by that Python validator.

Phase 3 adds executable hard-constraint fields (`criterion_id`, `operator`, and `threshold`) while preserving each alternative's confirmed `constraint_results` booleans. The engine recomputes and cross-checks those booleans. The result contract now separates feasible `alternative_results` from `excluded_alternatives` and records analytical cross-checks, Monte Carlo summaries, clamping diagnostics, method details, and reproducibility metadata.

Phase 4 adds optional sequential `analysis_settings.quadrature_points` (default 101; explicit values must be positive and odd). Sequential results record current action values, the full policy by remaining opportunities, action-switch points, deterministic midpoint-quantile quadrature settings, and memoization precision without changing the Phase 3 multi-criteria result branch.

Phase 5 extends multi-criteria alternative results with fixed-sample criterion means and baseline weighted contributions. Its required sensitivity section records analytical one-weight winner-switch thresholds, robust intervals, tie states, verification probes, and not-applicable edge cases. Sequential mathematics and input contracts are unchanged.

Phase 6 does not change either JSON contract. The report generator consumes and validates saved result-v1 documents without adding fields, recalculating values, or modifying the source file. Project/report version `0.5.0` therefore remains separate from the calculation engine version recorded in unchanged result artifacts.

Phase 7 also leaves both mathematical contracts unchanged. Versioned interview state is an internal local session record; only `confirmed-model.json` crosses into decision-model-v1. Project/Skill version `0.6.0` therefore does not alter historical model or result values.

Release `1.0.0-rc1` freezes both contracts at `1.0`. The mathematical engine remains accurately recorded as `0.4.0` in result artifacts, while the current report generator and overall release are `1.0.0-rc1`. Presentation and documentation changes do not rewrite demonstrated numerical values.

To accommodate ordinary floating-point representation without changing user data, the validator accepts a weight sum within an absolute tolerance of `1e-9` from 1. It never renormalizes or rewrites the submitted weights.
