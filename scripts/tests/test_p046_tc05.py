"""TC-P046-05 held-out scene failure."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p046_tc05", Path(__file__).resolve().parents[1] / "gates" / "p046_tc05.py"
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
        "profileId": "daylight-chart",
        "trainingError": "3",
        "validationScene": "natural",
        "validationError": "11",
        "validationReported": True,
        "trainingOnly": False,
        "supportLimit": "daylight-chart",
    }
    base.update(overrides)
    return base


class TcP04605(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P046-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_natural_scene_failure_stays_separate_from_training(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "restricted")
        self.assertEqual(result["rejectedClaims"], ["held-out:natural"])
        self.assertEqual(
            result["preservedResults"],
            [
                "profile:daylight-chart",
                "training-error:3",
                "validation-scene:natural",
                "validation-error:11",
                "support:daylight-chart",
            ],
        )
        self.assertIn("supported conditions", _MODULE.EXPECTED)

    def test_skin_repeat_restricts_the_profile(self):
        result = evaluate(payload(validationScene="skin", validationError="9"))
        self.assertEqual(result["decision"], "restricted")
        self.assertEqual(result["rejectedClaims"], ["held-out:skin"])
        self.assertIn("training-error:3", result["preservedResults"])
        self.assertIn("validation-error:9", result["preservedResults"])

    def test_saturated_fabric_repeat_restricts_the_profile(self):
        result = evaluate(payload(validationScene="saturated-fabric", validationError="14"))
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("held-out:saturated-fabric", result["rejectedClaims"])
        self.assertIn("validation-scene:saturated-fabric", result["preservedResults"])
        self.assertIn("support:daylight-chart", result["preservedResults"])

    def test_foliage_repeat_restricts_the_profile(self):
        result = evaluate(payload(validationScene="foliage", validationError="8"))
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("held-out:foliage", result["rejectedClaims"])
        self.assertIn("validation-error:8", result["preservedResults"])

    def test_narrow_band_repeat_restricts_the_profile(self):
        result = evaluate(payload(validationScene="narrow-band", validationError="20"))
        self.assertEqual(result["decision"], "restricted")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("held-out:narrow-band", result["rejectedClaims"])
        self.assertIn("training-error:3", result["preservedResults"])

    def test_training_only_report_fails_and_keeps_validation(self):
        result = evaluate(payload(trainingOnly=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "restricted"})
        self.assertEqual(result["rejectedClaims"], ["training-only-error"])
        self.assertIn("training-error:3", result["preservedResults"])
        self.assertIn("validation-error:11", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_unreported_validation_is_rejected_without_erasing_the_scene(self):
        result = evaluate(payload(validationReported=False, validationError="", trainingOnly=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("validation-scene:natural", result["preservedResults"])
        self.assertIn("validation-error:unreported", result["preservedResults"])

    def test_training_scene_with_both_errors_stays_separated(self):
        result = evaluate(payload(validationScene="training", validationError="3"))
        self.assertEqual(result["decision"], "separated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("validation-error:3", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "supportLimit"},
            {**valid, "extra": True},
            {**valid, "validationScene": "sky"},
            {**valid, "trainingError": "03"},
            {**valid, "validationReported": False, "validationError": "4"},
            {**valid, "trainingOnly": "false"},
            {**valid, "supportLimit": "Daylight Chart"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
