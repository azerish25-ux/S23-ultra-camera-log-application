"""TC-P008-02 conflicting source revision with a preserved remote commit."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gates"))
import p008_tc02 as gate


RESULT_KEYS = [
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
]
INSPECTED = "a" * 40
CURRENT = "b" * 40
REMOTE = "d00d" * 10
EVIDENCE = [
    "verified host protocol checker",
    "verified non-destructive capture policy",
    "verified unrelated colour registry",
]


class ConflictingRevisionTests(unittest.TestCase):
    def payload(self, **overrides) -> dict:
        data = {
            "caseId": "TC-P008-02",
            "inspectionRevision": INSPECTED,
            "currentRevision": INSPECTED,
            "incrementalReview": False,
            "changeScope": "none",
            "unrelatedEvidence": list(EVIDENCE),
            "remoteCommit": REMOTE,
        }
        data.update(overrides)
        return data

    def assert_shape(self, result: dict, decision: str, evidence: list[str]) -> None:
        self.assertEqual(RESULT_KEYS, list(result))
        self.assertEqual("TC-P008-02", result["caseId"])
        self.assertEqual(decision, result["decision"])
        self.assertNotIn(result["decision"], {"complete", "allowed", "established"})
        for key in ("reasons", "rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertTrue(result["reasons"])
        self.assertEqual(list(evidence) + [REMOTE], result["preservedResults"])
        self.assertIsNot(evidence, result["preservedResults"])
        self.assertIn(REMOTE, result["preservedResults"])
        for item in evidence:
            self.assertIn(item, result["preservedResults"])
        self.assertEqual([], result["rejectedClaims"])
        self.assertEqual([], result["openQuestions"])

    def test_equal_revisions_are_unchanged_and_keep_remote_commit(self):
        evidence = list(EVIDENCE)
        result = gate.evaluate(self.payload(unrelatedEvidence=evidence))
        self.assert_shape(result, "unchanged", evidence)
        joined = " ".join(result["reasons"])
        self.assertIn("unchanged", joined)
        self.assertIn("completion is not invented", joined)
        self.assertNotIn("documentation", joined)
        self.assertNotIn("capture interface", joined)

    def test_differing_revision_without_review_is_invalidated(self):
        evidence = list(EVIDENCE)
        result = gate.evaluate(self.payload(
            inspectionRevision=INSPECTED,
            currentRevision=CURRENT,
            incrementalReview=False,
            changeScope="none",
            unrelatedEvidence=evidence,
        ))
        self.assert_shape(result, "invalidated", evidence)
        joined = " ".join(result["reasons"])
        self.assertIn("incremental review", joined)
        self.assertIn("not treated as already inspected", joined)
        self.assertNotIn(result["decision"], {"complete", "allowed", "reviewed", "unchanged"})

    def test_false_pass_does_not_treat_new_revision_as_inspected(self):
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
        self.assertIn("documentation", joined)
        self.assertNotIn(result["decision"], {"complete", "allowed"})
        self.assertNotEqual("unchanged", result["decision"])

    def test_incremental_review_is_reviewed_and_not_complete(self):
        evidence = list(EVIDENCE)
        result = gate.evaluate(self.payload(
            inspectionRevision=INSPECTED,
            currentRevision=CURRENT,
            incrementalReview=True,
            changeScope="none",
            unrelatedEvidence=evidence,
        ))
        self.assert_shape(result, "reviewed", evidence)
        joined = " ".join(result["reasons"])
        self.assertIn("does not make the phase complete", joined)
        self.assertNotEqual("complete", result["decision"])
        self.assertNotIn("documentation-only", joined)
        self.assertNotIn("capture interface", joined)

    def test_documentation_scope_is_named(self):
        for incremental, decision in ((False, "invalidated"), (True, "reviewed")):
            result = gate.evaluate(self.payload(
                inspectionRevision=INSPECTED,
                currentRevision=CURRENT,
                incrementalReview=incremental,
                changeScope="documentation",
            ))
            self.assert_shape(result, decision, EVIDENCE)
            joined = " ".join(result["reasons"])
            self.assertIn("documentation", joined)
            self.assertNotEqual("complete", result["decision"])

    def test_capture_interface_scope_is_named(self):
        for incremental, decision in ((False, "invalidated"), (True, "reviewed")):
            result = gate.evaluate(self.payload(
                inspectionRevision=INSPECTED,
                currentRevision=CURRENT,
                incrementalReview=incremental,
                changeScope="capture_interface",
            ))
            self.assert_shape(result, decision, EVIDENCE)
            joined = " ".join(result["reasons"])
            self.assertIn("capture interface", joined)
            self.assertNotEqual("complete", result["decision"])
            self.assertNotEqual("allowed", result["decision"])

    def test_equal_revisions_still_mention_scope_and_preserve_remote_commit(self):
        documentation = gate.evaluate(self.payload(
            incrementalReview=True,
            changeScope="documentation",
            unrelatedEvidence=["doc evidence"],
        ))
        self.assert_shape(documentation, "unchanged", ["doc evidence"])
        self.assertIn("documentation", " ".join(documentation["reasons"]))

        capture = gate.evaluate(self.payload(
            incrementalReview=False,
            changeScope="capture_interface",
            unrelatedEvidence=[],
        ))
        self.assert_shape(capture, "unchanged", [])
        self.assertEqual([REMOTE], capture["preservedResults"])
        self.assertIn("capture interface", " ".join(capture["reasons"]))

    def test_evidence_order_is_preserved_ahead_of_remote_commit(self):
        evidence = ["second-looking item", "first-looking item"]
        result = gate.evaluate(self.payload(
            currentRevision=CURRENT,
            incrementalReview=False,
            unrelatedEvidence=evidence,
        ))
        self.assert_shape(result, "invalidated", evidence)
        self.assertEqual(evidence + [REMOTE], result["preservedResults"])

    def test_bad_payload_and_case_id_raise(self):
        for payload in (None, [], "TC-P008-02", 0):
            with self.assertRaises(ValueError):
                gate.evaluate(payload)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(caseId="TC-P008-01"))
        missing = self.payload()
        del missing["remoteCommit"]
        with self.assertRaises(ValueError):
            gate.evaluate(missing)
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(changeScope="firmware"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(unrelatedEvidence=["ok", 1]))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(unrelatedEvidence="not-a-list"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(incrementalReview="false"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(inspectionRevision="  "))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(currentRevision=""))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(remoteCommit=None))


if __name__ == "__main__":
    unittest.main()
