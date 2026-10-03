"""TC-P044-02 signed dark residuals."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p044_tc02", Path(__file__).resolve().parents[1] / "gates" / "p044_tc02.py"
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
        "exposureTimeMs": 10,
        "gain": 100,
        "residuals": [-3, -1, 2],
        "structure": "row",
        "clampToZero": False,
    }
    base.update(overrides)
    return base


class TcP04402(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P044-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_intervention_expected_and_negative(self):
        self.assertIn("below the estimated black level", _MODULE.INTERVENTION)
        self.assertIn("signed statistics", _MODULE.EXPECTED)
        self.assertIn("Clamping residuals to zero", _MODULE.NEGATIVE)

    def test_signed_row_bias_is_exposed_without_clipping(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "structured_error")
        self.assertEqual(result["rejectedClaims"], ["below-black", "row-bias"])
        self.assertIn("signed-min:-3", result["preservedResults"])
        self.assertIn("signed-sum:-2", result["preservedResults"])
        self.assertIn("residual:-3", result["preservedResults"])
        self.assertIn("capture:dark-a", result["preservedResults"])
        self.assertNotIn("signed-min:0", result["preservedResults"])

    def test_exposure_time_repeat_keeps_its_own_identity(self):
        short = evaluate(payload(exposureTimeMs=8, captureId="dark-short"))
        long = evaluate(payload(exposureTimeMs=100, captureId="dark-long", structure="column"))
        self.assertEqual(short["decision"], "structured_error")
        self.assertEqual(long["decision"], "structured_error")
        self.assertIn("exposure-ms:8", short["preservedResults"])
        self.assertIn("exposure-ms:100", long["preservedResults"])
        self.assertIn("column-bias", long["rejectedClaims"])
        self.assertNotIn("exposure-ms:8", long["preservedResults"])

    def test_gain_repeat_does_not_erase_signed_residuals(self):
        low = evaluate(payload(gain=1, structure="none"))
        high = evaluate(payload(gain=16, structure="none", residuals=[-4, 4]))
        self.assertEqual(low["rejectedClaims"], ["below-black"])
        self.assertEqual(high["rejectedClaims"], ["below-black"])
        self.assertIn("gain:1", low["preservedResults"])
        self.assertIn("gain:16", high["preservedResults"])
        self.assertIn("signed-min:-4", high["preservedResults"])
        self.assertIn("residual:4", high["preservedResults"])

    def test_independent_dark_captures_stay_separate(self):
        first = evaluate(payload(captureId="dark-a"))
        second = evaluate(payload(captureId="dark-b", residuals=[1, 1], structure="none"))
        self.assertIn("capture:dark-a", first["preservedResults"])
        self.assertEqual(second["decision"], "signed_retained")
        self.assertEqual(second["rejectedClaims"], [])
        self.assertIn("capture:dark-b", second["preservedResults"])
        self.assertIn("signed-min:1", second["preservedResults"])

    def test_negative_clamp_fails_and_keeps_the_signed_minimum(self):
        result = evaluate(payload(clampToZero=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "structured_error"})
        self.assertEqual(result["rejectedClaims"], ["clamped-residuals-before-noise"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("signed-min:-3", result["preservedResults"])
        self.assertIn("residual:-1", result["preservedResults"])
        self.assertNotIn("signed-min:0", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "residuals"},
            {**valid, "extra": True},
            {**valid, "residuals": []},
            {**valid, "residuals": [-1, True]},
            {**valid, "exposureTimeMs": 0},
            {**valid, "gain": False},
            {**valid, "structure": "pixel"},
            {**valid, "clampToZero": "yes"},
            {**valid, "captureId": " "},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
