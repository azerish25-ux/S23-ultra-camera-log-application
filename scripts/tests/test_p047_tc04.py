"""TC-P047-04 ill-conditioned fits are not rescued by an identity matrix."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p047_tc04", Path(__file__).resolve().parents[1] / "gates" / "p047_tc04.py"
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
        "fitId": "fit-a",
        "conditionNumber": "2.5",
        "colorDiversity": "adequate",
        "illuminantEndpoints": "present",
        "identityFallback": False,
    }
    base.update(overrides)
    return base


class TcP04704(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P047-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("fit:fit-a", result["preservedResults"])

    def test_constants(self):
        self.assertIn("nearly singular", _MODULE.INTERVENTION)
        self.assertIn("limited domain", _MODULE.EXPECTED)
        self.assertIn("\u2019", _MODULE.EXPECTED)
        self.assertIn("identity transform", _MODULE.NEGATIVE)

    def test_healthy_condition_is_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "conditioned")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("condition:2.5", result["preservedResults"])
        self.assertIn("host condition number is not a measured camera matrix", result["openQuestions"])

    def test_near_threshold_reports_limited_domain(self):
        result = evaluate(payload(conditionNumber="80"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "limited_domain")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("uncertainty:condition:80", result["openQuestions"])
        self.assertIn("condition:80", result["preservedResults"])
        self.assertIn("near the conditioning threshold", " ".join(result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed", "conditioned"})

    def test_invalid_illuminant_endpoints_repeat(self):
        result = evaluate(payload(illuminantEndpoints="invalid", conditionNumber="3"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("illuminant-endpoints:invalid", result["rejectedClaims"])
        self.assertIn("condition:3", result["preservedResults"])
        self.assertIn("endpoints:invalid", result["preservedResults"])

    def test_missing_illuminant_endpoints_repeat(self):
        result = evaluate(payload(illuminantEndpoints="missing"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["illuminant-endpoints:missing"])
        self.assertIn("diversity:adequate", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "limited_domain"})

    def test_unstable_inversion_is_rejected(self):
        result = evaluate(payload(conditionNumber="100"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unstable-inversion", result["rejectedClaims"])
        self.assertIn("condition:100", result["preservedResults"])

    def test_inadequate_diversity_is_rejected(self):
        result = evaluate(payload(colorDiversity="inadequate"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("inadequate-color-diversity", result["rejectedClaims"])
        self.assertIn("condition:2.5", result["preservedResults"])

    def test_identity_fallback_fails_and_keeps_the_condition(self):
        result = evaluate(payload(identityFallback=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-fallback"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("condition:2.5", result["preservedResults"])
        self.assertIn("identityFallback:true", result["preservedResults"])
        self.assertNotIn("condition:1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "conditioned"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "conditionNumber": "0"},
            {**valid, "conditionNumber": "2.50"},
            {**valid, "colorDiversity": "rich"},
            {**valid, "illuminantEndpoints": "none"},
            {**valid, "identityFallback": "false"},
            {k: v for k, v in valid.items() if k != "fitId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
