"""TC-P013-05 variable AE range is not fixed cadence."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p013_tc05", Path(__file__).resolve().parents[1] / "gates" / "p013_tc05.py"
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
_WITHHELD = "native fixed-cadence certification withheld pending measured results"
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


class TcP01305(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P013-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"withheld", "fixed_cadence"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_integer_30_ae_range_is_withheld(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["30", _SIZE])
        self.assertIn(_AE_ONLY, result["openQuestions"])
        self.assertIn(_WITHHELD, result["openQuestions"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("integer" in item and "30" in item for item in result["reasons"]))

    def test_fractional_29_97_ae_range_is_withheld(self):
        size = "1920x1080"
        result = evaluate(
            payload(nominalFps="29.97", rateClass="fractional", advertisedSize=size)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["29.97", size])
        self.assertIn(_AE_ONLY, result["openQuestions"])
        self.assertTrue(any("fractional" in item and "29.97" in item for item in result["reasons"]))
        self.assertNotIn("30", result["preservedResults"])

    def test_manual_timing_pending_stays_withheld(self):
        result = evaluate(payload(manualTimingPending=True, nominalFps="24"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotEqual(result["decision"], "fixed_cadence")
        self.assertIn(_MANUAL, result["openQuestions"])
        self.assertIn("24", result["preservedResults"])
        self.assertIn(_SIZE, result["preservedResults"])

    def test_manual_pending_blocks_fixed_cadence_even_with_evidence(self):
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
        self.assertNotIn(result["decision"], {"fixed_cadence", "qualified", "allowed"})
        self.assertIn(_MANUAL, result["openQuestions"])
        self.assertEqual(result["preservedResults"], ["24", "1280x720"])

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
            self.assertNotIn(result["decision"], {"qualified", "allowed", "fixed_cadence"})
            self.assertIn("constant-timestamps", result["rejectedClaims"])
            self.assertIn(nominal, result["preservedResults"])
            self.assertIn(_SIZE, result["preservedResults"])
            self.assertTrue(any("constant container timestamps" in item for item in result["reasons"]))

    def test_fixed_rate_evidence_without_manual_pending_is_not_qualified(self):
        result = evaluate(
            payload(fixedRateEvidence=True, aeRangeIncludesNominal=False, nominalFps="24")
        )
        self.assertEqual(result["decision"], "fixed_cadence")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["openQuestions"], [])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["24", _SIZE])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "nominalFps": "30.0"},
            {**valid, "nominalFps": "29.97"},
            {**valid, "rateClass": "fractional"},
            {**valid, "nominalFps": "29.970", "rateClass": "fractional"},
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
