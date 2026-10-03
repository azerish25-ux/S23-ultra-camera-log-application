"""TC-P048-04 identity fallback is not a stable calibration."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p048_tc04", Path(__file__).resolve().parents[1] / "gates" / "p048_tc04.py"
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
        "conditionNumber": "12",
        "colorCount": 6,
        "identityFallback": False,
        "illuminantEndpoint": "present",
        "domainNote": "chart-domain",
    }
    base.update(overrides)
    return base


class TcP04804(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P048-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("domain:chart-domain", result["preservedResults"])

    def test_constants(self):
        self.assertIn("nearly singular", _MODULE.INTERVENTION)
        self.assertIn("limited domain", _MODULE.EXPECTED)
        self.assertIn("identity transform", _MODULE.NEGATIVE)
        self.assertIn("\u2019", _MODULE.EXPECTED)

    def test_negative_identity_fallback_fails(self):
        result = evaluate(payload(identityFallback=True, conditionNumber="5000"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-fallback"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("condition:5000", result["preservedResults"])
        self.assertNotIn("transform:identity", result["preservedResults"])

    def test_repeat_near_conditioning_threshold(self):
        result = evaluate(payload(conditionNumber="1000", illuminantEndpoint="near_threshold"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("condition:1000", result["preservedResults"])
        self.assertIn("endpoint:near_threshold", result["preservedResults"])

    def test_repeat_missing_and_invalid_illuminant_endpoints(self):
        missing = evaluate(payload(illuminantEndpoint="missing"))
        invalid = evaluate(payload(illuminantEndpoint="invalid"))
        self.assertEqual(missing["decision"], "rejected")
        self.assertIn("missing-illuminant-endpoint", missing["rejectedClaims"])
        self.assertIn("endpoint:missing", missing["preservedResults"])
        self.assertEqual(invalid["decision"], "rejected")
        self.assertIn("invalid-illuminant-endpoint", invalid["rejectedClaims"])
        self.assertIn("condition:12", invalid["preservedResults"])
        self.assertNotIn(missing["decision"], {"qualified", "allowed"})
        self.assertNotIn(invalid["decision"], {"qualified", "allowed"})

    def test_limited_color_diversity_reports_domain(self):
        result = evaluate(payload(colorCount=2))
        self.assertEqual(result["decision"], "limited_domain")
        self.assertIn("limited-color-diversity", result["rejectedClaims"])
        self.assertIn("colors:2", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        for item in (None, {}, {**valid, "conditionNumber": "0"}, {**valid, "identityFallback": "yes"}):
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
