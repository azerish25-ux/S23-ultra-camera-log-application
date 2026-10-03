"""TC-P053-04 nonlinear processing order."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p053_tc04", Path(__file__).resolve().parents[1] / "gates" / "p053_tc04.py"
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
        "domain": "scene-linear",
        "declaredOrder": "linear-before-blur",
        "appliedOrder": "linear-before-blur",
        "referenceAgrees": True,
        "visuallyPlausible": True,
    }
    base.update(overrides)
    return base


class TcP05304(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P053-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_scene_linear_order_matches_the_reference(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "domain_reference")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("domain:scene-linear", result["preservedResults"])
        self.assertIn("declared:linear-before-blur", result["preservedResults"])
        self.assertIn("operation:blur", result["preservedResults"])

    def test_logarithmic_and_display_encoded_orders_are_separate(self):
        log = evaluate(
            payload(
                domain="logarithmic",
                operation="reduction",
                declaredOrder="log-before-reduction",
                appliedOrder="log-before-reduction",
            )
        )
        display = evaluate(
            payload(
                domain="display-encoded",
                operation="color",
                declaredOrder="linear-before-color",
                appliedOrder="linear-before-color",
                visuallyPlausible=False,
            )
        )
        self.assertEqual(log["decision"], "domain_reference")
        self.assertEqual(display["decision"], "domain_reference")
        self.assertIn("domain:logarithmic", log["preservedResults"])
        self.assertIn("domain:display-encoded", display["preservedResults"])
        self.assertIn("operation:color", display["preservedResults"])

    def test_visually_plausible_order_violation_is_rejected(self):
        result = evaluate(
            payload(
                domain="display-encoded",
                operation="exposure-scale",
                declaredOrder="linear-before-scale",
                appliedOrder="scale-after-encode",
                visuallyPlausible=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["order-violation", "visually-plausible-insufficient"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("applied:scale-after-encode", result["preservedResults"])
        self.assertIn("declared:linear-before-scale", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "domain_reference"})

    def test_reference_disagreement_fails_even_when_implausible(self):
        result = evaluate(payload(referenceAgrees=False, visuallyPlausible=False, operation="color"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("reference-disagreement", result["rejectedClaims"])
        self.assertIn("operation:color", result["preservedResults"])
        self.assertNotIn("visually-plausible-insufficient", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "domain": "camera"},
            {**valid, "operation": "sharpen"},
            {**valid, "declaredOrder": "Linear"},
            {**valid, "referenceAgrees": "yes"},
            {**valid, "appliedOrder": ""},
            {key: value for key, value in valid.items() if key != "domain"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
