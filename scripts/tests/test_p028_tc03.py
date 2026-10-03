"""TC-P028-03 a mean near the target does not hide a source gap."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p028_tc03", Path(__file__).resolve().parents[1] / "gates" / "p028_tc03.py"
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


def payload(**overrides):
    base = {
        "targetIntervalNs": 100,
        "intervalsNs": [250, 49, 51, 50],
        "duplicateTimestamp": False,
        "repeatedImageContent": False,
        "missingSourceFrame": False,
        "validator": "interval",
    }
    base.update(overrides)
    return base


class TcP02803(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P028-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("compensating short intervals", _MODULE.INTERVENTION)
        self.assertIn("original timing evidence", _MODULE.EXPECTED)
        self.assertIn("mean-only", _MODULE.NEGATIVE)

    def test_concealed_gap_reports_the_cadence_defect(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertIn("long-interval", result["rejectedClaims"])
        self.assertIn("short-interval", result["rejectedClaims"])
        self.assertIn("interval:250", result["preservedResults"])
        self.assertIn("interval:49", result["preservedResults"])
        self.assertIn("target:100", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_mean_only_validator_is_killed_on_the_concealed_gap(self):
        result = evaluate(payload(validator="mean_only"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "cadence_defect"})
        self.assertIn("mean-only-validator", result["rejectedClaims"])
        self.assertIn("source-cadence-defect", result["rejectedClaims"])
        self.assertIn("interval:250", result["preservedResults"])
        self.assertIn("interval:50", result["preservedResults"])

    def test_duplicate_timestamps_are_a_defect(self):
        result = evaluate(
            payload(intervalsNs=[100, 100, 100], duplicateTimestamp=True)
        )
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertIn("duplicate-timestamp", result["rejectedClaims"])
        self.assertIn("duplicate-timestamp", result["preservedResults"])
        self.assertIn("interval:100", result["preservedResults"])

    def test_repeated_image_content_is_a_defect(self):
        result = evaluate(
            payload(intervalsNs=[100, 100, 100], repeatedImageContent=True)
        )
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertIn("repeated-image-content", result["rejectedClaims"])
        self.assertIn("repeated-image-content", result["preservedResults"])

    def test_one_missing_source_frame_is_a_defect(self):
        result = evaluate(
            payload(intervalsNs=[100, 100, 100], missingSourceFrame=True)
        )
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertIn("missing-source-frame", result["rejectedClaims"])
        self.assertIn("missing-source-frame", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_uniform_intervals_are_retained_without_a_cadence_certificate(self):
        result = evaluate(payload(intervalsNs=[100, 100, 100, 100]))
        self.assertEqual(result["decision"], "intervals_retained")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("interval:100", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "intervalsNs": [100]},
            {**valid, "validator": "average"},
            {**valid, "targetIntervalNs": 0},
            {**valid, "duplicateTimestamp": "yes"},
            {k: v for k, v in valid.items() if k != "validator"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
