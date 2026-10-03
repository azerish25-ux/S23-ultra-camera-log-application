"""TC-P042-03 matrix convention mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p042_tc03", Path(__file__).resolve().parents[1] / "gates" / "p042_tc03.py"
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
        "matrixId": "cam-m",
        "convention": "transposed",
        "determinant": "1",
        "neutralCheck": "pass",
        "colorCheck": "pass",
    }
    base.update(overrides)
    return base


class TcP04203(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P042-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("Transpose or reverse", _MODULE.INTERVENTION)
        self.assertIn("convention error", _MODULE.EXPECTED)
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A finite determinant alone must not certify a color transform.",
        )

    def test_transposed_matrix_fails_even_when_numbers_look_fine(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["convention:transposed", "neutral-check", "color-vector-check"],
        )
        self.assertIn("determinant:1", result["preservedResults"])
        self.assertIn("matrix:cam-m", result["preservedResults"])
        self.assertIn("convention error transposed", result["reasons"])

    def test_finite_determinant_alone_is_rejected(self):
        result = evaluate(payload(convention="determinant_only", determinant="-3.5"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})
        self.assertEqual(result["rejectedClaims"], ["finite-determinant"])
        self.assertIn("determinant:-3.5", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_repeat_wrong_white_point(self):
        result = evaluate(payload(convention="wrong_white_point", determinant="0.8"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("convention:wrong_white_point", result["rejectedClaims"])
        self.assertIn("neutral-check", result["rejectedClaims"])
        self.assertIn("determinant:0.8", result["preservedResults"])

    def test_repeat_swapped_direction(self):
        result = evaluate(payload(convention="swapped_direction"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("convention:swapped_direction", result["rejectedClaims"])
        self.assertIn("color-vector-check", result["rejectedClaims"])
        self.assertIn("matrix:cam-m", result["preservedResults"])

    def test_duplicated_white_balance_does_not_certify(self):
        result = evaluate(payload(convention="duplicated_white_balance", neutralCheck="fail"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("convention:duplicated_white_balance", result["rejectedClaims"])

    def test_authored_pass_is_withheld(self):
        result = evaluate(payload(convention="authored"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("determinant:1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "determinant": "inf"},
            {**valid, "neutralCheck": "yes"},
            {**valid, "convention": "inverse"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
