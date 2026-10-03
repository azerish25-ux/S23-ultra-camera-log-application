"""TC-P011-05 variable AE inclusion is not native cadence."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p011_tc05", Path(__file__).resolve().parents[1] / "gates" / "p011_tc05.py"
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
_AE_ONLY = "variable AE range only"
_MANUAL = "manual timing awaiting result confirmation"


def rate(numerator, denominator=1):
    return {"numerator": numerator, "denominator": denominator}


def payload(**overrides):
    base = {
        "nominal": rate(24),
        "aeMin": rate(15),
        "aeMax": rate(30),
        "fixedRateEvidence": False,
        "constantContainerTimestamps": False,
        "manualTimingPending": False,
        "rateClass": "integer",
    }
    base.update(overrides)
    return base


class TcP01105(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P011-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native_fixed_24"})
        self.assertTrue(result["reasons"])

    def test_encodes_intervention_expected_and_negative(self):
        self.assertIn("no fixed-rate evidence", _MODULE.INTERVENTION)
        self.assertIn("withhold native fixed-cadence", _MODULE.EXPECTED)
        self.assertIn("constant container timestamps", _MODULE.NEGATIVE)

    def test_integer_24_inside_15_to_30_is_withheld(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["24/1", "ae:15/1-30/1"])
        self.assertEqual(result["openQuestions"], [_AE_ONLY])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("not rounded" in item and "30/1" in item for item in result["reasons"]))
        self.assertNotIn("ae:15/1-24/1", result["preservedResults"])

    def test_fractional_24000_1001_is_withheld_without_rounding(self):
        result = evaluate(
            payload(nominal=rate(24000, 1001), rateClass="fractional")
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["24000/1001", "ae:15/1-30/1"])
        self.assertEqual(result["openQuestions"], [_AE_ONLY])
        self.assertTrue(any("fractional" in item and "24000/1001" in item for item in result["reasons"]))
        self.assertNotIn("24/1", result["preservedResults"])

    def test_manual_timing_pending_stays_open_even_with_fixed_evidence(self):
        pending = evaluate(payload(manualTimingPending=True))
        self.assertEqual(pending["decision"], "withheld")
        self.assertEqual(pending["openQuestions"], [_AE_ONLY, _MANUAL])
        blocked = evaluate(
            payload(fixedRateEvidence=True, manualTimingPending=True, nominal=rate(30))
        )
        self.assertEqual(blocked["decision"], "withheld")
        self.assertNotIn(blocked["decision"], {"fixed_cadence", "qualified", "allowed"})
        self.assertIn(_MANUAL, blocked["openQuestions"])
        self.assertEqual(blocked["preservedResults"], ["30/1", "ae:15/1-30/1"])

    def test_constant_timestamps_do_not_upgrade_variable_timing(self):
        for nominal, rate_class in ((rate(24), "integer"), (rate(30000, 1001), "fractional")):
            result = evaluate(
                payload(
                    nominal=nominal,
                    rateClass=rate_class,
                    constantContainerTimestamps=True,
                    fixedRateEvidence=False,
                )
            )
            with self.subTest(nominal=nominal):
                self.assertEqual(result["decision"], "withheld")
                self.assertNotIn(result["decision"], {"qualified", "allowed", "fixed_cadence"})
                self.assertIn("constant-timestamps", result["rejectedClaims"])
                self.assertIn(f"{nominal['numerator']}/{nominal['denominator']}", result["preservedResults"])
                self.assertIn("ae:15/1-30/1", result["preservedResults"])
                self.assertTrue(
                    any("constant container timestamps" in item for item in result["reasons"])
                )

    def test_fixed_rate_evidence_without_manual_pending_is_fixed_cadence(self):
        result = evaluate(payload(fixedRateEvidence=True, constantContainerTimestamps=False))
        self.assertEqual(result["decision"], "fixed_cadence")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], [])
        self.assertEqual(result["preservedResults"], ["24/1", "ae:15/1-30/1"])

    def test_timestamps_are_rejected_even_when_fixed_evidence_exists(self):
        result = evaluate(payload(fixedRateEvidence=True, constantContainerTimestamps=True))
        self.assertEqual(result["decision"], "fixed_cadence")
        self.assertEqual(result["rejectedClaims"], ["constant-timestamps"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "nominal": rate(24, 1), "rateClass": "fractional"},
            {**valid, "nominal": rate(24000, 1001), "rateClass": "integer"},
            {**valid, "nominal": {"numerator": 48, "denominator": 2}},
            {**valid, "aeMin": rate(30), "aeMax": rate(15)},
            {**valid, "fixedRateEvidence": 1},
            {**valid, "rateClass": "fixed"},
            {**valid, "manualTimingPending": None},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
