"""TC-P053-07 denoise temporal leakage."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p053_tc07", Path(__file__).resolve().parents[1] / "gates" / "p053_tc07.py"
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
        "event": "occlusion",
        "regionId": "region-a",
        "averagedUnrelated": False,
        "historyValid": True,
        "textureRetained": True,
        "motionRetained": True,
    }
    base.update(overrides)
    return base


class TcP05307(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P053-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_occlusion_preserves_motion_and_texture(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "motion_preserved")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("event:occlusion", result["preservedResults"])
        self.assertIn("texture:true", result["preservedResults"])
        self.assertIn("motion:true", result["preservedResults"])
        self.assertIn("region:region-a", result["preservedResults"])

    def test_scene_cut_and_low_confidence_reduce_invalid_history(self):
        cut = evaluate(payload(event="scene-cut", historyValid=False))
        low = evaluate(payload(event="low-confidence", historyValid=False, regionId="region-b"))
        self.assertEqual(cut["decision"], "history_reduced")
        self.assertEqual(low["decision"], "history_reduced")
        self.assertIn("event:scene-cut", cut["preservedResults"])
        self.assertIn("history-valid:false", cut["preservedResults"])
        self.assertIn("event:low-confidence", low["preservedResults"])
        self.assertIn("texture:true", low["preservedResults"])
        self.assertNotIn(cut["decision"], {"qualified", "allowed"})

    def test_slow_motion_keeps_texture_when_history_is_valid(self):
        result = evaluate(payload(event="slow-motion", regionId="region-slow"))
        self.assertEqual(result["decision"], "motion_preserved")
        self.assertIn("event:slow-motion", result["preservedResults"])
        self.assertIn("region:region-slow", result["preservedResults"])

    def test_averaging_unrelated_frames_fails(self):
        result = evaluate(payload(event="scene-cut", averagedUnrelated=True, historyValid=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unrelated-frame-average"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("event:scene-cut", result["preservedResults"])
        self.assertIn("texture:true", result["preservedResults"])
        self.assertIn("motion:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "motion_preserved"})

    def test_lost_texture_or_motion_is_rejected(self):
        result = evaluate(payload(event="occlusion", textureRetained=False, motionRetained=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["texture-lost", "motion-lost"])
        self.assertIn("texture:false", result["preservedResults"])
        self.assertIn("motion:false", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "event": "pan"},
            {**valid, "regionId": ""},
            {**valid, "historyValid": "no"},
            {**valid, "averagedUnrelated": 0},
            {key: value for key, value in valid.items() if key != "event"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
