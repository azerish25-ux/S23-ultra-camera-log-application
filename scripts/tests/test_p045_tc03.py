"""TC-P045-03 matrix convention mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p045_tc03", Path(__file__).resolve().parents[1] / "gates" / "p045_tc03.py"
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
        "matrixId": "cam-to-work",
        "convention": "row_major",
        "determinantFinite": True,
        "whitePoint": "matched",
        "whiteBalance": "single",
        "neutralCheck": "pass",
        "colorVectorCheck": "pass",
    }
    base.update(overrides)
    return base


class TcP04503(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P045-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("matrix:cam-to-work", result["preservedResults"])

    def test_matching_convention_is_checked_not_certified_by_determinant(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "convention_checked")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("determinant:finite", result["preservedResults"])
        self.assertTrue(any("finite determinant was not the certificate" in item for item in result["reasons"]))

    def test_negative_finite_determinant_does_not_certify_a_transpose(self):
        result = evaluate(payload(convention="transposed", neutralCheck="pass", colorVectorCheck="pass"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("convention:transposed", result["rejectedClaims"])
        self.assertIn("finite-determinant-not-certificate", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("convention:transposed", result["preservedResults"])

    def test_reversed_transform_fails(self):
        result = evaluate(payload(convention="reversed"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("convention:reversed", result["rejectedClaims"])
        self.assertIn("matrix:cam-to-work", result["preservedResults"])

    def test_repeat_wrong_white_point(self):
        result = evaluate(payload(whitePoint="wrong"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("wrong-white-point", result["rejectedClaims"])
        self.assertIn("finite-determinant-not-certificate", result["rejectedClaims"])
        self.assertIn("white-point:wrong", result["preservedResults"])

    def test_repeat_duplicated_white_balance(self):
        result = evaluate(payload(whiteBalance="duplicated"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicated-white-balance", result["rejectedClaims"])
        self.assertIn("white-balance:duplicated", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_swapped_matrix_direction(self):
        result = evaluate(payload(convention="swapped_direction", neutralCheck="fail", colorVectorCheck="fail"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("convention:swapped_direction", result["rejectedClaims"])
        self.assertIn("neutral-check", result["rejectedClaims"])
        self.assertIn("color-vector-check", result["rejectedClaims"])
        self.assertIn("neutral-check:fail", result["preservedResults"])

    def test_failed_checks_with_only_a_finite_determinant_are_rejected(self):
        result = evaluate(payload(neutralCheck="fail", colorVectorCheck="pass"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("neutral-check", result["rejectedClaims"])
        self.assertIn("finite-determinant-not-certificate", result["rejectedClaims"])
        self.assertNotIn("color-vector-check", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "convention"},
            {**valid, "extra": True},
            {**valid, "determinantFinite": "true"},
            {**valid, "convention": "column"},
            {**valid, "whitePoint": "D65"},
            {**valid, "neutralCheck": "yes"},
            {**valid, "matrixId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
