"""TC-P047-05 training error is not a substitute for held-out scenes."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p047_tc05", Path(__file__).resolve().parents[1] / "gates" / "p047_tc05.py"
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
        "sceneClass": "skin",
        "trainingError": "0.006",
        "validationError": "0.2",
        "tolerance": "0.04",
        "reportTrainingOnly": False,
    }
    base.update(overrides)
    return base


class TcP04705(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P047-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("training-error:0.006", result["preservedResults"])
        self.assertIn("profile:profile-a", result["preservedResults"])

    def test_constants(self):
        self.assertIn("independent natural scene", _MODULE.INTERVENTION)
        self.assertIn("supported conditions", _MODULE.EXPECTED)
        self.assertIn("only training error", _MODULE.NEGATIVE)

    def test_skin_failure_keeps_training_and_validation_apart(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "restricted")
        self.assertEqual(result["rejectedClaims"], ["held-out:skin"])
        self.assertIn("validation-error:0.2", result["preservedResults"])
        self.assertIn("supported-conditions-exclude:skin", result["openQuestions"])
        self.assertTrue(any("not the acceptance metric" in item for item in result["reasons"]))

    def test_saturated_fabrics_and_foliage_repeat(self):
        for scene, error in (("saturated-fabrics", "0.15"), ("foliage", "0.09")):
            result = evaluate(payload(sceneClass=scene, validationError=error))
            self.assertEqual(result["decision"], "restricted")
            self.assertEqual(result["rejectedClaims"], ["held-out:" + scene])
            self.assertIn("scene:" + scene, result["preservedResults"])
            self.assertIn("training-error:0.006", result["preservedResults"])
            self.assertIn("validation-error:" + error, result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_narrow_band_lighting_repeat(self):
        result = evaluate(payload(sceneClass="narrow-band", validationError="0.3"))
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("held-out:narrow-band", result["rejectedClaims"])
        self.assertIn("training-error:0.006", result["preservedResults"])

    def test_training_only_report_fails(self):
        result = evaluate(payload(validationError="0.01", reportTrainingOnly=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["training-only-report"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("validation-error:0.01", result["preservedResults"])
        self.assertIn("training-error:0.006", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "separated", "restricted"})

    def test_within_tolerance_stays_separated(self):
        result = evaluate(payload(sceneClass="foliage", validationError="0.01"))
        self.assertEqual(result["decision"], "separated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("training-error:0.006", result["preservedResults"])
        self.assertIn("validation-error:0.01", result["preservedResults"])
        self.assertIn("profile restricted to supported conditions", result["openQuestions"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "sceneClass": "neutral"},
            {**valid, "tolerance": "0"},
            {**valid, "trainingError": "0.0060"},
            {**valid, "reportTrainingOnly": "false"},
            {k: v for k, v in valid.items() if k != "validationError"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
