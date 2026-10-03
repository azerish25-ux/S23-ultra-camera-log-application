"""TC-P041-02 signed dark residuals."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p041_tc02", Path(__file__).resolve().parents[1] / "gates" / "p041_tc02.py"
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
        "exposureNs": "10000000",
        "gain": "1",
        "residualMin": "-2.5",
        "rowBias": "0.25",
        "columnBias": "-0.5",
        "clampBeforeAnalysis": False,
    }
    base.update(overrides)
    return base


class TcP04102(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P041-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_signed_residuals_and_bias_stay_visible(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "signed_residuals")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("residualMin:-2.5", result["preservedResults"])
        self.assertIn("rowBias:0.25", result["preservedResults"])
        self.assertIn("columnBias:-0.5", result["preservedResults"])
        self.assertNotIn("residualMin:0", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["structured row or column bias"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_clamping_before_analysis_fails_and_keeps_the_sign(self):
        result = evaluate(payload(clampBeforeAnalysis=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["clamped-residuals"])
        self.assertIn("residualMin:-2.5", result["preservedResults"])
        self.assertIn("columnBias:-0.5", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertNotIn("residualMin:0", result["preservedResults"])

    def test_exposure_time_repeat_preserves_its_own_residual(self):
        result = evaluate(payload(captureId="dark-b", exposureNs="30000000", residualMin="-0.5", rowBias="0", columnBias="0"))
        self.assertEqual(result["decision"], "signed_residuals")
        self.assertIn("exposureNs:30000000", result["preservedResults"])
        self.assertIn("capture:dark-b", result["preservedResults"])
        self.assertIn("residualMin:-0.5", result["preservedResults"])
        self.assertEqual(result["openQuestions"], [])

    def test_gain_repeat_exposes_column_bias(self):
        result = evaluate(payload(captureId="dark-gain", gain="8.5", exposureNs="10000000", rowBias="0", columnBias="0.125"))
        self.assertEqual(result["decision"], "signed_residuals")
        self.assertIn("gain:8.5", result["preservedResults"])
        self.assertIn("columnBias:0.125", result["preservedResults"])
        self.assertIn("structured row or column bias", result["openQuestions"])

    def test_independent_dark_capture_repeat_is_not_clipped(self):
        result = evaluate(
            payload(
                captureId="dark-c",
                exposureNs="8000000",
                gain="2",
                residualMin="-4",
                rowBias="-0.125",
                columnBias="0",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "signed_residuals")
        self.assertIn("capture:dark-c", result["preservedResults"])
        self.assertIn("residualMin:-4", result["preservedResults"])
        self.assertIn("rowBias:-0.125", result["preservedResults"])
        self.assertEqual(_MODULE.INTERVENTION[:9], "Introduce")

    def test_no_structure_is_withheld(self):
        result = evaluate(payload(residualMin="0", rowBias="0", columnBias="0"))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("residualMin:0", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "residualMin": "-2.50"},
            {**valid, "gain": "0"},
            {**valid, "gain": "-1"},
            {**valid, "exposureNs": "0"},
            {**valid, "exposureNs": 10000000},
            {**valid, "clampBeforeAnalysis": "false"},
            {**valid, "captureId": "1dark"},
            {**valid, "rowBias": "NaN"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
