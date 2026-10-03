"""TC-P045-04 ill-conditioned calibration."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p045_tc04", Path(__file__).resolve().parents[1] / "gates" / "p045_tc04.py"
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
        "fitId": "chart-a",
        "conditionNumber": "12",
        "colorDiversity": "adequate",
        "identityFallback": False,
        "illuminantEndpoints": "present",
        "uncertainty": "0.01",
    }
    base.update(overrides)
    return base


class TcP04504(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P045-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("fit:chart-a", result["preservedResults"])

    def test_well_conditioned_fit_is_not_an_identity_fallback(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "conditioned")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("condition:12", result["preservedResults"])
        self.assertIn("uncertainty:0.01", result["preservedResults"])

    def test_negative_identity_fallback_fails_and_keeps_the_condition(self):
        result = evaluate(payload(identityFallback=True, conditionNumber="40"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("identity-fallback", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("condition:40", result["preservedResults"])
        self.assertNotIn("condition:1", result["preservedResults"])

    def test_unstable_inversion_is_rejected(self):
        result = evaluate(payload(conditionNumber="1000", colorDiversity="inadequate"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unstable-inversion", result["rejectedClaims"])
        self.assertIn("inadequate-color-diversity", result["rejectedClaims"])
        self.assertIn("condition:1000", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "limited_domain"})

    def test_repeat_near_threshold_reports_limited_domain(self):
        for number in ("100", "999"):
            result = evaluate(payload(conditionNumber=number, uncertainty="0.2"))
            self.assertEqual(result["decision"], "limited_domain")
            self.assertIn("near-condition-threshold", result["openQuestions"])
            self.assertIn(f"condition:{number}", result["preservedResults"])
            self.assertIn("uncertainty:0.2", result["preservedResults"])
            self.assertNotIn("identity-fallback", result["rejectedClaims"])

    def test_inadequate_diversity_limits_the_domain(self):
        result = evaluate(payload(colorDiversity="inadequate", uncertainty="0.3"))
        self.assertEqual(result["decision"], "limited_domain")
        self.assertIn("inadequate-color-diversity", result["rejectedClaims"])
        self.assertIn("diversity:inadequate", result["preservedResults"])
        self.assertIn("uncertainty:0.3", result["preservedResults"])

    def test_repeat_missing_illuminant_endpoints(self):
        result = evaluate(payload(illuminantEndpoints="missing"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("illuminant-endpoints:missing", result["rejectedClaims"])
        self.assertIn("endpoints:missing", result["preservedResults"])

    def test_repeat_invalid_illuminant_endpoints(self):
        result = evaluate(payload(illuminantEndpoints="invalid", conditionNumber="100"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("illuminant-endpoints:invalid", result["rejectedClaims"])
        self.assertNotEqual(result["decision"], "limited_domain")
        self.assertIn("condition:100", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "fitId"},
            {**valid, "extra": True},
            {**valid, "conditionNumber": "0"},
            {**valid, "conditionNumber": "12.0"},
            {**valid, "identityFallback": "false"},
            {**valid, "colorDiversity": "low"},
            {**valid, "illuminantEndpoints": "absent"},
            {**valid, "uncertainty": "-0.1"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
