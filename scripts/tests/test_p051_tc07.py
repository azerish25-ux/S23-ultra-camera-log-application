"""TC-P051-07 temporal denoise must not average unrelated frames."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p051_tc07", Path(__file__).resolve().parents[1] / "gates" / "p051_tc07.py"
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
        "condition": "slow-motion",
        "history": "valid",
        "texture": "weave-17",
        "motion": "right-2",
        "noiseScore": 4,
    }
    base.update(overrides)
    return base


class TcP05107(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P051-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants(self):
        self.assertIn("temporal noise", _MODULE.INTERVENTION)
        self.assertIn("invalid history", _MODULE.EXPECTED)
        self.assertIn("unrelated frames", _MODULE.NEGATIVE)

    def test_valid_history_preserves_motion_and_texture(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "motion_preserved")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("texture:weave-17", result["preservedResults"])
        self.assertIn("motion:right-2", result["preservedResults"])
        self.assertIn("condition:slow-motion", result["preservedResults"])

    def test_repeat_occlusion_and_scene_cut_reduce_invalid_history(self):
        for condition in ("occlusion", "scene-cut"):
            result = evaluate(payload(condition=condition, history="invalid"))
            self.assertEqual(result["decision"], "history_reduced")
            self.assertIn(f"condition:{condition}", result["preservedResults"])
            self.assertIn("texture:weave-17", result["preservedResults"])
            self.assertIn("motion:right-2", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_low_confidence(self):
        result = evaluate(payload(condition="low-confidence", history="invalid", noiseScore=0))
        self.assertEqual(result["decision"], "history_reduced")
        self.assertIn("condition:low-confidence", result["preservedResults"])
        self.assertIn("noise:0", result["preservedResults"])
        self.assertIn("texture:weave-17", result["preservedResults"])

    def test_unrelated_average_fails_even_with_low_noise(self):
        for condition in ("occlusion", "slow-motion"):
            result = evaluate(payload(condition=condition, history="unrelated", noiseScore=0))
            self.assertContract(result)
            self.assertEqual(result["decision"], "rejected")
            self.assertEqual(result["rejectedClaims"], ["unrelated-frame-average"])
            self.assertIn(_MODULE.NEGATIVE, result["reasons"])
            self.assertIn("texture:weave-17", result["preservedResults"])
            self.assertIn("motion:right-2", result["preservedResults"])
            self.assertIn("noise:0", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed", "motion_preserved"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "condition": "pan"},
            {**valid, "history": "maybe"},
            {**valid, "texture": "two words"},
            {**valid, "noiseScore": -1},
            {k: v for k, v in valid.items() if k != "motion"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
