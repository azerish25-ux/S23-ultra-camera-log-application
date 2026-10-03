"""TC-P054-07 denoise temporal leakage."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p054_tc07", Path(__file__).resolve().parents[1] / "gates" / "p054_tc07.py"
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
        "motion": "textured-pass",
        "historyValid": True,
        "textureRetention": "0.91",
        "motionTrail": "0.01",
        "qualityGate": "0.02",
        "averagedUnrelated": False,
    }
    base.update(overrides)
    return base


class TcP05407(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P054-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_negative_unrelated_frame_average_fails(self):
        result = evaluate(
            payload(motion="textured-pass", averagedUnrelated=True, textureRetention="0.4", motionTrail="0.3")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unrelated-frame-average"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("texture:0.4", result["preservedResults"])
        self.assertIn("trail:0.3", result["preservedResults"])
        self.assertIn("textured-pass", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "motion-preserved"})

    def test_repeat_occlusion_reduces_history(self):
        result = evaluate(
            payload(motion="occlusion", historyValid=False, textureRetention="0.91", motionTrail="0")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "history-reduced")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("occlusion", result["preservedResults"])
        self.assertIn("history:invalid", result["preservedResults"])
        self.assertIn("texture:0.91", result["preservedResults"])

    def test_repeat_scene_cut_reduces_history(self):
        result = evaluate(payload(motion="scene-cut", historyValid=False, motionTrail="0.01"))
        self.assertEqual(result["decision"], "history-reduced")
        self.assertIn("scene-cut", result["preservedResults"])
        self.assertIn("trail:0.01", result["preservedResults"])
        self.assertIn("gate:0.02", result["preservedResults"])

    def test_repeat_low_confidence_reduces_history(self):
        result = evaluate(payload(motion="low-confidence", historyValid=False, textureRetention="0.88"))
        self.assertEqual(result["decision"], "history-reduced")
        self.assertIn("low-confidence", result["preservedResults"])
        self.assertIn("texture:0.88", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_slow_motion_preserves_texture(self):
        result = evaluate(
            payload(motion="slow-motion", historyValid=True, textureRetention="0.93", motionTrail="0.01")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "motion-preserved")
        self.assertIn("slow-motion", result["preservedResults"])
        self.assertIn("texture:0.93", result["preservedResults"])
        self.assertIn("history:valid", result["preservedResults"])

    def test_trail_beyond_the_gate_is_temporal_leakage(self):
        result = evaluate(payload(motion="slow-motion", motionTrail="0.2", textureRetention="0.9"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("temporal-leakage", result["rejectedClaims"])
        self.assertIn("trail:0.2", result["preservedResults"])
        self.assertIn("slow-motion", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "motion-preserved"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "motion"},
            {**valid, "extra": True},
            {**valid, "motion": "pan"},
            {**valid, "textureRetention": "0.910"},
            {**valid, "qualityGate": "0"},
            {**valid, "historyValid": "false"},
            {**valid, "averagedUnrelated": 0},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
