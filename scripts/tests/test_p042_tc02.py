"""TC-P042-02 signed dark residuals."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p042_tc02", Path(__file__).resolve().parents[1] / "gates" / "p042_tc02.py"
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
        "residuals": ["-2", "1", "-4", "3"],
        "structure": "column",
        "repeat": "exposure",
        "clamp": False,
        "exposureNs": "10000000",
        "gain": "1",
        "captureId": "dark-a",
    }
    base.update(overrides)
    return base


class TcP04202(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P042-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Clamping residuals to zero before noise analysis must fail.",
        )
        self.assertIn("signed", _MODULE.EXPECTED)
        self.assertIn("black level", _MODULE.INTERVENTION)

    def test_signed_sum_stays_negative(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "signed_retained")
        self.assertIn("signed-sum:-2", result["preservedResults"])
        self.assertIn("residual:-4", result["preservedResults"])
        self.assertIn("column-bias", result["rejectedClaims"])
        self.assertNotIn("signed-sum:4", result["preservedResults"])
        self.assertIn("exposure:10000000ns", result["preservedResults"])

    def test_clamp_is_rejected_and_does_not_erase_the_signed_sum(self):
        result = evaluate(payload(clamp=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "signed_retained"})
        self.assertEqual(result["rejectedClaims"], ["clamped-residuals"])
        self.assertIn("signed-sum:-2", result["preservedResults"])
        self.assertIn("residual:-2", result["preservedResults"])
        self.assertNotIn("signed-sum:4", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_repeat_exposure_keeps_capture_identity(self):
        result = evaluate(payload(repeat="exposure", exposureNs="20000000", gain="1"))
        self.assertEqual(result["decision"], "signed_retained")
        self.assertIn("repeat:exposure", result["preservedResults"])
        self.assertIn("exposure:20000000ns", result["preservedResults"])
        self.assertIn("capture:dark-a", result["preservedResults"])

    def test_repeat_gain_keeps_the_signed_inventory(self):
        result = evaluate(payload(repeat="gain", gain="4", structure="row"))
        self.assertEqual(result["decision"], "signed_retained")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("repeat:gain", result["preservedResults"])
        self.assertIn("gain:4", result["preservedResults"])
        self.assertIn("row-bias", result["rejectedClaims"])
        self.assertIn("signed-sum:-2", result["preservedResults"])

    def test_repeat_independent_capture_without_structure_still_signs(self):
        result = evaluate(
            payload(repeat="independent_capture", structure="none", captureId="dark-b")
        )
        self.assertEqual(result["decision"], "signed_retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("capture:dark-b", result["preservedResults"])
        self.assertIn("signed-sum:-2", result["preservedResults"])

    def test_non_negative_residuals_are_withheld(self):
        result = evaluate(payload(residuals=["1", "2"], structure="none"))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("signed-sum:3", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "residuals": []},
            {**valid, "residuals": [-2]},
            {**valid, "clamp": 1},
            {**valid, "gain": "4.0"},
            {**valid, "repeat": "iso"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
