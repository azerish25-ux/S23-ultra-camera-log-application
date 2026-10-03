"""Host tests for the TC-P007-02 revision-conflict gate."""

import copy
import sys
import unittest

sys.path.insert(0, "/workspace/s23/scripts/gates")

from p007_tc02 import evaluate


H1 = "a" * 64
H2 = "b" * 64
H3 = "c" * 64
NAME = "Stock Neutral"
INSPECTED = "1111111111111111111111111111111111111111"
CURRENT = "2222222222222222222222222222222222222222"


def payload(**overrides):
    base = {
        "caseId": "TC-P007-02",
        "inspectionRevision": INSPECTED,
        "currentRevision": CURRENT,
        "incrementalReview": False,
        "changeScope": "none",
        "unrelatedEvidence": ["verified-colour-table", "verified-timing-log"],
        "profiles": [
            {"displayName": NAME, "sha256": H1},
            {"displayName": NAME, "sha256": H2},
        ],
    }
    base.update(overrides)
    return base


def hashes_of(result):
    return [item for item in result["preservedResults"] if item in {H1, H2, H3}]


class Tcp00702Tests(unittest.TestCase):
    def assert_contract(self, result, decision):
        self.assertEqual(
            set(result),
            {
                "caseId",
                "decision",
                "reasons",
                "rejectedClaims",
                "preservedResults",
                "openQuestions",
            },
        )
        self.assertEqual(result["caseId"], "TC-P007-02")
        self.assertEqual(result["decision"], decision)
        self.assertNotEqual(result["decision"], "allowed")
        for key in ("reasons", "rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        if result["decision"] != "allowed":
            self.assertTrue(result["reasons"])

    def test_distinct_hashes_survive_matching_display_names(self):
        result = evaluate(payload())
        self.assertEqual(hashes_of(result), [H1, H2])
        self.assertNotEqual(hashes_of(result), [H2])
        self.assertNotIn(NAME, result["preservedResults"])
        text = " ".join(result["reasons"]).lower()
        self.assertIn("distinct", text)
        self.assertIn("display name", text)

    def test_revision_conflict_without_review_is_invalidated(self):
        evidence = ["verified-colour-table", "verified-timing-log"]
        result = evaluate(payload(unrelatedEvidence=evidence, changeScope="documentation"))
        self.assert_contract(result, "invalidated")
        self.assertNotEqual(result["decision"], "allowed")
        self.assertNotEqual(result["decision"], "unchanged")
        self.assertNotEqual(result["decision"], "reviewed")
        for item in evidence:
            self.assertIn(item, result["preservedResults"])
            self.assertNotIn(item, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], [H1, H2, *evidence])
        text = " ".join(result["reasons"]).lower()
        self.assertIn("invalidat", text)
        self.assertNotIn("already inspected", text.replace("not treated as already inspected", ""))
        self.assertIn("not treated as already inspected", text)

    def test_incremental_review_names_documentation_scope(self):
        result = evaluate(
            payload(incrementalReview=True, changeScope="documentation")
        )
        self.assert_contract(result, "reviewed")
        text = " ".join(result["reasons"]).lower()
        self.assertIn("documentation", text)
        self.assertNotIn("capture interface", text)
        self.assertIn("verified-colour-table", result["preservedResults"])
        self.assertEqual(hashes_of(result), [H1, H2])

    def test_incremental_review_names_capture_interface_scope(self):
        result = evaluate(
            payload(incrementalReview=True, changeScope="capture_interface")
        )
        self.assert_contract(result, "reviewed")
        text = " ".join(result["reasons"])
        self.assertIn("capture interface", text)
        self.assertIn("capture_interface", text)
        self.assertNotIn("documentation", text)
        self.assertEqual(
            result["preservedResults"],
            [H1, H2, "verified-colour-table", "verified-timing-log"],
        )

    def test_incremental_review_of_scope_none(self):
        result = evaluate(payload(incrementalReview=True, changeScope="none"))
        self.assert_contract(result, "reviewed")
        text = " ".join(result["reasons"]).lower()
        self.assertIn("none", text)
        self.assertNotIn("documentation", text)
        self.assertNotIn("capture interface", text)

    def test_equal_revisions_are_unchanged(self):
        result = evaluate(
            payload(
                currentRevision=INSPECTED,
                incrementalReview=False,
                changeScope="none",
            )
        )
        self.assert_contract(result, "unchanged")
        self.assertEqual(hashes_of(result), [H1, H2])
        self.assertIn("verified-timing-log", result["preservedResults"])
        text = " ".join(result["reasons"]).lower()
        self.assertIn("unchanged", text)

    def test_equal_revisions_ignore_stale_incremental_scope(self):
        result = evaluate(
            payload(
                currentRevision=INSPECTED,
                incrementalReview=True,
                changeScope="capture_interface",
            )
        )
        self.assert_contract(result, "unchanged")
        self.assertNotEqual(result["decision"], "reviewed")
        self.assertNotEqual(result["decision"], "invalidated")

    def test_empty_unrelated_evidence_still_keeps_hashes(self):
        result = evaluate(payload(unrelatedEvidence=[]))
        self.assert_contract(result, "invalidated")
        self.assertEqual(result["preservedResults"], [H1, H2])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], [])

    def test_profile_order_and_alias_hash_are_stable(self):
        profiles = [
            {"displayName": "Alias", "sha256": H2},
            {"displayName": NAME, "sha256": H1},
            {"displayName": NAME, "sha256": H2},
            {"displayName": "Other", "sha256": H3},
        ]
        result = evaluate(
            payload(profiles=profiles, currentRevision=INSPECTED, unrelatedEvidence=["keep-me"])
        )
        self.assertEqual(result["decision"], "unchanged")
        self.assertEqual(hashes_of(result), [H2, H1, H3])
        self.assertIn("keep-me", result["preservedResults"])

    def test_case_differing_revisions_are_not_equal(self):
        result = evaluate(
            payload(inspectionRevision="AbC", currentRevision="abc", incrementalReview=False)
        )
        self.assertEqual(result["decision"], "invalidated")

    def test_payload_is_not_mutated(self):
        body = payload()
        snapshot = copy.deepcopy(body)
        evaluate(body)
        self.assertEqual(body, snapshot)

    def test_bad_payload_and_wrong_case_raise(self):
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(None)
        with self.assertRaises(ValueError):
            evaluate(payload(caseId="TC-P007-01"))
        missing = payload()
        del missing["currentRevision"]
        with self.assertRaises(ValueError):
            evaluate(missing)
        with self.assertRaises(ValueError):
            evaluate(payload(incrementalReview="true"))
        with self.assertRaises(ValueError):
            evaluate(payload(changeScope="docs"))
        with self.assertRaises(ValueError):
            evaluate(payload(changeScope="capture-interface"))
        with self.assertRaises(ValueError):
            evaluate(payload(unrelatedEvidence="verified-colour-table"))
        with self.assertRaises(ValueError):
            evaluate(payload(unrelatedEvidence=["ok", ""]))
        with self.assertRaises(ValueError):
            evaluate(payload(inspectionRevision=""))
        with self.assertRaises(ValueError):
            evaluate(payload(profiles=[{"displayName": NAME, "sha256": H1}, "bad"]))
        with self.assertRaises(ValueError):
            evaluate(payload(profiles={"displayName": NAME, "sha256": H1}))


if __name__ == "__main__":
    unittest.main()
