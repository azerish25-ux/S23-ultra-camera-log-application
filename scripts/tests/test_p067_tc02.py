"""TC-P067-02 accumulated floating-point error."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p067_tc02", Path(__file__).resolve().parents[1] / "gates" / "p067_tc02.py"
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
        "stageId": "wide-blur",
        "operation": "wide-support",
        "precision": "fp32",
        "observedError": "0.001",
        "errorBudget": "0.01",
        "differentialValidation": True,
        "promoted": False,
        "signedValue": "-1.5",
        "highRange": "12",
        "cancellation": "0.0001",
    }
    base.update(overrides)
    return base


class TcP06702(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P067-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("FP16", _MODULE.NEGATIVE)
        self.assertIn("long blur", _MODULE.REPEAT)

    def test_inside_budget_keeps_sensitive_samples(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "within_budget")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("signed:-1.5", result["preservedResults"])
        self.assertIn("high-range:12", result["preservedResults"])
        self.assertIn("cancellation:0.0001", result["preservedResults"])
        self.assertIn("wide-blur", result["preservedResults"])

    def test_fp16_without_differential_fails_even_inside_budget(self):
        result = evaluate(payload(precision="fp16", differentialValidation=False, operation="long-blur"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["fp16-without-differential"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("signed:-1.5", result["preservedResults"])
        self.assertIn("observed:0.001", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "within_budget"})

    def test_fp16_with_differential_can_stay_inside_budget(self):
        result = evaluate(payload(precision="fp16", differentialValidation=True))
        self.assertEqual(result["decision"], "within_budget")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("precision:fp16", result["preservedResults"])

    def test_repeat_matrix_promotes_precision(self):
        result = evaluate(
            payload(operation="matrix", observedError="0.2", precision="fp32", promoted=True)
        )
        self.assertEqual(result["decision"], "precision_promoted")
        self.assertIn("operation:matrix", result["preservedResults"])
        self.assertIn("observed:0.2", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_highlight_without_promotion_is_rejected(self):
        result = evaluate(
            payload(operation="highlight", observedError="1", precision="fp16", differentialValidation=True, promoted=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["error-budget-exceeded"])
        self.assertIn("high-range:12", result["preservedResults"])
        self.assertIn("operation:highlight", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "observedError": "0.010"},
            {**valid, "errorBudget": "0"},
            {**valid, "signedValue": "-0"},
            {**valid, "precision": "fp8"},
            {**valid, "operation": "blur"},
            {**valid, "promoted": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
