"""TC-P032-03 gap concealed by average rate."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p032_tc03", Path(__file__).resolve().parents[1] / "gates" / "p032_tc03.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_GAP = [80000000, 5000000, 5000000]


def payload(**overrides):
    base = {
        "targetIntervalNs": 30000000,
        "intervalsNs": list(_GAP),
        "duplicateTimestamp": False,
        "repeatedImageContent": False,
        "missingSourceFrame": False,
        "validator": "interval",
    }
    base.update(overrides)
    return base


class TcP03203(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P032-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def assert_intervals_kept(self, result, intervals):
        for item in intervals:
            self.assertIn(f"interval:{item}", result["preservedResults"])
        self.assertIn("target:30000000", result["preservedResults"])

    def test_mean_only_validator_is_killed_when_the_average_matches(self):
        source = payload(validator="mean_only")
        result = evaluate(source)
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("mean-only-validator", result["rejectedClaims"])
        self.assertIn("source-cadence-defect", result["rejectedClaims"])
        self.assert_intervals_kept(result, _GAP)
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertGreater(len(result["preservedResults"]), 1)

    def test_interval_validator_reports_the_concealed_gap(self):
        result = evaluate(payload(validator="interval"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertIn("source-cadence-defect", result["rejectedClaims"])
        self.assertIn("long-interval", result["rejectedClaims"])
        self.assertIn("short-interval", result["rejectedClaims"])
        self.assert_intervals_kept(result, _GAP)
        self.assertNotEqual(result["preservedResults"], ["target:30000000"])

    def test_duplicate_timestamps_are_a_cadence_defect(self):
        intervals = [30000000, 30000000]
        result = evaluate(
            payload(intervalsNs=intervals, duplicateTimestamp=True, validator="interval")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertIn("duplicate-timestamp", result["rejectedClaims"])
        self.assertIn("duplicate-timestamp", result["preservedResults"])
        self.assert_intervals_kept(result, intervals)

    def test_repeated_image_content_is_preserved(self):
        intervals = [30000000, 30000000, 30000000]
        result = evaluate(
            payload(intervalsNs=intervals, repeatedImageContent=True, validator="interval")
        )
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("repeated-image-content", result["preservedResults"])
        self.assertIn("repeated-image-content", result["rejectedClaims"])
        self.assert_intervals_kept(result, intervals)

    def test_one_missing_source_frame_is_preserved(self):
        intervals = [30000000, 30000000]
        result = evaluate(
            payload(intervalsNs=intervals, missingSourceFrame=True, validator="interval")
        )
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertIn("missing-source-frame", result["preservedResults"])
        self.assertIn("missing-source-frame", result["rejectedClaims"])
        self.assert_intervals_kept(result, intervals)

    def test_uniform_intervals_are_not_a_fixed_cadence_certificate(self):
        result = evaluate(payload(intervalsNs=[30000000, 30000000], validator="interval"))
        self.assertEqual(result["decision"], "intervals_retained")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("interval:30000000", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["host intervals do not certify fixed cadence"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "intervalsNs": [30000000]},
            {**valid, "intervalsNs": [30000000, True]},
            {**valid, "targetIntervalNs": 0},
            {**valid, "validator": "average"},
            {**valid, "duplicateTimestamp": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
