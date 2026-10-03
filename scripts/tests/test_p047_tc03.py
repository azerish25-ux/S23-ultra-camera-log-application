"""TC-P047-03 a finite determinant does not certify a color convention."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p047_tc03", Path(__file__).resolve().parents[1] / "gates" / "p047_tc03.py"
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
        "matrixId": "matrix-a",
        "convention": "row-major",
        "determinantFinite": True,
        "neutralCheck": "pass",
        "colorVectorCheck": "pass",
    }
    base.update(overrides)
    return base


class TcP04703(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P047-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("matrix:matrix-a", result["preservedResults"])

    def test_constants(self):
        self.assertIn("Transpose or reverse", _MODULE.INTERVENTION)
        self.assertIn("convention error", _MODULE.EXPECTED)
        self.assertIn("finite determinant", _MODULE.NEGATIVE)

    def test_row_major_hold_is_not_certification(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "convention_held")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("convention:row-major", result["preservedResults"])
        self.assertIn("reported-neutral:pass", result["preservedResults"])

    def test_transposed_and_reversed_fail_both_checks(self):
        for convention in ("transposed", "reversed"):
            result = evaluate(
                payload(
                    convention=convention,
                    determinantFinite=True,
                    neutralCheck="pass",
                    colorVectorCheck="pass",
                )
            )
            self.assertEqual(result["decision"], "rejected")
            self.assertEqual(
                result["rejectedClaims"],
                [
                    "convention-error:" + convention,
                    "neutral-check-failed",
                    "color-vector-check-failed",
                ],
            )
            self.assertIn(_MODULE.NEGATIVE, result["reasons"])
            self.assertIn("convention:" + convention, result["preservedResults"])
            self.assertIn("determinantFinite:true", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed", "convention_held"})

    def test_wrong_white_point_repeat(self):
        result = evaluate(payload(convention="wrong-white-point"))
        self.assertContract(result)
        self.assertIn("convention-error:wrong-white-point", result["rejectedClaims"])
        self.assertIn("neutral-check-failed", result["rejectedClaims"])
        self.assertIn("color-vector-check-failed", result["rejectedClaims"])

    def test_duplicated_white_balance_and_swapped_direction_repeat(self):
        for convention in ("duplicated-white-balance", "swapped-direction"):
            result = evaluate(payload(convention=convention, determinantFinite=True))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn("convention-error:" + convention, result["rejectedClaims"])
            self.assertIn("independent neutral and color-vector checks failed", result["reasons"])
            self.assertIn("matrix:matrix-a", result["preservedResults"])

    def test_row_major_check_failure_is_specific(self):
        result = evaluate(payload(neutralCheck="fail", colorVectorCheck="pass"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["neutral-check-failed"])
        self.assertNotIn("convention-error:row-major", result["rejectedClaims"])
        self.assertIn("reported-color:pass", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "convention": "column-major"},
            {**valid, "determinantFinite": 1},
            {**valid, "neutralCheck": "ok"},
            {k: v for k, v in valid.items() if k != "matrixId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
