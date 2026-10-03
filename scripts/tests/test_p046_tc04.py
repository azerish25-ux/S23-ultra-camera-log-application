"""TC-P046-04 ill-conditioned calibration."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p046_tc04", Path(__file__).resolve().parents[1] / "gates" / "p046_tc04.py"
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
        "fitId": "chart-fit",
        "conditionNumerator": "7",
        "conditionDenominator": "3",
        "thresholdNumerator": "20",
        "thresholdDenominator": "1",
        "diversity": "adequate",
        "identityFallback": False,
        "uncertainty": "4",
    }
    base.update(overrides)
    return base


class TcP04604(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P046-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_stable_adequate_fit_is_not_a_physical_calibration(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "conditioned")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("condition:7/3", result["preservedResults"])
        self.assertIn("fit", _MODULE.EXPECTED)
        self.assertIn("\u2019", _MODULE.EXPECTED)

    def test_near_threshold_reports_limited_domain(self):
        result = evaluate(payload(conditionNumerator="11", conditionDenominator="1", uncertainty="6"))
        self.assertEqual(result["decision"], "limited_domain")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "conditioned"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("condition:11/1", result["preservedResults"])
        self.assertIn("uncertainty:6", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["uncertainty 6"])

    def test_threshold_itself_rejects_unstable_inversion(self):
        result = evaluate(payload(conditionNumerator="20", conditionDenominator="1"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unstable-inversion"])
        self.assertIn("condition:20/1", result["preservedResults"])
        self.assertNotIn("condition:1/1", result["preservedResults"])

    def test_invalid_illuminant_endpoints_repeat(self):
        result = evaluate(payload(diversity="invalid", uncertainty="9"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["invalid-illuminant-endpoints"])
        self.assertIn("diversity:invalid", result["preservedResults"])
        self.assertIn("uncertainty:9", result["preservedResults"])

    def test_missing_illuminant_endpoints_repeat(self):
        result = evaluate(payload(diversity="missing-endpoints"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-illuminant-endpoints", result["rejectedClaims"])
        self.assertIn("diversity:missing-endpoints", result["preservedResults"])
        self.assertIn("condition:7/3", result["preservedResults"])

    def test_narrow_diversity_reports_uncertainty(self):
        result = evaluate(payload(diversity="narrow", uncertainty="12"))
        self.assertEqual(result["decision"], "limited_domain")
        self.assertIn("limited domain uncertainty 12", result["reasons"])
        self.assertIn("diversity:narrow", result["preservedResults"])

    def test_identity_fallback_fails_and_keeps_the_condition(self):
        result = evaluate(payload(identityFallback=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "conditioned"})
        self.assertEqual(result["rejectedClaims"], ["identity-fallback"])
        self.assertIn("condition:7/3", result["preservedResults"])
        self.assertIn("identity-fallback:true", result["preservedResults"])
        self.assertNotIn("condition:1/1", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "diversity"},
            {**valid, "extra": True},
            {**valid, "conditionNumerator": "7.0"},
            {**valid, "conditionDenominator": "0"},
            {**valid, "diversity": "wide"},
            {**valid, "identityFallback": "false"},
            {**valid, "uncertainty": "-1"},
            {**valid, "thresholdNumerator": "0"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
