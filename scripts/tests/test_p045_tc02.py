"""TC-P045-02 signed dark residuals."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p045_tc02", Path(__file__).resolve().parents[1] / "gates" / "p045_tc02.py"
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
        "captureId": "dark-1",
        "exposure": "1/30",
        "gain": "100",
        "blackLevel": "64",
        "residuals": ["-0.25", "-0.1", "0.02"],
        "biasAxis": "row",
        "clampResiduals": False,
    }
    base.update(overrides)
    return base


class TcP04502(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P045-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_row_bias_exposes_signed_residuals(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "exposed")
        self.assertEqual(result["rejectedClaims"], ["structured-bias:row"])
        self.assertIn("residual:-0.25", result["preservedResults"])
        self.assertIn("signed-min:-0.25", result["preservedResults"])
        self.assertIn("capture:dark-1", result["preservedResults"])
        self.assertIn("exposure:1/30", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_column_bias_is_a_separate_repeat(self):
        result = evaluate(payload(biasAxis="column", captureId="dark-col"))
        self.assertEqual(result["decision"], "exposed")
        self.assertIn("structured-bias:column", result["rejectedClaims"])
        self.assertIn("residual:-0.1", result["preservedResults"])
        self.assertIn("capture:dark-col", result["preservedResults"])

    def test_negative_clamp_fails_and_keeps_the_signed_values(self):
        result = evaluate(payload(clampResiduals=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["clamped-residuals", "hidden-signed-dark"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("residual:-0.25", result["preservedResults"])
        self.assertIn("signed-min:-0.25", result["preservedResults"])
        self.assertNotIn("signed-min:0", result["preservedResults"])

    def test_repeat_shorter_exposure(self):
        result = evaluate(payload(exposure="1/250", biasAxis="none"))
        self.assertEqual(result["decision"], "exposed")
        self.assertIn("exposure:1/250", result["preservedResults"])
        self.assertIn("residual:-0.25", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_repeat_higher_gain(self):
        result = evaluate(payload(gain="1600", captureId="dark-gain"))
        self.assertEqual(result["decision"], "exposed")
        self.assertIn("gain:1600", result["preservedResults"])
        self.assertIn("capture:dark-gain", result["preservedResults"])
        self.assertIn("signed-max:0.02", result["preservedResults"])

    def test_repeat_independent_dark_capture(self):
        result = evaluate(payload(captureId="dark-2", exposure="1/1000", gain="800", biasAxis="column"))
        self.assertEqual(result["decision"], "exposed")
        self.assertIn("capture:dark-2", result["preservedResults"])
        self.assertIn("exposure:1/1000", result["preservedResults"])
        self.assertIn("gain:800", result["preservedResults"])
        self.assertIn("structured-bias:column", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "residuals"},
            {**valid, "extra": True},
            {**valid, "residuals": ["0.1", "0.2"]},
            {**valid, "residuals": ["-0"]},
            {**valid, "clampResiduals": 1},
            {**valid, "biasAxis": "pixel"},
            {**valid, "blackLevel": "-1"},
            {**valid, "exposure": "1 / 30"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
