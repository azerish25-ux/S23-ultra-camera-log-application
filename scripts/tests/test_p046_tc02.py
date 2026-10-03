"""TC-P046-02 signed dark residuals."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p046_tc02", Path(__file__).resolve().parents[1] / "gates" / "p046_tc02.py"
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
        "exposureMs": 10,
        "gain": 100,
        "residuals": [-3, 1, -1],
        "rowBias": 2,
        "columnBias": -1,
        "clampBeforeAnalysis": False,
    }
    base.update(overrides)
    return base


class TcP04602(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P046-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_signed_residuals_and_bias_are_exposed(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "bias_exposed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("residual:0:-3", result["preservedResults"])
        self.assertIn("signed-min:-3", result["preservedResults"])
        self.assertIn("row-bias:2", result["preservedResults"])
        self.assertIn("column-bias:-1", result["preservedResults"])
        self.assertIn("values below the estimated black level", result["openQuestions"])
        self.assertIn("structured row or column bias", result["openQuestions"])
        self.assertIn("signed", _MODULE.EXPECTED)

    def test_exposure_time_repeat_keeps_its_own_residuals(self):
        result = evaluate(payload(captureId="dark-exposure", exposureMs=33, residuals=[-8, 4]))
        self.assertEqual(result["decision"], "bias_exposed")
        self.assertIn("exposure:33", result["preservedResults"])
        self.assertIn("residual:0:-8", result["preservedResults"])
        self.assertNotIn("exposure:10", result["preservedResults"])

    def test_gain_setting_repeat_keeps_the_signed_minimum(self):
        result = evaluate(payload(captureId="dark-gain", gain=400, residuals=[-2], rowBias=0, columnBias=0))
        self.assertEqual(result["decision"], "bias_exposed")
        self.assertIn("gain:400", result["preservedResults"])
        self.assertIn("signed-min:-2", result["preservedResults"])
        self.assertIn("capture:dark-gain", result["preservedResults"])

    def test_independent_dark_capture_is_not_clipped_away(self):
        result = evaluate(
            payload(captureId="dark-b", exposureMs=50, gain=200, residuals=[0, -5], rowBias=0, columnBias=1)
        )
        self.assertEqual(result["decision"], "bias_exposed")
        self.assertIn("capture:dark-b", result["preservedResults"])
        self.assertIn("residual:1:-5", result["preservedResults"])
        self.assertIn("signed-min:-5", result["preservedResults"])

    def test_clamp_before_analysis_fails_and_keeps_the_sign(self):
        result = evaluate(payload(clampBeforeAnalysis=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bias_exposed"})
        self.assertEqual(result["rejectedClaims"], ["clamped-before-analysis"])
        self.assertIn("residual:0:-3", result["preservedResults"])
        self.assertNotIn("residual:0:0", result["preservedResults"])
        self.assertIn("signed-min:-3", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_non_negative_residuals_are_retained_without_a_certificate(self):
        result = evaluate(payload(residuals=[0, 2], rowBias=0, columnBias=0))
        self.assertEqual(result["decision"], "signed_retained")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("signed-min:0", result["preservedResults"])
        self.assertEqual(result["openQuestions"], [])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "residuals"},
            {**valid, "extra": 1},
            {**valid, "residuals": []},
            {**valid, "residuals": [-1, True]},
            {**valid, "exposureMs": 0},
            {**valid, "gain": -4},
            {**valid, "clampBeforeAnalysis": 1},
            {**valid, "captureId": "Dark A"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
