"""TC-P044-04 ill-conditioned calibration."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p044_tc04", Path(__file__).resolve().parents[1] / "gates" / "p044_tc04.py"
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
        "colorCount": 18,
        "identityFallback": False,
        "illuminantEndpoint": "present",
        "domainNote": "chart-fit",
    }
    base.update(overrides)
    return base


class TcP04404(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P044-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_intervention_expected_and_negative(self):
        self.assertIn("nearly singular", _MODULE.INTERVENTION)
        self.assertIn("limited domain", _MODULE.EXPECTED)
        self.assertIn("\u2019", _MODULE.EXPECTED)
        self.assertIn("identity transform", _MODULE.NEGATIVE)

    def test_stable_fit_is_withheld_and_keeps_the_condition(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("condition:12", result["preservedResults"])
        self.assertIn("colors:18", result["preservedResults"])
        self.assertIn("domain:chart-fit", result["preservedResults"])
        self.assertNotIn("transform:identity", result["preservedResults"])

    def test_nearly_singular_matrix_rejects_inversion(self):
        result = evaluate(payload(conditionNumber="1001"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unstable-inversion"])
        self.assertIn("condition:1001", result["preservedResults"])
        self.assertIn("unstable inversion rejected", result["reasons"])

    def test_limited_color_diversity_reports_uncertainty(self):
        result = evaluate(payload(colorCount=2, domainNote="two-swatch"))
        self.assertEqual(result["decision"], "limited_domain")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["limited-color-diversity"])
        self.assertIn("colors:2", result["preservedResults"])
        self.assertIn("domain:two-swatch", result["preservedResults"])
        self.assertIn("uncertainty recorded for a limited fit domain", result["openQuestions"])

    def test_near_threshold_repeat_does_not_certify_inversion(self):
        result = evaluate(payload(conditionNumber="1000", illuminantEndpoint="near_threshold"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("condition:1000", result["preservedResults"])
        self.assertIn("endpoint:near_threshold", result["preservedResults"])
        self.assertIn("near conditioning threshold; inversion not certified", result["openQuestions"])

    def test_missing_illuminant_endpoint_repeat(self):
        result = evaluate(payload(illuminantEndpoint="missing"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["missing-illuminant-endpoint"])
        self.assertIn("endpoint:missing", result["preservedResults"])
        self.assertIn("condition:12", result["preservedResults"])

    def test_invalid_illuminant_endpoint_repeat(self):
        result = evaluate(payload(illuminantEndpoint="invalid"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["invalid-illuminant-endpoint"])
        self.assertIn("endpoint:invalid", result["preservedResults"])

    def test_negative_identity_fallback_cannot_qualify(self):
        result = evaluate(payload(identityFallback=True, conditionNumber="4"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})
        self.assertEqual(result["rejectedClaims"], ["identity-fallback"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("condition:4", result["preservedResults"])
        self.assertNotIn("transform:identity", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "domainNote"},
            {**valid, "extra": True},
            {**valid, "conditionNumber": "0"},
            {**valid, "conditionNumber": 12},
            {**valid, "colorCount": 0},
            {**valid, "colorCount": True},
            {**valid, "identityFallback": "false"},
            {**valid, "illuminantEndpoint": "absent"},
            {**valid, "domainNote": " "},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
