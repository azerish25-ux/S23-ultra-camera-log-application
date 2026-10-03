"""TC-P006-04 contradictory outcomes: baseline, adversarial, false-pass, repetition."""

import sys
import unittest

sys.path.insert(0, "/workspace/s23/scripts/gates")

import p006_tc04

CASE_ID = "TC-P006-04"
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _payload(
    summary_passed=True,
    raw_failed=False,
    skipped_physical_as_pass=False,
    stale_report=False,
    raw_log_id="raw-log-001",
    case_id=CASE_ID,
):
    return {
        "caseId": case_id,
        "summaryPassed": summary_passed,
        "rawFailed": raw_failed,
        "skippedPhysicalAsPass": skipped_physical_as_pass,
        "staleReport": stale_report,
        "rawLogId": raw_log_id,
    }


class P006Tc04Tests(unittest.TestCase):
    def test_payload_must_be_dict(self):
        for payload in (None, [], "TC-P006-04", 0):
            with self.assertRaises(ValueError):
                p006_tc04.evaluate(payload)

    def test_case_id_mismatch(self):
        payload = _payload()
        payload["caseId"] = "TC-P006-03"
        with self.assertRaises(ValueError):
            p006_tc04.evaluate(payload)
        payload = _payload()
        del payload["caseId"]
        with self.assertRaises(ValueError):
            p006_tc04.evaluate(payload)

    def test_baseline_consistent_run_still_defers_firmware(self):
        result = p006_tc04.evaluate(_payload())
        self.assertEqual(CASE_ID, result["caseId"])
        self.assertEqual("consistent", result["decision"])
        self.assertNotEqual("allowed", result["decision"])
        text = " ".join(result["reasons"]).lower()
        self.assertIn("deferred", text)
        self.assertIn("blocked stream", text)
        self.assertIn("recovery", text)
        self.assertEqual(["raw-log-001"], result["preservedResults"])
        self.assertEqual([], result["rejectedClaims"])
        self.assertEqual([], result["openQuestions"])
        self.assertTrue(result["reasons"])
        self._assert_schema(result)

    def test_adversarial_passing_summary_with_failing_raw_log_is_blocked(self):
        result = p006_tc04.evaluate(
            _payload(summary_passed=True, raw_failed=True, raw_log_id="raw-critical-7")
        )
        self.assertEqual("blocked", result["decision"])
        self.assertNotEqual("allowed", result["decision"])
        self.assertEqual(["raw-critical-7"], result["preservedResults"])
        self.assertEqual(["aggregate-summary"], result["rejectedClaims"])
        self.assertEqual([], result["openQuestions"])
        self._assert_contradiction_prefers_raw(result, "raw-critical-7")
        self._assert_schema(result)

    def test_false_pass_trusting_green_summary_is_blocked(self):
        result = p006_tc04.evaluate(
            _payload(
                summary_passed=True,
                raw_failed=True,
                skipped_physical_as_pass=False,
                stale_report=False,
                raw_log_id="raw-false-pass",
            )
        )
        self.assertEqual("blocked", result["decision"])
        self.assertNotIn(result["decision"], ("allowed", "consistent", "accepted"))
        joined = " ".join(result["reasons"]).lower()
        self.assertIn("green summary", joined)
        self.assertIn("blocked", joined)
        self.assertIn("raw-false-pass", result["preservedResults"])
        self._assert_contradiction_prefers_raw(result, "raw-false-pass")

    def test_repetition_skipped_physical_counted_as_pass_is_blocked(self):
        result = p006_tc04.evaluate(
            _payload(
                summary_passed=True,
                raw_failed=False,
                skipped_physical_as_pass=True,
                stale_report=False,
                raw_log_id="raw-skip",
            )
        )
        self.assertEqual("blocked", result["decision"])
        self.assertNotEqual("allowed", result["decision"])
        self.assertEqual(["raw-skip"], result["preservedResults"])
        joined = " ".join(result["reasons"]).lower()
        self.assertIn("skipped physical", joined)
        self._assert_contradiction_prefers_raw(result, "raw-skip")

    def test_repetition_stale_report_is_blocked(self):
        result = p006_tc04.evaluate(
            _payload(
                summary_passed=True,
                raw_failed=False,
                skipped_physical_as_pass=False,
                stale_report=True,
                raw_log_id="raw-stale",
            )
        )
        self.assertEqual("blocked", result["decision"])
        self.assertNotEqual("allowed", result["decision"])
        self.assertEqual(["raw-stale"], result["preservedResults"])
        self.assertIn("stale", " ".join(result["reasons"]).lower())
        self._assert_contradiction_prefers_raw(result, "raw-stale")

    def test_repetition_all_contradiction_flags_stay_blocked(self):
        result = p006_tc04.evaluate(
            _payload(
                summary_passed=True,
                raw_failed=True,
                skipped_physical_as_pass=True,
                stale_report=True,
                raw_log_id="raw-all",
            )
        )
        self.assertEqual("blocked", result["decision"])
        self.assertNotEqual("allowed", result["decision"])
        self.assertEqual(["raw-all"], result["preservedResults"])
        joined = " ".join(result["reasons"]).lower()
        self.assertIn("raw log failed", joined)
        self.assertIn("skipped physical", joined)
        self.assertIn("stale", joined)
        self._assert_contradiction_prefers_raw(result, "raw-all")

    def test_summary_not_passed_and_raw_failed(self):
        result = p006_tc04.evaluate(
            _payload(summary_passed=False, raw_failed=True, raw_log_id="raw-fail")
        )
        self.assertEqual("failed", result["decision"])
        self.assertNotEqual("allowed", result["decision"])
        self.assertEqual(["raw-fail"], result["preservedResults"])
        self.assertEqual([], result["openQuestions"])
        self.assertTrue(result["reasons"])
        self.assertIn("deferred", " ".join(result["reasons"]).lower())
        self._assert_schema(result)

    def test_skip_or_stale_with_failing_summary_is_blocked(self):
        for skipped, stale in ((True, False), (False, True), (True, True)):
            result = p006_tc04.evaluate(
                _payload(
                    summary_passed=False,
                    raw_failed=True,
                    skipped_physical_as_pass=skipped,
                    stale_report=stale,
                    raw_log_id="raw-distorted",
                )
            )
            self.assertEqual("blocked", result["decision"])
            self.assertNotEqual("failed", result["decision"])
            self.assertEqual(["aggregate-summary"], result["rejectedClaims"])
            self.assertEqual(["raw-distorted"], result["preservedResults"])

    def test_summary_not_passed_without_raw_failure_is_not_allowed(self):
        result = p006_tc04.evaluate(
            _payload(summary_passed=False, raw_failed=False, raw_log_id="raw-hold")
        )
        self.assertEqual("failed", result["decision"])
        self.assertNotEqual("allowed", result["decision"])
        self.assertNotEqual("consistent", result["decision"])
        self.assertEqual(["raw-hold"], result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_non_bool_flags_and_bad_raw_log_id_raise(self):
        payload = _payload()
        payload["summaryPassed"] = 1
        with self.assertRaises(ValueError):
            p006_tc04.evaluate(payload)
        payload = _payload()
        payload["rawLogId"] = None
        with self.assertRaises(ValueError):
            p006_tc04.evaluate(payload)
        payload = _payload()
        payload["rawLogId"] = ""
        with self.assertRaises(ValueError):
            p006_tc04.evaluate(payload)
        payload = _payload()
        payload["rawLogId"] = "   "
        with self.assertRaises(ValueError):
            p006_tc04.evaluate(payload)
        payload = _payload()
        del payload["staleReport"]
        with self.assertRaises(ValueError):
            p006_tc04.evaluate(payload)

    def test_decisions_never_allowed_across_repetitions(self):
        matrix = []
        for summary_passed in (False, True):
            for raw_failed in (False, True):
                for skipped in (False, True):
                    for stale in (False, True):
                        result = p006_tc04.evaluate(
                            _payload(
                                summary_passed=summary_passed,
                                raw_failed=raw_failed,
                                skipped_physical_as_pass=skipped,
                                stale_report=stale,
                                raw_log_id="raw-matrix",
                            )
                        )
                        matrix.append(result["decision"])
                        self.assertNotEqual("allowed", result["decision"])
                        self.assertIn("raw-matrix", result["preservedResults"])
                        self.assertTrue(result["reasons"])
                        self.assertEqual([], result["openQuestions"])
                        self._assert_schema(result)
                        if skipped or stale or (summary_passed and raw_failed):
                            self.assertEqual("blocked", result["decision"])
                            if summary_passed:
                                self._assert_contradiction_prefers_raw(result, "raw-matrix")
                        elif (not summary_passed) and raw_failed:
                            self.assertEqual("failed", result["decision"])
                        elif summary_passed and not raw_failed and not skipped and not stale:
                            self.assertEqual("consistent", result["decision"])
        self.assertNotIn("allowed", matrix)

    def _assert_contradiction_prefers_raw(self, result, raw_log_id):
        joined = " ".join(result["reasons"]).lower()
        self.assertIn("contradiction", joined)
        self.assertIn("prefer", joined)
        self.assertIn("raw log", joined)
        self.assertIn(raw_log_id, result["preservedResults"])
        self.assertIn(raw_log_id, joined)

    def _assert_schema(self, result):
        self.assertEqual(list(_RESULT_KEYS), list(result.keys()))
        self.assertIsInstance(result["caseId"], str)
        self.assertIsInstance(result["decision"], str)
        for key in ("reasons", "rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        if result["decision"] != "allowed":
            self.assertTrue(result["reasons"])


if __name__ == "__main__":
    unittest.main()
