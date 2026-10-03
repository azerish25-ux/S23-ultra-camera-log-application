"""TC-P015-05 variable AE range is not native fixed cadence."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p015_tc05", Path(__file__).resolve().parents[1] / "gates" / "p015_tc05.py"
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
_SIZE = "3840x2160"


def payload(**overrides):
    base = {
        "nominalFps": "30",
        "aeRangeIncludesNominal": True,
        "fixedRateEvidence": False,
        "constantContainerTimestamps": False,
        "manualTimingPending": False,
        "rateClass": "integer",
        "advertisedSize": _SIZE,
    }
    base.update(overrides)
    return base


class TcP01505(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P015-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_contract_text(self):
        self.assertIn("no fixed-rate evidence", _MODULE.INTERVENTION)
        self.assertIn("rate strategy", _MODULE.EXPECTED)
        self.assertIn("constant container timestamps", _MODULE.NEGATIVE)
        self.assertIn("fractional", _MODULE.REPEAT)

    def test_integer_30_ae_range_is_withheld(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["30", "integer", _SIZE])
        self.assertEqual(result["openQuestions"], [_AE_ONLY])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("rate strategy integer nominal 30" in item for item in result["reasons"]))
        self.assertTrue(any("withheld pending measured results" in item for item in result["reasons"]))

    def test_fractional_29_97_ae_range_is_withheld(self):
        size = "1920x1080"
        result = evaluate(payload(nominalFps="29.97", rateClass="fractional", advertisedSize=size))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["29.97", "fractional", size])
        self.assertEqual(result["openQuestions"], [_AE_ONLY])
        self.assertTrue(any("fractional" in item and "29.97" in item for item in result["reasons"]))

    def test_manual_timing_pending_stays_withheld(self):
        result = evaluate(
            payload(
                nominalFps="24",
                fixedRateEvidence=True,
                aeRangeIncludesNominal=False,
                manualTimingPending=True,
                advertisedSize="1280x720",
            )
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"measured", "qualified", "allowed"})
        self.assertEqual(result["openQuestions"], [_MANUAL])
        self.assertEqual(result["preservedResults"], ["24", "integer", "1280x720"])

    def test_constant_timestamps_do_not_upgrade_variable_timing(self):
        for nominal, rate_class in (("30", "integer"), ("23.976", "fractional")):
            result = evaluate(
                payload(
                    nominalFps=nominal,
                    rateClass=rate_class,
                    constantContainerTimestamps=True,
                    fixedRateEvidence=False,
                )
            )
            self.assertEqual(result["decision"], "withheld")
            self.assertNotIn(result["decision"], {"qualified", "allowed", "measured"})
            self.assertIn("constant-timestamps", result["rejectedClaims"])
            self.assertIn(nominal, result["preservedResults"])
            self.assertIn(rate_class, result["preservedResults"])
            self.assertTrue(any("constant container timestamps" in item for item in result["reasons"]))

    def test_fixed_rate_evidence_is_measured_not_qualified(self):
        result = evaluate(
            payload(fixedRateEvidence=True, aeRangeIncludesNominal=False, constantContainerTimestamps=False)
        )
        self.assertEqual(result["decision"], "measured")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["openQuestions"], [])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(_SIZE, result["preservedResults"])
        self.assertTrue(any("not physical cadence certification" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "nominalFps": "30.0"},
            {**valid, "nominalFps": "29.97"},
            {**valid, "rateClass": "fixed"},
            {**valid, "advertisedSize": "3840X2160"},
            {**valid, "fixedRateEvidence": 1},
            {**valid, "manualTimingPending": None},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
