"""TC-P044-03 matrix convention mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p044_tc03", Path(__file__).resolve().parents[1] / "gates" / "p044_tc03.py"
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
        "transform": "forward",
        "determinant": "2",
        "neutralCheck": True,
        "colorVectorCheck": True,
        "whitePoint": "d65",
        "certifyByDeterminant": False,
    }
    base.update(overrides)
    return base


class TcP04403(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P044-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_intervention_expected_and_negative(self):
        self.assertIn("Transpose or reverse", _MODULE.INTERVENTION)
        self.assertIn("convention error", _MODULE.EXPECTED)
        self.assertIn("finite determinant", _MODULE.NEGATIVE)

    def test_forward_checks_are_held_without_a_certificate(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "checks_held")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("transform:forward", result["preservedResults"])
        self.assertIn("determinant:2", result["preservedResults"])
        self.assertIn("white-point:d65", result["preservedResults"])

    def test_transposed_transform_is_a_convention_error(self):
        result = evaluate(
            payload(transform="transposed", neutralCheck=False, colorVectorCheck=False)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("convention-error:transposed", result["rejectedClaims"])
        self.assertIn("neutral-check-failed", result["rejectedClaims"])
        self.assertIn("color-vector-check-failed", result["rejectedClaims"])
        self.assertIn("determinant:2", result["preservedResults"])
        self.assertIn("specific convention error transposed", result["reasons"])

    def test_wrong_white_point_repeat_keeps_the_finite_determinant(self):
        result = evaluate(payload(whitePoint="wrong", determinant="-3"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["wrong-white-point"])
        self.assertIn("determinant:-3", result["preservedResults"])
        self.assertIn("white-point:wrong", result["preservedResults"])

    def test_duplicated_white_balance_repeat_is_not_a_certificate(self):
        result = evaluate(payload(whitePoint="duplicated_wb"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["duplicated-white-balance"])
        self.assertIn("transform:forward", result["preservedResults"])
        self.assertIn("determinant:2", result["preservedResults"])

    def test_swapped_direction_repeat_names_the_convention(self):
        result = evaluate(payload(transform="swapped_direction", determinant="1"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["convention-error:swapped_direction"])
        self.assertIn("determinant:1", result["preservedResults"])
        self.assertIn("specific convention error swapped_direction", result["reasons"])

    def test_negative_finite_determinant_alone_cannot_qualify(self):
        result = evaluate(payload(certifyByDeterminant=True, determinant="1"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "checks_held"})
        self.assertEqual(result["rejectedClaims"], ["determinant-not-a-certificate"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("determinant:1", result["preservedResults"])
        self.assertIn("neutral-check:true", result["preservedResults"])
        self.assertIn("color-vector-check:true", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "transform"},
            {**valid, "extra": True},
            {**valid, "transform": "inverse"},
            {**valid, "determinant": "0"},
            {**valid, "determinant": "1.5"},
            {**valid, "determinant": 2},
            {**valid, "neutralCheck": "true"},
            {**valid, "whitePoint": "D65"},
            {**valid, "certifyByDeterminant": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
