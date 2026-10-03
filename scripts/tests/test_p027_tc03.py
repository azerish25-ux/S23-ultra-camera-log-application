"""TC-P027-03 a mean-only cadence check is rejected."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p027_tc03", Path(__file__).resolve().parents[1] / "gates" / "p027_tc03.py"
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
        "pattern": "duplicate-timestamps",
        "averageNearTarget": True,
        "meanOnlyValidator": False,
        "intervalsMs": ["16", "16", "80"],
        "timingEvidence": "trace-p027",
    }
    base.update(overrides)
    return base


class TcP02703(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P027-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("compensating short intervals", _MODULE.INTERVENTION)
        self.assertIn("original timing evidence", _MODULE.EXPECTED)
        self.assertIn("mean-only", _MODULE.NEGATIVE)
        self.assertIn("duplicate-timestamps", _MODULE.PATTERNS)
        self.assertIn("repeated-image-content", _MODULE.PATTERNS)
        self.assertIn("missing-source-frame", _MODULE.PATTERNS)

    def test_duplicate_timestamps_keep_the_original_intervals(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            ["trace-p027", "interval:16", "interval:16", "interval:80"],
        )
        self.assertTrue(any("cadence defect" in item for item in result["reasons"]))

    def test_missing_source_frame_is_a_separate_repeat(self):
        result = evaluate(
            payload(pattern="missing-source-frame", intervalsMs=["40", "40"], timingEvidence="gap-trace")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertEqual(result["preservedResults"], ["gap-trace", "interval:40", "interval:40"])
        self.assertTrue(any("missing-source-frame" in item for item in result["reasons"]))

    def test_mean_only_validator_is_killed_and_intervals_remain(self):
        result = evaluate(
            payload(
                pattern="long-and-short-intervals",
                meanOnlyValidator=True,
                intervalsMs=["200", "10", "10"],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "cadence_defect"})
        self.assertEqual(result["rejectedClaims"], ["mean-only-validator"])
        self.assertIn("trace-p027", result["preservedResults"])
        self.assertIn("interval:200", result["preservedResults"])
        self.assertIn("interval:10", result["preservedResults"])

    def test_repeated_image_content_mean_only_is_also_rejected(self):
        result = evaluate(payload(pattern="repeated-image-content", meanOnlyValidator=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("interval:80", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "pattern": "average"},
            {**valid, "intervalsMs": []},
            {**valid, "intervalsMs": ["0"]},
            {**valid, "intervalsMs": [16]},
            {**valid, "timingEvidence": "Trace"},
            {**valid, "meanOnlyValidator": "true"},
            {k: v for k, v in valid.items() if k != "pattern"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
