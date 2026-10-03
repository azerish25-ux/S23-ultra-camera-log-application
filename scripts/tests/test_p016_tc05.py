"""TC-P016-05 variable AE range is not fixed cadence."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p016_tc05", Path(__file__).resolve().parents[1] / "gates" / "p016_tc05.py"
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
_ORACLE = ["file-retained", "playback:separate", "cadence:separate"]


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


class TcP01605(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P016-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("not-endurance-certified", result["openQuestions"])
        for token in _ORACLE:
            self.assertIn(token, result["preservedResults"])

    def test_contract_text_is_encoded(self):
        self.assertIn("variable AE range", _MODULE.INTERVENTION)
        self.assertIn("fixed-cadence", _MODULE.EXPECTED)
        self.assertIn("constant container timestamps", _MODULE.NEGATIVE)

    def test_integer_rate_without_fixed_evidence_is_withheld(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["30", _SIZE, *_ORACLE])
        self.assertEqual(result["openQuestions"], [_AE_ONLY, "not-endurance-certified"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("integer" in item and "30" in item for item in result["reasons"]))

    def test_fractional_rate_without_fixed_evidence_is_withheld(self):
        size = "1920x1080"
        result = evaluate(payload(nominalFps="29.97", rateClass="fractional", advertisedSize=size))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["29.97", size, *_ORACLE])
        self.assertEqual(result["openQuestions"], [_AE_ONLY, "not-endurance-certified"])
        self.assertTrue(any("fractional" in item and "29.97" in item for item in result["reasons"]))
        self.assertNotIn("30", result["preservedResults"])

    def test_manual_timing_pending_stays_withheld(self):
        result = evaluate(payload(manualTimingPending=True, nominalFps="24", advertisedSize="1280x720"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"fixed_cadence", "qualified", "allowed"})
        self.assertEqual(result["openQuestions"], [_AE_ONLY, _MANUAL, "not-endurance-certified"])
        self.assertEqual(result["preservedResults"], ["24", "1280x720", *_ORACLE])

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
        self.assertEqual(result["openQuestions"], [_MANUAL, "not-endurance-certified"])
        self.assertEqual(result["preservedResults"], ["24", "1280x720", *_ORACLE])

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
            self.assertTrue(any("constant container timestamps" in item for item in result["reasons"]))

    def test_fixed_rate_evidence_without_manual_pending_is_fixed_cadence(self):
        result = evaluate(
            payload(
                nominalFps="24",
                rateClass="integer",
                fixedRateEvidence=True,
                aeRangeIncludesNominal=False,
                manualTimingPending=False,
                advertisedSize="1920x1080",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "fixed_cadence")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], ["not-endurance-certified"])
        self.assertEqual(result["preservedResults"], ["24", "1920x1080", *_ORACLE])

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
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
