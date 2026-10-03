"""TC-P050-07 temporal denoise must not average unrelated frames."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p050_tc07", Path(__file__).resolve().parents[1] / "gates" / "p050_tc07.py"
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
        "condition": "slow_motion",
        "averageUnrelated": False,
        "texture": True,
        "motion": True,
    }
    base.update(overrides)
    return base


class TcP05007(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P050-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("texture:true", result["preservedResults"])

    def test_constants(self):
        self.assertIn("temporal noise reduction", _MODULE.INTERVENTION)
        self.assertIn("invalid history", _MODULE.EXPECTED)
        self.assertIn("unrelated frames", _MODULE.NEGATIVE)

    def test_repeat_occlusion_scene_cut_and_low_confidence(self):
        for condition in ("occlusion", "scene_cut", "low_confidence"):
            result = evaluate(payload(condition=condition))
            self.assertContract(result)
            self.assertEqual(result["decision"], "history_reduced")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(f"condition:{condition}", result["preservedResults"])
            self.assertIn("motion:true", result["preservedResults"])
            self.assertTrue(any("invalid history reduced" in item for item in result["reasons"]))

    def test_repeat_slow_motion_keeps_texture(self):
        result = evaluate(payload(condition="slow_motion"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "motion_kept")
        self.assertIn("condition:slow_motion", result["preservedResults"])
        self.assertTrue(any("slow motion kept texture" in item for item in result["reasons"]))

    def test_unrelated_frame_average_fails(self):
        for condition in ("occlusion", "slow_motion"):
            result = evaluate(payload(condition=condition, averageUnrelated=True))
            self.assertEqual(result["decision"], "rejected")
            self.assertNotIn(result["decision"], {"qualified", "allowed", "motion_kept"})
            self.assertEqual(result["rejectedClaims"], ["unrelated-frame-average"])
            self.assertIn(_MODULE.NEGATIVE, result["reasons"])
            self.assertIn(f"condition:{condition}", result["preservedResults"])
            self.assertIn("texture:true", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "condition": "pan"},
            {**valid, "texture": 1},
            {k: v for k, v in valid.items() if k != "motion"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
