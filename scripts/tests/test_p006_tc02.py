"""TC-P006-02 conflicting source revision decision gate."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gates"))
import p006_tc02 as gate


RESULT_KEYS = ["caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"]
INSPECTED = "a" * 40
CURRENT = "b" * 40
EVIDENCE = [
    "verified colour registry",
    "verified non-destructive capture policy",
    "verified application-level route inventory",
]


class ConflictingRevisionTests(unittest.TestCase):
    def payload(self, **overrides) -> dict:
        data = {
            "caseId": "TC-P006-02",
            "inspectionRevision": INSPECTED,
            "currentRevision": INSPECTED,
            "incrementalReview": False,
            "changeScope": "none",
            "unrelatedEvidence": list(EVIDENCE),
        }
        data.update(overrides)
        return data

    def assert_shape(self, result: dict, decision: str, evidence: list[str]) -> None:
        self.assertEqual(RESULT_KEYS, list(result))
        self.assertEqual("TC-P006-02", result["caseId"])
        self.assertEqual(decision, result["decision"])
        self.assertNotEqual("allowed", result["decision"])
        self.assertNotEqual("established", result["decision"])
        for key in ("reasons", "rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertTrue(result["reasons"])
        self.assertEqual(evidence, result["preservedResults"])
        self.assertIsNot(evidence, result["preservedResults"])
        self.assertEqual([], result["rejectedClaims"])
        self.assertEqual([], result["openQuestions"])

    def test_baseline_equal_revisions_are_unchanged(self):
        evidence = list(EVIDENCE)
        result = gate.evaluate(self.payload(unrelatedEvidence=evidence))
        self.assert_shape(result, "unchanged", evidence)
        self.assertIn("unchanged", " ".join(result["reasons"]))
        self.assertNotIn("incremental review", " ".join(result["reasons"]))

    def test_adversarial_operation_invalidates_revision_without_incremental_review(self):
        evidence = list(EVIDENCE)
        result = gate.evaluate(self.payload(
            inspectionRevision=INSPECTED,
            currentRevision=CURRENT,
            incrementalReview=False,
            changeScope="none",
            unrelatedEvidence=evidence,
        ))
        self.assert_shape(result, "invalidated", evidence)
        self.assertIn("incremental review", " ".join(result["reasons"]))
        self.assertNotEqual("allowed", result["decision"])

    def test_false_pass_control_does_not_treat_new_revision_as_inspected(self):
        evidence = ["already inspected appearance", "unrelated verified ledger"]
        result = gate.evaluate(self.payload(
            inspectionRevision=INSPECTED,
            currentRevision=CURRENT,
            incrementalReview=False,
            changeScope="documentation",
            unrelatedEvidence=evidence,
        ))
        self.assert_shape(result, "invalidated", evidence)
        joined = " ".join(result["reasons"])
        self.assertIn("incremental review", joined)
        self.assertNotIn(result["decision"], {"allowed", "unchanged", "reviewed"})
        self.assertNotIn("documentation-only", joined)

    def test_repetition_documentation_only(self):
        evidence = list(EVIDENCE)
        result = gate.evaluate(self.payload(
            inspectionRevision=INSPECTED,
            currentRevision=CURRENT,
            incrementalReview=True,
            changeScope="documentation",
            unrelatedEvidence=evidence,
        ))
        self.assert_shape(result, "reviewed", evidence)
        joined = " ".join(result["reasons"])
        self.assertIn("documentation-only", joined)
        self.assertNotIn("capture interface", joined)
        self.assertNotEqual("allowed", result["decision"])
        self.assertNotEqual("invalidated", result["decision"])

    def test_repetition_capture_interface(self):
        evidence = list(EVIDENCE)
        result = gate.evaluate(self.payload(
            inspectionRevision=INSPECTED,
            currentRevision=CURRENT,
            incrementalReview=True,
            changeScope="capture_interface",
            unrelatedEvidence=evidence,
        ))
        self.assert_shape(result, "reviewed", evidence)
        joined = " ".join(result["reasons"])
        self.assertIn("capture interface", joined)
        self.assertNotIn("documentation-only", joined)
        self.assertNotEqual("allowed", result["decision"])
        self.assertNotEqual("invalidated", result["decision"])

    def test_reviewed_revision_with_no_declared_scope_preserves_evidence(self):
        evidence = ["unrelated verified evidence"]
        result = gate.evaluate(self.payload(
            inspectionRevision=INSPECTED,
            currentRevision=CURRENT,
            incrementalReview=True,
            changeScope="none",
            unrelatedEvidence=evidence,
        ))
        self.assert_shape(result, "reviewed", evidence)
        self.assertIn("Incremental review", result["reasons"][0])

    def test_equal_revisions_ignore_scope_and_keep_evidence_order(self):
        evidence = ["second-looking item", "first-looking item"]
        result = gate.evaluate(self.payload(
            currentRevision=INSPECTED,
            incrementalReview=True,
            changeScope="capture_interface",
            unrelatedEvidence=evidence,
        ))
        self.assert_shape(result, "unchanged", evidence)

    def test_non_dict_payload_and_case_id_mismatch_raise(self):
        with self.assertRaises(ValueError):
            gate.evaluate(None)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(caseId="TC-P006-01"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(changeScope="firmware"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(unrelatedEvidence=["ok", 1]))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(incrementalReview="false"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(inspectionRevision="HEAD", currentRevision="HEAD"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(inspectionRevision="A" * 40, currentRevision="A" * 40))


if __name__ == "__main__":
    unittest.main()
