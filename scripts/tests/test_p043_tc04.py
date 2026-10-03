"""TC-P043-04 ill-conditioned calibration."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p043_tc04", Path(__file__).resolve().parents[1] / "gates" / "p043_tc04.py"
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
        "condition": "stable",
        "conditionNumber": "12",
        "colorCount": 6,
        "illuminantEndpoints": "present",
        "uncertainty": "0.02",
        "identityFallback": False,
    }
    base.update(overrides)
    return base


class TcP04304(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P043-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("fit:chart-a", result["preservedResults"])
        self.assertIn("uncertainty:0.02", result["preservedResults"])

    def test_identity_fallback_fails(self):
        result = evaluate(payload(identityFallback=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "fit_recorded", "limited_domain"})
        self.assertIn("identity-fallback", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("fallback:refused", result["preservedResults"])
        self.assertNotIn("identity", result["preservedResults"])
        self.assertIn("fit:chart-a", result["preservedResults"])

    def test_near_threshold_reports_limited_domain(self):
        result = evaluate(payload(condition="near-threshold", conditionNumber="100"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "limited_domain")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("conditionNumber:100", result["preservedResults"])
        self.assertIn("limited domain uncertainty 0.02", result["reasons"])
        self.assertIn("near conditioning threshold", result["openQuestions"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_invalid_illuminant_endpoints_reject_the_fit(self):
        result = evaluate(payload(illuminantEndpoints="invalid"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "fit_recorded"})
        self.assertIn("illuminant-endpoints:invalid", result["rejectedClaims"])
        self.assertIn("uncertainty:0.02", result["preservedResults"])
        self.assertIn("fit:chart-a", result["preservedResults"])

    def test_missing_illuminant_endpoints_reject_the_fit(self):
        result = evaluate(payload(illuminantEndpoints="missing"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("illuminant-endpoints:missing", result["rejectedClaims"])
        self.assertIn("condition:stable", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_nearly_singular_matrix_is_not_inverted(self):
        result = evaluate(payload(condition="nearly-singular", conditionNumber="1000"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unstable-inversion", result["rejectedClaims"])
        self.assertNotIn("identity-fallback", result["rejectedClaims"])
        self.assertIn("fallback:absent", result["preservedResults"])
        self.assertIn("conditionNumber:1000", result["preservedResults"])

    def test_low_diversity_reports_its_domain(self):
        result = evaluate(payload(condition="low-diversity", colorCount=2))
        self.assertEqual(result["decision"], "limited_domain")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("colors:2", result["preservedResults"])
        self.assertIn("limited color diversity", result["openQuestions"])
        self.assertIn("uncertainty:0.02", result["preservedResults"])

    def test_stable_fit_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "fit_recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("fallback:absent", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "condition": "singular"},
            {**valid, "condition": "stable", "colorCount": 2},
            {**valid, "conditionNumber": "12.0"},
            {**valid, "identityFallback": "false"},
            {**valid, "uncertainty": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
