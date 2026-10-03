"""TC-P006-06: an uncontrolled threshold revision must not erase a failure."""

from __future__ import annotations

import math
import sys
import unittest

sys.path.insert(0, "/workspace/s23/scripts/gates")

from p006_tc06 import evaluate

CASE_ID = "TC-P006-06"
KEYS = ["caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"]

# Repetition plan: cadence, color error, render latency, temporal artifact severity.
REPETITIONS = (
    ("cadence", "frames", "cadence", 1, 4),
    ("color error", "deltaE", "display_value", 2, 8),
    ("render latency", "ms", "elapsed_ms", 16, 40),
    ("temporal artifact severity", "score", "temporal_artifact", 3, 9),
)


def threshold(name, original, proposed, unit, domain, loosened, reviewed, version_recorded, original_failed):
    return {
        "name": name,
        "originalValue": original,
        "proposedValue": proposed,
        "unit": unit,
        "domain": domain,
        "loosened": loosened,
        "reviewed": reviewed,
        "versionRecorded": version_recorded,
        "originalFailed": original_failed,
    }


def payload(body, case_id=CASE_ID):
    return {"caseId": case_id, "threshold": body}


def proposed_claim(body):
    return (
        f"proposed-change:{body['name']}:"
        f"{body['originalValue']}->{body['proposedValue']}:"
        f"{body['unit']}:{body['domain']}"
    )


def assert_contract(test, result):
    test.assertEqual(list(result.keys()), KEYS)
    test.assertEqual(result["caseId"], CASE_ID)
    test.assertNotEqual(result["decision"], "allowed")
    for key in ("reasons", "rejectedClaims", "preservedResults", "openQuestions"):
        test.assertIsInstance(result[key], list)
        test.assertTrue(all(isinstance(item, str) and item for item in result[key]))
    test.assertTrue(result["reasons"])
    serialized = " ".join(
        result["reasons"] + result["rejectedClaims"] + result["preservedResults"] + result["openQuestions"]
    ).lower()
    test.assertNotIn("original run passed", serialized)
    test.assertNotIn("decision allowed", serialized)


class UncontrolledThresholdRevisionTests(unittest.TestCase):
    def test_loosened_without_review_or_version_is_blocked(self):
        body = threshold("cadence", 1, 4, "frames", "cadence", True, False, False, True)
        result = evaluate(payload(body))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "blocked")
        self.assertIn("original-failure:cadence", result["preservedResults"])
        self.assertIn(proposed_claim(body), result["rejectedClaims"])
        self.assertIn("original-pass:cadence", result["rejectedClaims"])
        self.assertNotEqual(result["decision"], "allowed")

    def test_review_without_version_record_stays_blocked(self):
        body = threshold("color error", 2, 8, "deltaE", "display_value", True, True, False, True)
        result = evaluate(payload(body))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "blocked")
        self.assertIn("original-failure:color error", result["preservedResults"])
        self.assertIn(proposed_claim(body), result["rejectedClaims"])

    def test_version_record_without_review_stays_blocked(self):
        body = threshold("render latency", 16, 40, "ms", "elapsed_ms", True, False, True, True)
        result = evaluate(payload(body))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "blocked")
        self.assertIn("original-failure:render latency", result["preservedResults"])
        self.assertIn(proposed_claim(body), result["rejectedClaims"])
        self.assertTrue(any("not reviewed" in reason for reason in result["reasons"]))

    def test_reviewed_versioned_revision_requires_renewed_validation(self):
        body = threshold(
            "temporal artifact severity", 3, 9, "score", "temporal_artifact",
            True, True, True, True,
        )
        result = evaluate(payload(body))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "reviewed_revision")
        self.assertTrue(any("renewed validation" in reason for reason in result["reasons"]))
        self.assertIn("original-failure:temporal artifact severity", result["preservedResults"])
        self.assertIn("original-pass:temporal artifact severity", result["rejectedClaims"])
        self.assertNotIn(proposed_claim(body), result["rejectedClaims"])
        self.assertNotEqual(result["decision"], "allowed")
        self.assertNotEqual(result["decision"], "blocked")

    def test_reviewed_revision_without_original_failure_still_does_not_claim_a_pass(self):
        body = threshold("cadence", 1, 4, "frames", "cadence", True, True, True, False)
        result = evaluate(payload(body))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "reviewed_revision")
        self.assertTrue(any("renewed validation" in reason for reason in result["reasons"]))
        self.assertNotIn("original-failure:cadence", result["preservedResults"])
        self.assertNotEqual(result["decision"], "allowed")

    def test_loosened_blocked_even_when_original_failure_flag_is_false(self):
        body = threshold("cadence", 1, 4, "frames", "cadence", True, False, False, False)
        result = evaluate(payload(body))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "blocked")
        self.assertIn("original-failure:cadence", result["preservedResults"])
        self.assertIn(proposed_claim(body), result["rejectedClaims"])
        self.assertNotEqual(result["decision"], "allowed")

    def test_not_loosened_original_failure_stays_failed(self):
        body = threshold("color error", 2, 2, "deltaE", "display_value", False, False, False, True)
        result = evaluate(payload(body))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "failed")
        self.assertIn("original-failure:color error", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_not_loosened_and_not_failed_is_unchanged(self):
        body = threshold("render latency", 16, 16, "ms", "elapsed_ms", False, True, True, False)
        result = evaluate(payload(body))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], [])
        self.assertEqual(result["openQuestions"], [])

    def test_repetition_cadence_color_error_render_latency_temporal_artifact(self):
        for name, unit, domain, original, proposed in REPETITIONS:
            uncontrolled = threshold(name, original, proposed, unit, domain, True, False, False, True)
            blocked = evaluate(payload(uncontrolled))
            assert_contract(self, blocked)
            self.assertEqual(blocked["decision"], "blocked")
            self.assertIn(f"original-failure:{name}", blocked["preservedResults"])
            self.assertIn(proposed_claim(uncontrolled), blocked["rejectedClaims"])
            self.assertNotEqual(blocked["decision"], "allowed")

            partial = threshold(name, original, proposed, unit, domain, True, True, False, True)
            still_blocked = evaluate(payload(partial))
            assert_contract(self, still_blocked)
            self.assertEqual(still_blocked["decision"], "blocked")
            self.assertIn(f"original-failure:{name}", still_blocked["preservedResults"])

            reviewed = threshold(name, original, proposed, unit, domain, True, True, True, True)
            revision = evaluate(payload(reviewed))
            assert_contract(self, revision)
            self.assertEqual(revision["decision"], "reviewed_revision")
            self.assertTrue(any("renewed validation" in reason for reason in revision["reasons"]))
            self.assertIn(f"original-failure:{name}", revision["preservedResults"])
            self.assertNotEqual(revision["decision"], "allowed")

            failed = evaluate(payload(threshold(
                name, original, original, unit, domain, False, False, False, True,
            )))
            assert_contract(self, failed)
            self.assertEqual(failed["decision"], "failed")
            self.assertIn(f"original-failure:{name}", failed["preservedResults"])

            unchanged = evaluate(payload(threshold(
                name, original, proposed, unit, domain, False, False, False, False,
            )))
            assert_contract(self, unchanged)
            self.assertEqual(unchanged["decision"], "unchanged")

    def test_wrong_case_id_and_bad_payload_raise_value_error(self):
        good = threshold("cadence", 1, 4, "frames", "cadence", True, False, False, True)
        with self.assertRaises(ValueError):
            evaluate(payload(good, case_id="TC-P006-05"))
        for bad in (
            None,
            [],
            {"caseId": CASE_ID},
            {"caseId": CASE_ID, "threshold": None},
            {"caseId": CASE_ID, "threshold": []},
            payload({**good, "name": ""}),
            payload({**good, "originalValue": "1"}),
            payload({**good, "proposedValue": math.nan}),
            payload({**good, "proposedValue": True}),
            payload({**good, "unit": None}),
            payload({**good, "domain": "  "}),
            payload({**good, "loosened": 1}),
            payload({**good, "reviewed": "yes"}),
            payload({**good, "versionRecorded": None}),
            payload({**good, "originalFailed": 0}),
            {"threshold": good},
        ):
            with self.assertRaises(ValueError):
                evaluate(bad)


if __name__ == "__main__":
    unittest.main()
