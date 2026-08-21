import unittest

from research_workbench.examples.sir_canary import simulate_sir, verification_report


class SirCanaryTests(unittest.TestCase):
    def test_fixed_public_canary_passes_all_numerical_checks(self) -> None:
        report = verification_report()
        self.assertEqual("SIM-SIR-001", report["case_id"])
        self.assertEqual("passed", report["status"])
        self.assertTrue(all(report["checks"].values()))
        errors = report["euler_final_l1_errors"]
        self.assertGreater(errors["1.0"], errors["0.5"])
        self.assertGreater(errors["0.5"], errors["0.25"])

    def test_invalid_initial_state_and_method_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            simulate_sir(initial=(1000.0, 1.0, 0.0))
        with self.assertRaises(ValueError):
            simulate_sir(method="invented")


if __name__ == "__main__":
    unittest.main()
