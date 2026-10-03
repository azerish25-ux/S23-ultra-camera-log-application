"""TC-P055-07 denoise temporal leakage."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p055_tc07", Path(__file__).resolve().parents[1] / "gates" / "p055_tc07.py"
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
        "subjectId": "cloth",
        "textureId": "weave-4",
        "motion": "textured",
        "historyValid": True,
        "averageUnrelated": False,
        "noiseScore": "0.02",
    }
    base.update(overrides)
    return base


class TcP05507(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P055-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Averaging unrelated frames to obtain low noise must fail.",
        )
        self.assertIn("temporal noise reduction", _MODULE.INTERVENTION)

    def test_valid_history_preserves_motion(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "motion_preserved")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("motion:textured", result["preservedResults"])
        self.assertIn("texture:weave-4", result["preservedResults"])
        self.assertIn("noise:0.02", result["preservedResults"])

    def test_negative_unrelated_average_fails(self):
        result = evaluate(payload(averageUnrelated=True, noiseScore="0.001", motion="slow-motion"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unrelated-frame-average"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("motion:slow-motion", result["preservedResults"])
        self.assertIn("texture:weave-4", result["preservedResults"])
        self.assertIn("noise:0.001", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "motion_preserved"})

    def test_repeat_occlusion_reduces_invalid_history(self):
        result = evaluate(payload(motion="occlusion", historyValid=False))
        self.assertEqual(result["decision"], "history_reduced")
        self.assertIn("motion:occlusion", result["preservedResults"])
        self.assertIn("texture:weave-4", result["preservedResults"])

    def test_repeat_scene_cut(self):
        result = evaluate(payload(motion="scene-cut", historyValid=False, subjectId="cut-a"))
        self.assertEqual(result["decision"], "history_reduced")
        self.assertIn("motion:scene-cut", result["preservedResults"])
        self.assertIn("subject:cut-a", result["preservedResults"])

    def test_repeat_low_confidence_and_slow_motion(self):
        low = evaluate(payload(motion="low-confidence", historyValid=False))
        slow = evaluate(payload(motion="slow-motion", historyValid=True))
        self.assertEqual(low["decision"], "history_reduced")
        self.assertIn("motion:low-confidence", low["preservedResults"])
        self.assertEqual(slow["decision"], "motion_preserved")
        self.assertIn("motion:slow-motion", slow["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "motion": "pan"},
            {**valid, "noiseScore": "0.020"},
            {**valid, "averageUnrelated": 0},
            {**valid, "subjectId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
