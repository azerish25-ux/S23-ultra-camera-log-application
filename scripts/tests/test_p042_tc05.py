"""TC-P042-05 held-out scene failure."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p042_tc05", Path(__file__).resolve().parents[1] / "gates" / "p042_tc05.py"
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
        "profileId": "profile-a",
        "scene": "skin",
        "trainingError": "3",
        "validationError": "40",
        "report": "separated",
    }
    base.update(overrides)
    return base


class TcP04205(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P042-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("training patches", _MODULE.INTERVENTION)
        self.assertIn("training and validation", _MODULE.EXPECTED)
        self.assertEqual(_MODULE.NEGATIVE, "Reporting only training error must fail.")

    def test_training_only_report_is_rejected(self):
        result = evaluate(payload(report="training_only"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["training-only-error"])
        self.assertIn("training-error:3", result["preservedResults"])
        self.assertIn("validation-error:40", result["preservedResults"])
        self.assertIn("scene:skin", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_repeat_skin_keeps_errors_separate(self):
        result = evaluate(payload(scene="skin"))
        self.assertEqual(result["decision"], "restricted")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["held-out-scene"])
        self.assertEqual(
            result["preservedResults"][:4],
            [
                "profile:profile-a",
                "scene:skin",
                "training-error:3",
                "validation-error:40",
            ],
        )
        self.assertIn("profile restricted for skin", result["reasons"])

    def test_repeat_foliage_is_restricted(self):
        result = evaluate(payload(scene="foliage", trainingError="1", validationError="9"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("scene:foliage", result["preservedResults"])
        self.assertIn("training-error:1", result["preservedResults"])
        self.assertIn("validation-error:9", result["preservedResults"])
        self.assertIn("unsupported scenes are outside the profile", result["openQuestions"])

    def test_saturated_fabrics_and_narrow_band_stay_separate(self):
        for scene in ("saturated_fabrics", "narrow_band"):
            result = evaluate(payload(scene=scene))
            self.assertEqual(result["decision"], "restricted")
            self.assertIn(f"scene:{scene}", result["preservedResults"])
            self.assertIn("training-error:3", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_equal_errors_are_withheld_not_certified(self):
        result = evaluate(payload(scene="skin", trainingError="4", validationError="4"))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("validation-error:4", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "scene": "sky"},
            {**valid, "trainingError": -3},
            {**valid, "report": "validation_only"},
            {**valid, "validationError": "4.0"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
