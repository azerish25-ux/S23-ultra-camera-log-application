"""TC-P026-03 a near-target mean does not hide a cadence gap."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p026_tc03", Path(__file__).resolve().parents[1] / "gates" / "p026_tc03.py"
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
        "defect": "compensated_gap",
        "targetFps": "30",
        "averageFps": "29.97",
        "meanOnly": False,
        "timestamps": ["0", "100", "120", "140"],
        "sourceId": "video-timestamps",
    }
    base.update(overrides)
    return base


class TcP02603(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P026-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("compensating short intervals", _MODULE.INTERVENTION)
        self.assertIn("cadence defect", _MODULE.EXPECTED)
        self.assertIn("mean-only", _MODULE.NEGATIVE)
        self.assertIn("duplicate_timestamps", _MODULE.DEFECTS)
        self.assertIn("missing_source_frame", _MODULE.DEFECTS)

    def test_compensated_gap_keeps_the_original_timestamps(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertEqual(result["rejectedClaims"], ["compensated_gap"])
        self.assertEqual(
            result["preservedResults"],
            ["t:0", "t:100", "t:120", "t:140", "video-timestamps"],
        )

    def test_mean_only_validator_is_rejected_and_keeps_the_evidence(self):
        result = evaluate(payload(meanOnly=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "cadence_observed"})
        self.assertEqual(result["rejectedClaims"], ["mean-only-validator", "compensated_gap"])
        self.assertIn("t:100", result["preservedResults"])
        self.assertIn("video-timestamps", result["preservedResults"])

    def test_duplicate_timestamps_are_a_separate_defect(self):
        result = evaluate(payload(defect="duplicate_timestamps", timestamps=["10", "10", "43"]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertEqual(result["rejectedClaims"], ["duplicate_timestamps"])
        self.assertIn("t:10", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_missing_source_frame_preserves_timing_evidence(self):
        result = evaluate(
            payload(defect="missing_source_frame", timestamps=["0", "66"], sourceId="frame-2-absent")
        )
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertEqual(result["rejectedClaims"], ["missing_source_frame"])
        self.assertEqual(result["preservedResults"], ["t:0", "t:66", "frame-2-absent"])

    def test_repeated_image_content_is_reported(self):
        result = evaluate(payload(defect="repeated_image_content"))
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertIn("repeated_image_content", result["rejectedClaims"])
        self.assertIn("video-timestamps", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "defect": "jitter"},
            {**valid, "timestamps": ["0"]},
            {**valid, "averageFps": "30.0"},
            {k: v for k, v in valid.items() if k != "sourceId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
