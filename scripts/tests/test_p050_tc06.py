"""TC-P050-06 a moving highlight is not removed with the defect."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p050_tc06", Path(__file__).resolve().parents[1] / "gates" / "p050_tc06.py"
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
        "frameCount": 3,
        "defectX": 4,
        "defectY": 5,
        "featureX": 8,
        "featureY": 5,
        "featureMoving": True,
        "saturated": False,
        "removeAllIsolated": False,
    }
    base.update(overrides)
    return base


class TcP05006(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P050-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("defect:4,5", result["preservedResults"])
        self.assertIn("feature:8,5", result["preservedResults"])

    def test_constants(self):
        self.assertIn("persistent sensor defect", _MODULE.INTERVENTION)
        self.assertIn("preserve the real scene feature", _MODULE.EXPECTED)
        self.assertIn("isolated bright pixel", _MODULE.NEGATIVE)

    def test_repeat_over_several_frames(self):
        result = evaluate(payload(frameCount=6))
        self.assertContract(result)
        self.assertEqual(result["decision"], "defect_only")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("frames:6", result["preservedResults"])
        self.assertTrue(any("moving bright feature preserved" in item for item in result["reasons"]))

    def test_repeat_near_saturated_boundary(self):
        result = evaluate(payload(saturated=True, frameCount=4))
        self.assertContract(result)
        self.assertEqual(result["decision"], "defect_only")
        self.assertIn("saturated:true", result["preservedResults"])
        self.assertTrue(any("saturated boundary" in item for item in result["reasons"]))
        self.assertIn("feature:8,5", result["preservedResults"])

    def test_removing_every_isolated_bright_pixel_fails(self):
        result = evaluate(payload(removeAllIsolated=True, saturated=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "defect_only"})
        self.assertEqual(result["rejectedClaims"], ["remove-every-isolated-bright"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("feature:8,5", result["preservedResults"])
        self.assertIn("defect:4,5", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "frameCount": 1},
            {**valid, "featureX": 4, "featureY": 5},
            {**valid, "featureMoving": 1},
            {k: v for k, v in valid.items() if k != "saturated"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
