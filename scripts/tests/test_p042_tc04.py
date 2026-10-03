"""TC-P042-04 ill-conditioned calibration."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p042_tc04", Path(__file__).resolve().parents[1] / "gates" / "p042_tc04.py"
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
        "matrixId": "fit-a",
        "condition": "nearly_singular",
        "conditionNumber": "1000000",
        "diversity": 2,
        "uncertainty": "4",
    }
    base.update(overrides)
    return base


class TcP04204(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P042-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("nearly singular", _MODULE.INTERVENTION)
        self.assertIn("limited domain", _MODULE.EXPECTED)
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Returning an identity transform as an invisible fallback must fail.",
        )

    def test_identity_fallback_is_rejected(self):
        result = evaluate(
            payload(condition="identity_fallback", conditionNumber="1", diversity=24)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-fallback"])
        self.assertIn("matrix:fit-a", result["preservedResults"])
        self.assertIn("condition:1", result["preservedResults"])
        self.assertIn("diversity:24", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertNotIn("identity-matrix", result["preservedResults"])

    def test_nearly_singular_rejects_unstable_inversion(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unstable-inversion", result["rejectedClaims"])
        self.assertIn("nearly_singular", result["rejectedClaims"])
        self.assertIn("uncertainty:4", result["preservedResults"])

    def test_repeat_near_threshold_reports_limited_domain(self):
        result = evaluate(
            payload(condition="near_threshold", conditionNumber="12.5", uncertainty="0.5")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "limited_domain")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["limited-domain"])
        self.assertIn("uncertainty:0.5", result["preservedResults"])
        self.assertIn("condition:12.5", result["preservedResults"])
        self.assertIn("fit restricted to the reported domain", result["openQuestions"])

    def test_repeat_missing_illuminant_keeps_uncertainty(self):
        result = evaluate(payload(condition="missing_illuminant", diversity=0, uncertainty="2"))
        self.assertEqual(result["decision"], "limited_domain")
        self.assertIn("diversity:0", result["preservedResults"])
        self.assertIn("uncertainty:2", result["preservedResults"])
        self.assertIn("fit:missing_illuminant", result["preservedResults"])

    def test_invalid_illuminant_is_not_an_identity(self):
        result = evaluate(payload(condition="invalid_illuminant"))
        self.assertEqual(result["decision"], "limited_domain")
        self.assertNotIn("identity-fallback", result["rejectedClaims"])
        self.assertIn("matrix:fit-a", result["preservedResults"])

    def test_low_diversity_is_rejected(self):
        result = evaluate(payload(condition="low_diversity", diversity=1))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("low_diversity", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "conditionNumber": "0"},
            {**valid, "diversity": True},
            {**valid, "condition": "singular"},
            {**valid, "uncertainty": "-1"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
