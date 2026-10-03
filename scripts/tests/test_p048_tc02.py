"""TC-P048-02 signed dark residuals are not clamped away."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p048_tc02", Path(__file__).resolve().parents[1] / "gates" / "p048_tc02.py"
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
        "captureId": "dark-a",
        "exposureTimeMs": 8,
        "gain": 4,
        "residuals": [-2, 0, 1],
        "structure": "row",
        "clampToZero": False,
    }
    base.update(overrides)
    return base


class TcP04802(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P048-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertIn("below the estimated black level", _MODULE.INTERVENTION)
        self.assertIn("signed statistics", _MODULE.EXPECTED)
        self.assertIn("Clamping residuals to zero", _MODULE.NEGATIVE)

    def test_negative_clamp_fails_and_keeps_signed_values(self):
        result = evaluate(payload(clampToZero=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("clamped-residuals-before-noise", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("residual:-2", result["preservedResults"])
        self.assertIn("signed-min:-2", result["preservedResults"])
        self.assertIn("capture:dark-a", result["preservedResults"])

    def test_repeat_exposure_time_exposes_row_bias(self):
        result = evaluate(payload(exposureTimeMs=16, residuals=[-3, 1], structure="row"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "structured_error")
        self.assertIn("exposure-ms:16", result["preservedResults"])
        self.assertIn("below-black", result["rejectedClaims"])
        self.assertIn("row-bias", result["rejectedClaims"])
        self.assertIn("signed-min:-3", result["preservedResults"])

    def test_repeat_gain_and_independent_dark_capture(self):
        result = evaluate(
            payload(
                captureId="dark-b",
                exposureTimeMs=33,
                gain=16,
                residuals=[-1, 2],
                structure="column",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "structured_error")
        self.assertIn("gain:16", result["preservedResults"])
        self.assertIn("capture:dark-b", result["preservedResults"])
        self.assertIn("column-bias", result["rejectedClaims"])
        self.assertIn("residual:-1", result["preservedResults"])

    def test_unsigned_clean_capture_stays_signed(self):
        result = evaluate(payload(residuals=[0, 1, 2], structure="none"))
        self.assertEqual(result["decision"], "signed_retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("signed-sum:3", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        for item in (None, {}, {**valid, "residuals": []}, {**valid, "clampToZero": 1}):
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
