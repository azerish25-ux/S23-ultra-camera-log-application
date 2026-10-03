"""TC-P055-06 defect versus real highlight."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p055_tc06", Path(__file__).resolve().parents[1] / "gates" / "p055_tc06.py"
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
        "featureId": "spark-3",
        "frameCount": 1,
        "nearSaturation": False,
        "removeAllIsolated": False,
        "defectPersistent": True,
        "featureMoving": True,
    }
    base.update(overrides)
    return base


class TcP05506(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P055-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(_MODULE.NEGATIVE, "Removing every isolated bright pixel must fail.")
        self.assertIn("persistent sensor defect", _MODULE.INTERVENTION)

    def test_only_the_defect_is_corrected(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "defect_only")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("defect:hot-12", result["preservedResults"])
        self.assertIn("feature:spark-3", result["preservedResults"])

    def test_negative_removing_every_isolated_pixel_fails(self):
        result = evaluate(payload(removeAllIsolated=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["removed-every-isolated-bright-pixel"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("feature:spark-3", result["preservedResults"])
        self.assertIn("defect:hot-12", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "defect_only"})

    def test_repeat_several_frames(self):
        result = evaluate(payload(frameCount=5))
        self.assertEqual(result["decision"], "defect_only")
        self.assertIn("frames:5", result["preservedResults"])
        self.assertTrue(any("5 frames" in item for item in result["openQuestions"]))

    def test_repeat_near_saturated_boundary(self):
        result = evaluate(payload(nearSaturation=True, frameCount=3))
        self.assertEqual(result["decision"], "defect_only")
        self.assertIn("near-saturation:true", result["preservedResults"])
        self.assertIn("feature:spark-3", result["preservedResults"])

    def test_non_persistent_defect_is_withheld(self):
        result = evaluate(payload(defectPersistent=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("defect:hot-12", result["preservedResults"])
        self.assertIn("feature:spark-3", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "frameCount": 0},
            {**valid, "featureId": "hot-12"},
            {**valid, "removeAllIsolated": "yes"},
            {**valid, "defectId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
