"""TC-P049-07 unrelated temporal averages do not buy low noise."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p049_tc07", Path(__file__).resolve().parents[1] / "gates" / "p049_tc07.py"
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
        "motion": True,
        "texture": True,
        "averageUnrelated": False,
    }
    base.update(overrides)
    return base


class TcP04907(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P049-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("motion:true", result["preservedResults"])
        self.assertIn("texture:true", result["preservedResults"])

    def test_constants(self):
        self.assertIn("temporal noise", _MODULE.INTERVENTION)
        self.assertIn("invalid history", _MODULE.EXPECTED)
        self.assertIn("unrelated frames", _MODULE.NEGATIVE)

    def test_occlusion_reduces_history_and_keeps_texture(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "history_reduced")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("condition:occlusion", result["preservedResults"])

    def test_scene_cut_reduces_history(self):
        result = evaluate(payload(condition="scene-cut"))
        self.assertEqual(result["decision"], "history_reduced")
        self.assertIn("condition:scene-cut", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_low_confidence_and_slow_motion_are_distinct(self):
        low = evaluate(payload(condition="low-confidence"))
        slow = evaluate(payload(condition="slow-motion"))
        self.assertEqual(low["decision"], "history_reduced")
        self.assertEqual(slow["decision"], "texture_preserved")
        self.assertIn("condition:slow-motion", slow["preservedResults"])
        self.assertIn("texture:true", slow["preservedResults"])

    def test_unrelated_average_fails_and_keeps_motion(self):
        result = evaluate(payload(condition="steady", averageUnrelated=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unrelated-frame-average"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("motion:true", result["preservedResults"])
        self.assertIn("texture:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "texture_preserved"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "condition": "cut"},
            {**valid, "motion": "yes"},
            {**valid, "averageUnrelated": 1},
            {k: v for k, v in valid.items() if k != "texture"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
