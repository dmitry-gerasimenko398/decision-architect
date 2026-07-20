"""Tests for the Phase 2 model contracts and manual validator."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from decision_architect.models import MultiCriteriaModel, SequentialExplorationModel
from decision_architect.validation import load_validated_model, validate_model


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"
SCHEMAS = PROJECT_ROOT / "schemas"


def load_example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def issue_codes(model: dict) -> set[str]:
    return {issue.code for issue in validate_model(model)}


class ValidModelTests(unittest.TestCase):
    def test_job_choice_passes_and_builds_typed_model(self) -> None:
        model = load_validated_model(EXAMPLES / "job-choice.json")
        self.assertIsInstance(model, MultiCriteriaModel)
        self.assertEqual(len(model.alternatives), 3)
        self.assertEqual(len(model.criteria), 4)

    def test_feynman_restaurant_passes_and_builds_typed_model(self) -> None:
        model = load_validated_model(EXAMPLES / "feynman-restaurant.json")
        self.assertIsInstance(model, SequentialExplorationModel)
        self.assertEqual(model.state.remaining_opportunities, 8)
        self.assertEqual(model.utility_scale.maximum, 10)

    def test_schema_documents_are_valid_json_with_both_discriminators(self) -> None:
        for filename in ("decision-model-v1.schema.json", "decision-result-v1.schema.json"):
            schema = json.loads((SCHEMAS / filename).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            serialized = json.dumps(schema)
            self.assertIn("multi_criteria", serialized)
            self.assertIn("sequential_exploration", serialized)
            if filename == "decision-result-v1.schema.json":
                self.assertIn("mean_utility_tie", serialized)
                self.assertIn("indifferent", serialized)
            local_references = []

            def collect_references(value: object) -> None:
                if isinstance(value, dict):
                    for key, child in value.items():
                        if key == "$ref" and isinstance(child, str) and child.startswith("#/$defs/"):
                            local_references.append(child.removeprefix("#/$defs/"))
                        collect_references(child)
                elif isinstance(value, list):
                    for child in value:
                        collect_references(child)

            collect_references(schema)
            for reference in local_references:
                self.assertIn(reference, schema["$defs"], f"Broken local schema reference: {reference}")


class InvalidMultiCriteriaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = load_example("job-choice.json")

    def test_malformed_triangular_distribution_fails(self) -> None:
        model = copy.deepcopy(self.model)
        model["alternatives"][0]["criterion_estimates"]["salary"] = {
            "minimum": 80000,
            "most_likely": 75000,
            "maximum": 70000,
        }
        self.assertIn("invalid_triangular_distribution", issue_codes(model))

    def test_weights_that_do_not_sum_to_one_fail(self) -> None:
        model = copy.deepcopy(self.model)
        model["criteria"][0]["weight"] = 0.34
        self.assertIn("weights_not_normalized", issue_codes(model))

    def test_negative_weight_fails(self) -> None:
        model = copy.deepcopy(self.model)
        model["criteria"][0]["weight"] = -0.1
        self.assertIn("negative_weight", issue_codes(model))

    def test_missing_criterion_estimate_fails(self) -> None:
        model = copy.deepcopy(self.model)
        del model["alternatives"][0]["criterion_estimates"]["salary"]
        issues = validate_model(model)
        self.assertTrue(
            any(
                issue.code == "missing_criterion_estimate" and issue.path.endswith(".salary")
                for issue in issues
            )
        )

    def test_duplicate_ids_fail(self) -> None:
        model = copy.deepcopy(self.model)
        model["alternatives"][1]["id"] = model["alternatives"][0]["id"]
        self.assertIn("duplicate_id", issue_codes(model))

    def test_invalid_utility_anchors_fail(self) -> None:
        model = copy.deepcopy(self.model)
        model["criteria"][0]["best_anchor"] = model["criteria"][0]["worst_anchor"]
        self.assertIn("invalid_utility_anchors", issue_codes(model))

    def test_unknown_model_type_fails(self) -> None:
        model = copy.deepcopy(self.model)
        model["model_type"] = "unsupported_model"
        self.assertIn("unknown_model_type", issue_codes(model))

    def test_disabled_clamping_fails(self) -> None:
        model = copy.deepcopy(self.model)
        model["analysis_settings"]["clamp_utility"] = False
        self.assertIn("clamping_required", issue_codes(model))

    def test_unknown_constraint_criterion_fails(self) -> None:
        model = copy.deepcopy(self.model)
        model["hard_constraints"][0]["criterion_id"] = "not_a_criterion"
        self.assertIn("unknown_criterion_id", issue_codes(model))


class InvalidSequentialExplorationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = load_example("feynman-restaurant.json")

    def test_remaining_opportunities_below_one_fails(self) -> None:
        model = copy.deepcopy(self.model)
        model["state"]["remaining_opportunities"] = 0
        self.assertIn("invalid_remaining_opportunities", issue_codes(model))

    def test_unseen_options_below_zero_fails(self) -> None:
        model = copy.deepcopy(self.model)
        model["state"]["unseen_options_remaining"] = -1
        self.assertIn("invalid_unseen_options", issue_codes(model))

    def test_best_known_value_outside_scale_fails(self) -> None:
        model = copy.deepcopy(self.model)
        model["state"]["best_known_value"] = 11
        self.assertIn("best_known_outside_scale", issue_codes(model))

    def test_new_option_distribution_outside_scale_fails(self) -> None:
        model = copy.deepcopy(self.model)
        model["new_option_distribution"]["maximum"] = 11
        self.assertIn("distribution_outside_scale", issue_codes(model))

    def test_impossible_utility_scale_fails(self) -> None:
        model = copy.deepcopy(self.model)
        model["utility_scale"]["minimum"] = 10
        self.assertIn("invalid_utility_scale", issue_codes(model))

    def test_malformed_new_option_distribution_fails(self) -> None:
        model = copy.deepcopy(self.model)
        model["new_option_distribution"]["most_likely"] = 11
        self.assertIn("invalid_triangular_distribution", issue_codes(model))

    def test_even_quadrature_points_fail_clearly(self) -> None:
        model = copy.deepcopy(self.model)
        model["analysis_settings"]["quadrature_points"] = 100
        self.assertIn("invalid_quadrature_points", issue_codes(model))

    def test_non_positive_quadrature_points_fail_clearly(self) -> None:
        model = copy.deepcopy(self.model)
        model["analysis_settings"]["quadrature_points"] = -1
        self.assertIn("invalid_quadrature_points", issue_codes(model))


if __name__ == "__main__":
    unittest.main()
