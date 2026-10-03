"""TC-P054-04 nonlinear processing order."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p054_tc04", Path(__file__).resolve().parents[1] / "gates" / "p054_tc04.py"
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
        "operation": "blur",
        "appliedDomain": "scene-linear",
        "declaredDomain": "scene-linear",
        "referenceDelta": "0",
        "plausible": False,
    }
    base.update(overrides)
    return base


class TcP05404(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P054-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_repeat_logarithmic_order_is_rejected(self):
        result = evaluate(
            payload(
                operation="reduction",
                appliedDomain="logarithmic",
                declaredDomain="scene-linear",
                referenceDelta="0.2",
                plausible=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["order-violation", "reference-disagreement", "plausible-not-sufficient"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("logarithmic", result["preservedResults"])
        self.assertIn("delta:0.2", result["preservedResults"])
        self.assertIn("reduction", result["preservedResults"])

    def test_repeat_display_encoded_order_is_rejected(self):
        result = evaluate(
            payload(
                operation="color",
                appliedDomain="display-encoded",
                declaredDomain="scene-linear",
                referenceDelta="0.05",
                plausible=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("order-violation", result["rejectedClaims"])
        self.assertIn("plausible-not-sufficient", result["rejectedClaims"])
        self.assertIn("display-encoded", result["preservedResults"])
        self.assertIn("delta:0.05", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "domain-matched"})

    def test_repeat_scene_linear_match_is_domain_matched(self):
        result = evaluate(payload(operation="exposure-scale", referenceDelta="0", plausible=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "domain-matched")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("exposure-scale", result["preservedResults"])
        self.assertIn("scene-linear", result["preservedResults"])
        self.assertIn("delta:0", result["preservedResults"])

    def test_negative_plausible_result_does_not_excuse_blur_order(self):
        result = evaluate(
            payload(
                operation="blur",
                appliedDomain="display-encoded",
                declaredDomain="logarithmic",
                referenceDelta="0",
                plausible=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("order-violation", result["rejectedClaims"])
        self.assertIn("plausible-not-sufficient", result["rejectedClaims"])
        self.assertNotIn("reference-disagreement", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("blur", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "operation"},
            {**valid, "extra": True},
            {**valid, "operation": "sharpen"},
            {**valid, "appliedDomain": "linear"},
            {**valid, "referenceDelta": "0.00"},
            {**valid, "referenceDelta": "-0.1"},
            {**valid, "plausible": "true"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
