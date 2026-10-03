"""TC-P008-04 contradictory outcomes: summary, raw log, skip, and stale report."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gates.p008_tc04 import evaluate

KEYS = {"caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"}


def payload(**overrides) -> dict:
    body = {
        "summaryPassed": False,
        "rawFailed": False,
        "skippedPhysicalAsPass": False,
        "staleReport": False,
        "rawLogId": "raw-log-9",
        "remoteCommit": "remote-sha",
        "localBuildSucceeded": False,
    }
    body.update(overrides)
    return body


class ContradictoryOutcomeGate(unittest.TestCase):
    def assert_contract(self, result: dict) -> None:
        self.assertEqual(set(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P008-04")
        self.assertIsInstance(result["reasons"], list)
        self.assertIsInstance(result["rejectedClaims"], list)
        self.assertIsInstance(result["preservedResults"], list)
        self.assertIsInstance(result["openQuestions"], list)
        self.assertNotIn(result["decision"], {"complete", "allowed"})
        if result["decision"] != "allowed":
            self.assertTrue(result["reasons"])
            self.assertTrue(all(isinstance(reason, str) and reason for reason in result["reasons"]))

    def test_summary_and_raw_failure_is_blocked(self) -> None:
        for build in (False, True):
            with self.subTest(localBuildSucceeded=build):
                result = evaluate(payload(summaryPassed=True, rawFailed=True, localBuildSucceeded=build))
                self.assert_contract(result)
                self.assertEqual(result["decision"], "blocked")
                self.assertIn("summary", result["rejectedClaims"])
                self.assertEqual(result["preservedResults"], ["raw-log-9", "remote-sha"])
                self.assertNotIn(result["decision"], {"complete", "allowed"})

    def test_skipped_physical_counted_as_pass_is_blocked(self) -> None:
        result = evaluate(payload(summaryPassed=True, skippedPhysicalAsPass=True, localBuildSucceeded=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "blocked")
        self.assertEqual(result["openQuestions"], ["physical device gate pending"])
        self.assertIn("raw-log-9", result["preservedResults"])
        self.assertIn("remote-sha", result["preservedResults"])
        self.assertNotIn(result["decision"], {"complete", "allowed", "consistent"})

    def test_stale_report_with_green_summary_is_blocked(self) -> None:
        result = evaluate(payload(summaryPassed=True, staleReport=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "blocked")
        self.assertIn("summary", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["raw-log-9", "remote-sha"])
        self.assertEqual(result["openQuestions"], [])

    def test_every_contradiction_source_blocks_even_when_the_build_passed(self) -> None:
        result = evaluate(payload(
            summaryPassed=True,
            rawFailed=True,
            skippedPhysicalAsPass=True,
            staleReport=True,
            localBuildSucceeded=True,
            rawLogId="log-a",
            remoteCommit="commit-b",
        ))
        self.assertEqual(result["decision"], "blocked")
        self.assertEqual(result["preservedResults"], ["log-a", "commit-b"])
        self.assertEqual(result["rejectedClaims"], ["summary"])
        self.assertNotIn(result["decision"], {"complete", "allowed"})
        self.assertTrue(any("green summary" in reason for reason in result["reasons"]))
        self.assertTrue(any("local build" in reason for reason in result["reasons"]))

    def test_raw_failure_without_green_summary_is_failed(self) -> None:
        result = evaluate(payload(summaryPassed=False, rawFailed=True, localBuildSucceeded=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "failed")
        self.assertNotEqual(result["decision"], "complete")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["raw-log-9", "remote-sha"])

    def test_no_contradiction_and_no_raw_failure_is_consistent_not_complete(self) -> None:
        for build in (False, True):
            with self.subTest(localBuildSucceeded=build):
                result = evaluate(payload(summaryPassed=True, localBuildSucceeded=build))
                self.assert_contract(result)
                self.assertEqual(result["decision"], "consistent")
                self.assertNotEqual(result["decision"], "complete")
                self.assertNotEqual(result["decision"], "allowed")
                self.assertEqual(result["preservedResults"], ["raw-log-9", "remote-sha"])
                self.assertEqual(result["rejectedClaims"], [])

    def test_negative_summary_without_raw_failure_is_consistent(self) -> None:
        result = evaluate(payload(summaryPassed=False, rawFailed=False, skippedPhysicalAsPass=True, staleReport=True))
        self.assertEqual(result["decision"], "consistent")
        self.assertNotIn(result["decision"], {"blocked", "complete", "allowed"})
        self.assertIn("remote-sha", result["preservedResults"])
        self.assertIn("raw-log-9", result["preservedResults"])

    def test_trusting_green_summary_without_the_failure_is_blocked(self) -> None:
        hidden = evaluate(payload(summaryPassed=True, rawFailed=False))
        caught = evaluate(payload(summaryPassed=True, rawFailed=True))
        self.assertEqual(hidden["decision"], "consistent")
        self.assertEqual(caught["decision"], "blocked")
        self.assertNotEqual(caught["decision"], hidden["decision"])
        self.assertIn("raw-log-9", caught["preservedResults"])

    def test_invalid_payloads_raise(self) -> None:
        with self.assertRaises(ValueError):
            evaluate("nope")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            evaluate(payload(summaryPassed=1))
        with self.assertRaises(ValueError):
            evaluate(payload(rawFailed="yes"))
        with self.assertRaises(ValueError):
            evaluate(payload(rawLogId=""))
        with self.assertRaises(ValueError):
            evaluate(payload(remoteCommit=None))
        incomplete = payload()
        del incomplete["staleReport"]
        with self.assertRaises(ValueError):
            evaluate(incomplete)
        with self.assertRaises(ValueError):
            evaluate(payload(localBuildSucceeded="true"))

    def test_payload_is_not_mutated(self) -> None:
        body = payload(summaryPassed=True, rawFailed=True, localBuildSucceeded=True)
        snapshot = repr(body)
        evaluate(body)
        self.assertEqual(repr(body), snapshot)


if __name__ == "__main__":
    unittest.main()
