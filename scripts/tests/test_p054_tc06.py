"""TC-P054-06 defect versus real highlight."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p054_tc06", Path(__file__).resolve().parents[1] / "gates" / "p054_tc06.py"
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
        "defectId": "hot-12",
        "featureId": "point-light",
        "frameCount": "4",
        "defectPersistent": True,
        "featureMoving": True,
        "nearSaturation": False,
        "featureCode": "1.4",
        "removeAllIsolated": False,
    }
    base.update(overrides)
    return base


class TcP05406(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P054-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn("real-feature:preserved", result["preservedResults"])

    def test_persistent_moving_feature_is_defect_only(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "defect-only")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("hot-12", result["preservedResults"])
        self.assertIn("point-light", result["preservedResults"])
        self.assertIn("feature-code:1.4", result["preservedResults"])
        self.assertIn("frames:4", result["preservedResults"])

    def test_negative_removing_every_isolated_bright_pixel_fails(self):
        result = evaluate(payload(removeAllIsolated=True, featureCode="2"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["every-isolated-bright-pixel"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("point-light", result["preservedResults"])
        self.assertIn("feature-code:2", result["preservedResults"])
        self.assertIn("real-feature:preserved", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "defect-only"})

    def test_repeat_several_frames_preserve_the_real_feature(self):
        result = evaluate(payload(frameCount="6", featureId="speck", featureCode="1.1"))
        self.assertEqual(result["decision"], "defect-only")
        self.assertIn("frames:6", result["preservedResults"])
        self.assertIn("speck", result["preservedResults"])
        self.assertIn("feature-code:1.1", result["preservedResults"])
        self.assertIn("real-feature:preserved", result["preservedResults"])

    def test_repeat_near_saturated_boundary_preserves_feature(self):
        result = evaluate(payload(nearSaturation=True, featureCode="0.98", frameCount="5"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "defect-only")
        self.assertIn("near-saturation:yes", result["preservedResults"])
        self.assertIn("feature-code:0.98", result["preservedResults"])
        self.assertIn("point-light", result["preservedResults"])
        self.assertTrue(any("near saturation" in item for item in result["openQuestions"]))

    def test_non_persistent_defect_is_withheld(self):
        result = evaluate(payload(defectPersistent=False, featureId="lamp"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("lamp", result["preservedResults"])
        self.assertIn("real-feature:preserved", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "defectId"},
            {**valid, "extra": True},
            {**valid, "frameCount": "0"},
            {**valid, "frameCount": "04"},
            {**valid, "featureCode": "1.40"},
            {**valid, "defectPersistent": "true"},
            {**valid, "featureId": ""},
            {**valid, "nearSaturation": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
