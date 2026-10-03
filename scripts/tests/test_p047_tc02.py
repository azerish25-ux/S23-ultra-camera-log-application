"""TC-P047-02 signed dark residuals are not clamped away."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p047_tc02", Path(__file__).resolve().parents[1] / "gates" / "p047_tc02.py"
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
        "exposureTime": "0.01",
        "gain": "4",
        "captureId": "dark-a",
        "residualMin": "-0.004",
        "rowBias": "0.002",
        "columnBias": "-0.001",
        "clampResidualsToZero": False,
    }
    base.update(overrides)
    return base


class TcP04702(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P047-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("residualMin:-0.004", result["preservedResults"])

    def test_constants(self):
        self.assertIn("black level", _MODULE.INTERVENTION)
        self.assertIn("signed statistics", _MODULE.EXPECTED)
        self.assertIn("Clamping residuals", _MODULE.NEGATIVE)

    def test_short_exposure_keeps_signed_structure(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "signed_retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["openQuestions"],
            ["below-black:-0.004", "row-bias:0.002", "column-bias:-0.001"],
        )
        self.assertIn("exposure:0.01", result["preservedResults"])
        self.assertIn("gain:4", result["preservedResults"])
        self.assertIn("capture:dark-a", result["preservedResults"])
        self.assertNotIn("residualMin:0", result["preservedResults"])

    def test_longer_exposure_and_higher_gain_repeat(self):
        result = evaluate(payload(exposureTime="0.5", gain="16", captureId="dark-b"))
        self.assertEqual(result["decision"], "signed_retained")
        self.assertIn("exposure:0.5", result["preservedResults"])
        self.assertIn("gain:16", result["preservedResults"])
        self.assertIn("capture:dark-b", result["preservedResults"])
        self.assertIn("residualMin:-0.004", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_independent_dark_capture_keeps_its_bias(self):
        result = evaluate(
            payload(
                exposureTime="0.02",
                gain="8",
                captureId="dark-c",
                residualMin="-0.01",
                rowBias="0",
                columnBias="0.003",
            )
        )
        self.assertEqual(result["decision"], "signed_retained")
        self.assertEqual(result["openQuestions"], ["below-black:-0.01", "column-bias:0.003"])
        self.assertIn("rowBias:0", result["preservedResults"])
        self.assertIn("capture:dark-c", result["preservedResults"])

    def test_clamping_to_zero_fails_and_keeps_the_signed_value(self):
        for exposure, gain, capture in (("0.01", "4", "dark-a"), ("1", "1", "dark-d")):
            result = evaluate(
                payload(
                    exposureTime=exposure,
                    gain=gain,
                    captureId=capture,
                    clampResidualsToZero=True,
                )
            )
            self.assertEqual(result["decision"], "rejected")
            self.assertEqual(result["rejectedClaims"], ["clamped-residuals"])
            self.assertIn(_MODULE.NEGATIVE, result["reasons"])
            self.assertIn("residualMin:-0.004", result["preservedResults"])
            self.assertNotIn("residualMin:0", result["preservedResults"])
            self.assertIn("below-black:-0.004", result["openQuestions"])
            self.assertNotIn(result["decision"], {"qualified", "allowed", "signed_retained"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "residualMin": "-0"},
            {**valid, "residualMin": "-0.0040"},
            {**valid, "exposureTime": "0"},
            {**valid, "clampResidualsToZero": 1},
            {k: v for k, v in valid.items() if k != "rowBias"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
