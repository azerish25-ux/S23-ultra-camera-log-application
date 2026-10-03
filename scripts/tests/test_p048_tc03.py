"""TC-P048-03 a finite determinant does not certify a color transform."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p048_tc03", Path(__file__).resolve().parents[1] / "gates" / "p048_tc03.py"
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
        "determinant": "1",
        "neutralCheck": True,
        "colorVectorCheck": True,
        "whitePoint": "d65",
        "certifyByDeterminant": False,
    }
    base.update(overrides)
    return base


class TcP04803(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P048-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("determinant:1", result["preservedResults"])

    def test_constants(self):
        self.assertIn("Transpose or reverse", _MODULE.INTERVENTION)
        self.assertIn("convention error", _MODULE.EXPECTED)
        self.assertIn("finite determinant", _MODULE.NEGATIVE)

    def test_held_checks_are_not_a_certificate(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "checks_held")
        self.assertEqual(result["rejectedClaims"], [])

    def test_negative_determinant_does_not_certify(self):
        result = evaluate(payload(certifyByDeterminant=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("determinant-not-a-certificate", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("transform:forward", result["preservedResults"])

    def test_repeat_wrong_white_point(self):
        result = evaluate(payload(whitePoint="wrong"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("wrong-white-point", result["rejectedClaims"])
        self.assertIn("white-point:wrong", result["preservedResults"])

    def test_repeat_duplicated_white_balance(self):
        result = evaluate(payload(whitePoint="duplicated_wb"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("duplicated-white-balance", result["rejectedClaims"])
        self.assertIn("determinant:1", result["preservedResults"])

    def test_repeat_swapped_matrix_direction(self):
        result = evaluate(payload(transform="swapped_direction", neutralCheck=False, colorVectorCheck=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("convention-error:swapped_direction", result["rejectedClaims"])
        self.assertIn("neutral-check-failed", result["rejectedClaims"])
        self.assertIn("color-vector-check-failed", result["rejectedClaims"])
        self.assertIn("transform:swapped_direction", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        for item in (None, {}, {**valid, "determinant": "0"}, {**valid, "transform": "inverse"}):
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
