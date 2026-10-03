"""TC-P056-06 real highlights are not removed with sensor defects."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p056_tc06", Path(__file__).resolve().parents[1] / "gates" / "p056_tc06.py"
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
        "frameIndex": 0,
        "defectId": "hot-12",
        "featureId": "speck",
        "defectCorrected": True,
        "featurePreserved": True,
        "removeAllIsolated": False,
        "nearSaturation": False,
    }
    base.update(overrides)
    return base


class TcP05606(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P056-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_several_frames_correct_only_the_defect(self):
        for frame in (0, 2, 5):
            result = evaluate(payload(frameIndex=frame))
            self.assertContract(result)
            self.assertEqual(result["decision"], "defect-only")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(f"frame:{frame}", result["preservedResults"])
            self.assertIn("feature:speck", result["preservedResults"])
            self.assertIn("defect:hot-12", result["preservedResults"])

    def test_near_saturated_boundary_keeps_the_feature(self):
        result = evaluate(payload(frameIndex=3, nearSaturation=True, featureId="lamp"))
        self.assertEqual(result["decision"], "defect-only")
        self.assertIn("boundary:saturated", result["preservedResults"])
        self.assertIn("feature:lamp", result["preservedResults"])
        self.assertIn("frame:3", result["preservedResults"])

    def test_negative_removing_every_isolated_bright_pixel_fails(self):
        result = evaluate(payload(removeAllIsolated=True, featurePreserved=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["remove-all-isolated-bright", "feature-removed"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("feature:speck", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "defect-only"})

    def test_feature_removal_without_a_blanket_policy_still_fails(self):
        result = evaluate(payload(featurePreserved=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["feature-removed"])
        self.assertIn("feature:speck", result["preservedResults"])

    def test_uncorrected_defect_is_withheld(self):
        result = evaluate(payload(defectCorrected=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("defect:hot-12", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "frameIndex": -1},
            {**valid, "defectId": ""},
            {**valid, "featurePreserved": "yes"},
            {**valid, "nearSaturation": 0},
            {k: v for k, v in valid.items() if k != "featureId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
