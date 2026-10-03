"""TC-P056-07 temporal denoise must not average unrelated frames."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p056_tc07", Path(__file__).resolve().parents[1] / "gates" / "p056_tc07.py"
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
        "motion": "slow-motion",
        "averagedUnrelated": False,
        "historyInvalid": False,
        "texturePreserved": True,
        "motionPreserved": True,
        "relianceReduced": False,
    }
    base.update(overrides)
    return base


class TcP05607(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P056-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_slow_motion_keeps_texture(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "motion-kept")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("motion:slow-motion", result["preservedResults"])
        self.assertIn("texture:true", result["preservedResults"])

    def test_occlusion_drops_invalid_history(self):
        result = evaluate(
            payload(motion="occlusion", historyInvalid=True, relianceReduced=True)
        )
        self.assertEqual(result["decision"], "history-limited")
        self.assertIn("motion:occlusion", result["preservedResults"])
        self.assertIn("history-invalid:true", result["preservedResults"])

    def test_scene_cut_with_unrelated_average_fails(self):
        result = evaluate(payload(motion="scene-cut", averagedUnrelated=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unrelated-frame-average"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("motion:scene-cut", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "motion-kept"})

    def test_low_confidence_without_reduced_reliance_fails(self):
        result = evaluate(payload(motion="low-confidence", historyInvalid=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("invalid-history", result["rejectedClaims"])
        self.assertIn("motion:low-confidence", result["preservedResults"])

    def test_lost_texture_fails_and_stays_in_the_inventory(self):
        result = evaluate(payload(texturePreserved=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["texture-or-motion-lost"])
        self.assertIn("texture:false", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "motion": "pan"},
            {**valid, "averagedUnrelated": "no"},
            {**valid, "relianceReduced": 1},
            {k: v for k, v in valid.items() if k != "motion"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
