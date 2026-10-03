"""TC-P046-03 matrix convention mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p046_tc03", Path(__file__).resolve().parents[1] / "gates" / "p046_tc03.py"
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
        "matrixId": "cam-to-xyz",
        "convention": "row-camera-to-xyz",
        "determinant": "56",
        "determinantFinite": True,
        "neutralCheck": "pass",
        "colorVectorCheck": "pass",
    }
    base.update(overrides)
    return base


class TcP04603(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P046-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_checks_observed_are_not_a_determinant_certificate(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "checks_observed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("determinant:56", result["preservedResults"])
        self.assertIn("finite determinant was not the certificate", " ".join(result["reasons"]))
        self.assertIn("convention error", _MODULE.EXPECTED)

    def test_transposed_matrix_is_a_convention_error(self):
        result = evaluate(payload(convention="transposed", neutralCheck="pass", colorVectorCheck="pass"))
        self.assertEqual(result["decision"], "convention_error")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "checks_observed"})
        self.assertEqual(
            result["rejectedClaims"],
            ["convention-error:transposed", "neutral-check", "color-vector-check", "finite-determinant"],
        )
        self.assertIn("convention:transposed", result["preservedResults"])
        self.assertIn("determinant:56", result["preservedResults"])

    def test_reversed_matrix_is_a_convention_error(self):
        result = evaluate(payload(convention="reversed", determinant="-56"))
        self.assertEqual(result["decision"], "convention_error")
        self.assertIn("convention-error:reversed", result["rejectedClaims"])
        self.assertIn("determinant:-56", result["preservedResults"])

    def test_wrong_white_point_repeat(self):
        result = evaluate(payload(convention="wrong-white", determinant="7"))
        self.assertEqual(result["decision"], "convention_error")
        self.assertEqual(result["rejectedClaims"][0], "convention-error:wrong-white")
        self.assertIn("finite-determinant", result["rejectedClaims"])
        self.assertIn("determinant:7", result["preservedResults"])

    def test_duplicated_white_balance_repeat(self):
        result = evaluate(payload(convention="duplicated-wb"))
        self.assertEqual(result["decision"], "convention_error")
        self.assertIn("convention-error:duplicated-white-balance", result["rejectedClaims"])
        self.assertIn("neutral-check", result["rejectedClaims"])
        self.assertIn("color-vector-check", result["rejectedClaims"])

    def test_swapped_matrix_direction_repeat(self):
        result = evaluate(payload(convention="swapped-direction", determinant="1"))
        self.assertEqual(result["decision"], "convention_error")
        self.assertIn("convention-error:swapped-direction", result["rejectedClaims"])
        self.assertIn("determinant:1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_finite_determinant_alone_is_rejected(self):
        result = evaluate(payload(neutralCheck="skipped", colorVectorCheck="skipped"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "checks_observed"})
        self.assertEqual(result["rejectedClaims"], ["finite-determinant"])
        self.assertIn("determinant:56", result["preservedResults"])
        self.assertIn("neutral-check:skipped", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_failed_check_does_not_certify(self):
        result = evaluate(payload(colorVectorCheck="fail"))
        self.assertEqual(result["decision"], "checks_failed")
        self.assertIn("color-vector-check", result["rejectedClaims"])
        self.assertIn("finite-determinant", result["rejectedClaims"])
        self.assertIn("color-vector-check:fail", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "convention"},
            {**valid, "extra": True},
            {**valid, "convention": "column"},
            {**valid, "determinant": "56.0"},
            {**valid, "determinant": "056"},
            {**valid, "determinantFinite": 1},
            {**valid, "neutralCheck": "passed"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
