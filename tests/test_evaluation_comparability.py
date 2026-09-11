"""Interpretation ceiling tests; pure comparison is not Runtime admission."""

import copy
import unittest

from research_workbench.evaluation.comparability import derive_comparability
from research_workbench.evaluation.pins import EvaluationValidationError


class PairwiseComparisonTests(unittest.TestCase):
    def setUp(self):
        self.surface = {
            key: ["exact"]
            for key in (
                "tasks",
                "methods",
                "requirements",
                "non_skill_components",
                "non_skill_supplies",
                "interfaces",
                "supply_boundaries",
                "execution_bindings",
                "execution_constraints",
            )
        }

    def test_exact_equality_allows_only_conditional_skill_interpretation(self):
        result = derive_comparability(
            self.surface, self.surface, admitted_skill_count=1
        )
        self.assertEqual(result["status"], "exact-skill-only")
        self.assertEqual(result["interpretation"], "skill-conditional-increment")

    def test_method_supply_tool_interface_and_boundary_deltas_are_package_effects(self):
        for key in (
            "methods",
            "requirements",
            "non_skill_components",
            "non_skill_supplies",
            "interfaces",
            "supply_boundaries",
            "execution_constraints",
        ):
            changed = copy.deepcopy(self.surface)
            changed[key] = ["changed"]
            with self.subTest(key=key):
                result = derive_comparability(
                    self.surface, changed, admitted_skill_count=1
                )
                self.assertEqual(result["status"], "skill-bearing-package")
                self.assertEqual(result["mismatches"], [key])

    def test_missing_shared_conditions_or_wrong_admitted_extension_is_unavailable(self):
        for key in ("tasks", "execution_bindings", "interfaces"):
            changed = copy.deepcopy(self.surface)
            changed[key] = []
            self.assertEqual(
                derive_comparability(self.surface, changed, admitted_skill_count=1)[
                    "status"
                ],
                "not-comparable",
            )
        for count in (0, 2):
            self.assertEqual(
                derive_comparability(
                    self.surface, self.surface, admitted_skill_count=count
                )["interpretation"],
                "unavailable",
            )
        with self.assertRaises(EvaluationValidationError):
            derive_comparability({}, self.surface, admitted_skill_count=1)
