"""TC-P051-06 a moving highlight is not a sensor defect."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p051_tc06", Path(__file__).resolve().parents[1] / "gates" / "p051_tc06.py"
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


def frame(ident, feature_x, feature_value=3800):
    return {
        "id": ident,
        "defectX": 1,
        "defectY": 1,
        "defectValue": 50,
        "featureX": feature_x,
        "featureY": 4,
        "featureValue": feature_value,
    }


def payload(**overrides):
    base = {
        "frames": [frame("f0", 3), frame("f1", 4), frame("f2", 5)],
        "policy": "defect-only",
        "nearSaturation": False,
    }
    base.update(overrides)
    return base


class TcP05106(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P051-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants(self):
        self.assertIn("moving bright feature", _MODULE.INTERVENTION)
        self.assertIn("supported defect", _MODULE.EXPECTED)
        self.assertIn("isolated bright pixel", _MODULE.NEGATIVE)

    def test_repeat_several_frames_keep_the_moving_feature(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "feature_preserved")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("feature:f0:3,4:3800", result["preservedResults"])
        self.assertIn("feature:f1:4,4:3800", result["preservedResults"])
        self.assertIn("feature:f2:5,4:3800", result["preservedResults"])
        self.assertIn("defect:f0:1,1", result["preservedResults"])
        self.assertIn("corrected:f0", result["preservedResults"])
        self.assertIn("corrected:f2", result["preservedResults"])

    def test_repeat_near_saturated_boundary(self):
        result = evaluate(
            payload(
                frames=[frame("f0", 6, 4000)],
                nearSaturation=True,
            )
        )
        self.assertEqual(result["decision"], "feature_preserved")
        self.assertIn("feature:f0:6,4:4000", result["preservedResults"])
        self.assertIn("saturated-boundary", result["preservedResults"])
        self.assertIn("corrected:f0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_removing_every_isolated_bright_pixel_fails(self):
        result = evaluate(payload(policy="remove-isolated-bright", nearSaturation=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["remove-every-isolated-bright"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("feature:f0:3,4:3800", result["preservedResults"])
        self.assertIn("feature:f2:5,4:3800", result["preservedResults"])
        self.assertIn("defect:f1:1,1", result["preservedResults"])
        self.assertIn("saturated-boundary", result["preservedResults"])
        self.assertFalse(any(item.startswith("corrected:") for item in result["preservedResults"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed", "feature_preserved"})

    def test_invalid_payload_raises(self):
        valid = payload()
        still = [frame("f0", 3), frame("f1", 3)]
        cases = [
            None,
            {},
            {**valid, "policy": "smear"},
            {**valid, "frames": still},
            {**valid, "nearSaturation": "yes"},
            {**valid, "frames": []},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
