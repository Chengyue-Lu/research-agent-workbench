import unittest

from research_workbench.kernel import Claim, Evidence, ObjectRef, Question


class KernelObjectTests(unittest.TestCase):
    def test_revision_is_part_of_object_reference(self) -> None:
        question = Question(object_id="Q-001", revision=2, text="What changed?")
        self.assertEqual(ObjectRef("Q-001", 2), question.ref)

    def test_claim_keeps_support_and_counterevidence_separate(self) -> None:
        supporting = Evidence(object_id="E-001", statement="supports")
        opposing = Evidence(object_id="E-002", statement="limits")
        claim = Claim(
            object_id="C-001",
            support_refs=[supporting.ref],
            counterevidence_refs=[opposing.ref],
        )
        self.assertEqual([ObjectRef("E-001", 1)], claim.support_refs)
        self.assertEqual([ObjectRef("E-002", 1)], claim.counterevidence_refs)


if __name__ == "__main__":
    unittest.main()
