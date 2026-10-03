"""TC-P041-04 ill-conditioned calibration."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p041_tc04", Path(__file__).resolve().parents[1] / "gates" / "p041_tc04.py"
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
        "conditionNumber": "12.5",
        "colorDiversity": "adequate",
        "illuminantEndpoints": "present",
        "identityFallback": False,
        "uncertainty": "unreported",
        "domain": "chart-d65",
    }
    base.update(overrides)
    return base


class TcP04104(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P041-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_identity_fallback_fails_and_keeps_the_condition(self):
        result = evaluate(payload(identityFallback=True, conditionNumber="100000"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("identity-fallback", result["rejectedClaims"])
        self.assertIn("unstable-inversion", result["rejectedClaims"])
        self.assertIn("condition:100000", result["preservedResults"])
        self.assertIn("domain:chart-d65", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertNotIn("matrix:identity", result["preservedResults"])

    def test_below_threshold_is_stable_and_not_certified(self):
        result = evaluate(payload(conditionNumber="9999.9"))
        self.assertEqual(result["decision"], "inversion_stable")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("condition:9999.9", result["preservedResults"])
        self.assertIn("stable inversion is not a certified profile", result["openQuestions"])

    def test_near_threshold_above_reports_limited_domain(self):
        result = evaluate(payload(conditionNumber="10000.1", uncertainty="0.2", domain="near-threshold"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "limited_domain")
        self.assertEqual(result["rejectedClaims"], ["unstable-inversion"])
        self.assertIn("condition:10000.1", result["preservedResults"])
        self.assertIn("uncertainty:0.2", result["preservedResults"])
        self.assertIn("domain:near-threshold", result["openQuestions"])
        self.assertIn("\u2019", _MODULE.EXPECTED)

    def test_unreported_uncertainty_rejects_the_unstable_inversion(self):
        result = evaluate(payload(conditionNumber="10000.1"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unstable-inversion"])
        self.assertIn("uncertainty:unreported", result["preservedResults"])

    def test_missing_illuminant_endpoints_repeat_rejects(self):
        result = evaluate(payload(illuminantEndpoints="missing", domain="open-illuminant"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("illuminant-endpoints-missing", result["rejectedClaims"])
        self.assertIn("domain:open-illuminant", result["preservedResults"])
        self.assertIn("endpoints:missing", result["preservedResults"])

    def test_invalid_illuminant_endpoints_repeat_rejects(self):
        result = evaluate(payload(illuminantEndpoints="invalid", uncertainty="0.4"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["illuminant-endpoints-invalid"])
        self.assertIn("uncertainty:0.4", result["preservedResults"])

    def test_narrow_diversity_reports_its_domain(self):
        result = evaluate(payload(colorDiversity="narrow", uncertainty="0.8", domain="two-patch"))
        self.assertEqual(result["decision"], "limited_domain")
        self.assertEqual(result["rejectedClaims"], ["narrow-diversity"])
        self.assertIn("diversity:narrow", result["preservedResults"])
        self.assertIn("domain:two-patch", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "conditionNumber": "-1"},
            {**valid, "conditionNumber": "10000.10"},
            {**valid, "colorDiversity": "low"},
            {**valid, "identityFallback": "false"},
            {**valid, "uncertainty": "NaN"},
            {**valid, "domain": "bad domain"},
            {**valid, "illuminantEndpoints": "wrong"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
