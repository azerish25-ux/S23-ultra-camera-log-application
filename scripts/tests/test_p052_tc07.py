"""TC-P052-07 denoise temporal leakage."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p052_tc07", Path(__file__).resolve().parents[1] / "gates" / "p052_tc07.py"
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
        "condition": "occlusion",
        "motionPreserved": True,
        "texturePreserved": True,
        "historyReduced": False,
        "averagedUnrelated": False,
        "noise": "0.2",
    }
    base.update(overrides)
    return base


class TcP05207(unittest.TestCase):
    def test_occlusion_keeps_motion_and_texture(self):
        result = evaluate(payload())
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P052-07")
        self.assertEqual(result["decision"], "gated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("condition:occlusion", result["preservedResults"])
        self.assertIn("motion:true", result["preservedResults"])
        self.assertIn("texture:true", result["preservedResults"])
        self.assertIn("noise:0.2", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_unrelated_average_keeps_noise_and_motion(self):
        result = evaluate(
            payload(condition="scene-cut", motionPreserved=False, texturePreserved=False, averagedUnrelated=True, noise="0.01")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("averaged-unrelated", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("noise:0.01", result["preservedResults"])
        self.assertIn("motion:false", result["preservedResults"])
        self.assertIn("condition:scene-cut", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "gated"})

    def test_repeat_scene_cut_drops_invalid_history(self):
        result = evaluate(payload(condition="scene-cut", motionPreserved=False, texturePreserved=False, historyReduced=True))
        self.assertEqual(result["decision"], "gated")
        self.assertIn("history-reduced:true", result["preservedResults"])
        self.assertIn("condition:scene-cut", result["preservedResults"])

    def test_repeat_low_confidence(self):
        result = evaluate(payload(condition="low-confidence", averagedUnrelated=True, noise="0.01"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("averaged-unrelated", result["rejectedClaims"])
        self.assertIn("condition:low-confidence", result["preservedResults"])
        self.assertIn("noise:0.01", result["preservedResults"])

    def test_repeat_slow_motion(self):
        result = evaluate(payload(condition="slow-motion"))
        self.assertEqual(result["decision"], "gated")
        self.assertIn("condition:slow-motion", result["preservedResults"])
        self.assertIn("texture:true", result["preservedResults"])

    def test_leak_without_history_drop(self):
        result = evaluate(payload(motionPreserved=False, texturePreserved=True, historyReduced=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("temporal-leak", result["rejectedClaims"])
        self.assertIn("motion:false", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "condition"},
            {**valid, "extra": True},
            {**valid, "condition": "pan"},
            {**valid, "motionPreserved": "true"},
            {**valid, "noise": "0.010"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
