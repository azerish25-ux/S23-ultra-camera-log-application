"""TC-P043-02 signed dark residuals."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p043_tc02", Path(__file__).resolve().parents[1] / "gates" / "p043_tc02.py"
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
        "exposureNs": 10000000,
        "gain": "1",
        "blackLevel": 64,
        "sample": 60,
        "biasAxis": "row",
        "bias": 2,
        "clampResiduals": False,
    }
    base.update(overrides)
    return base


class TcP04302(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P043-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("signed:-4", result["preservedResults"])
        self.assertNotIn("signed:0", result["preservedResults"])

    def test_row_bias_below_black_is_exposed(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "structured_error")
        self.assertEqual(result["rejectedClaims"], ["below-black", "row-bias"])
        self.assertIn("capture:dark-a", result["preservedResults"])
        self.assertIn("exposureNs:10000000", result["preservedResults"])
        self.assertIn("gain:1", result["preservedResults"])
        self.assertIn("bias:row:2", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_repeat_exposure_keeps_the_signed_residual(self):
        result = evaluate(payload(exposureNs=20000000))
        self.assertContract(result)
        self.assertEqual(result["decision"], "structured_error")
        self.assertIn("exposureNs:20000000", result["preservedResults"])
        self.assertIn("signed:-4", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_gain_keeps_the_signed_residual(self):
        result = evaluate(payload(gain="4"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "structured_error")
        self.assertIn("gain:4", result["preservedResults"])
        self.assertIn("signed:-4", result["preservedResults"])
        self.assertIn("below-black", result["rejectedClaims"])

    def test_independent_dark_capture_exposes_column_bias(self):
        result = evaluate(payload(captureId="dark-b", biasAxis="column", bias=-1))
        self.assertContract(result)
        self.assertEqual(result["decision"], "structured_error")
        self.assertIn("capture:dark-b", result["preservedResults"])
        self.assertIn("bias:column:-1", result["preservedResults"])
        self.assertIn("column-bias", result["rejectedClaims"])
        self.assertIn("signed:-4", result["preservedResults"])

    def test_clamping_residuals_fails_and_keeps_the_signed_value(self):
        result = evaluate(payload(clampResiduals=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "structured_error"})
        self.assertIn("residuals-clamped", result["rejectedClaims"])
        self.assertIn("below-black", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("signed:-4", result["preservedResults"])
        self.assertNotIn("signed:0", result["preservedResults"])

    def test_clean_residual_is_recorded_not_qualified(self):
        result = evaluate(payload(sample=64, biasAxis="none", bias=0))
        self.assertEqual(result["decision"], "residuals_recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("signed:0", result["preservedResults"])
        self.assertIn("capture:dark-a", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "biasAxis": "pixel"},
            {**valid, "biasAxis": "none", "bias": 1},
            {**valid, "exposureNs": 0},
            {**valid, "gain": "1.0"},
            {**valid, "clampResiduals": 1},
            {**valid, "sample": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
