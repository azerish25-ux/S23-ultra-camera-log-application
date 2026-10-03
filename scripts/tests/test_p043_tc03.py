"""TC-P043-03 matrix convention mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p043_tc03", Path(__file__).resolve().parents[1] / "gates" / "p043_tc03.py"
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
        "matrixId": "cam-rgb",
        "determinant": "1.2",
        "finite": True,
        "fault": "none",
        "neutralCheck": True,
        "colorVectorCheck": True,
        "certifyFromDeterminant": False,
    }
    base.update(overrides)
    return base


class TcP04303(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P043-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("matrix:cam-rgb", result["preservedResults"])
        self.assertIn("determinant:1.2", result["preservedResults"])

    def test_finite_determinant_does_not_certify(self):
        result = evaluate(payload(certifyFromDeterminant=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "convention_checked"})
        self.assertIn("determinant-certificate", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("determinant:1.2", result["preservedResults"])

    def test_transposed_matrix_names_the_convention_error(self):
        result = evaluate(payload(fault="transposed", neutralCheck=False, colorVectorCheck=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["convention-error:transposed"])
        self.assertIn("convention error transposed", result["reasons"])
        self.assertIn("neutral check failed", result["reasons"])
        self.assertIn("color-vector check failed", result["reasons"])
        self.assertIn("fault:transposed", result["preservedResults"])

    def test_wrong_white_point_is_a_convention_error(self):
        result = evaluate(payload(fault="wrong-white", neutralCheck=False, colorVectorCheck=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("convention-error:wrong-white", result["rejectedClaims"])
        self.assertIn("determinant:1.2", result["preservedResults"])
        self.assertIn("convention error wrong-white", result["reasons"])

    def test_duplicated_white_balance_is_a_convention_error(self):
        result = evaluate(payload(fault="duplicated-wb", neutralCheck=False, colorVectorCheck=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["convention-error:duplicated-wb"])
        self.assertIn("fault:duplicated-wb", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_swapped_matrix_direction_is_a_convention_error(self):
        result = evaluate(payload(fault="swapped-direction", neutralCheck=False, colorVectorCheck=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("convention-error:swapped-direction", result["rejectedClaims"])
        self.assertIn("matrix:cam-rgb", result["preservedResults"])
        self.assertIn("color-vector check failed", result["reasons"])

    def test_ignored_passing_checks_stay_rejected(self):
        result = evaluate(payload(fault="reversed", neutralCheck=True, colorVectorCheck=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("convention-error:reversed", result["rejectedClaims"])
        self.assertIn("neutral-check-ignored", result["rejectedClaims"])
        self.assertIn("color-vector-check-ignored", result["rejectedClaims"])
        self.assertIn("determinant:1.2", result["preservedResults"])

    def test_clean_checks_are_not_qualification(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "convention_checked")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("fault:none", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "finite": False},
            {**valid, "determinant": "1.20"},
            {**valid, "fault": "transpose"},
            {**valid, "neutralCheck": "true"},
            {**valid, "matrixId": " "},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
