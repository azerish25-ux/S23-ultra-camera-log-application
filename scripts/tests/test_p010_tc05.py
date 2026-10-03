"""TC-P010-05 variable AE range is not fixed cadence."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p010_tc05", Path(__file__).resolve().parents[1] / "gates" / "p010_tc05.py"
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


class TcP01005(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P010-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def assertSizePreserved(self, result, size=_SIZE):
        self.assertIn(size, result["preservedResults"])

    def test_integer_30_ae_range_is_withheld(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("30", result["preservedResults"])
        self.assertSizePreserved(result)
        self.assertEqual(result["preservedResults"], ["30", _SIZE])
        self.assertEqual(result["openQuestions"], [_AE_ONLY])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("integer" in item and "30" in item for item in result["reasons"]))
        self.assertNotIn("29.97", " ".join(result["reasons"]))

    def test_fractional_29_97_ae_range_is_withheld(self):
        size = "1920x1080"
        result = evaluate(
            payload(nominalFps="29.97", rateClass="fractional", advertisedSize=size)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["29.97", size])
        self.assertSizePreserved(result, size)
        self.assertEqual(result["openQuestions"], [_AE_ONLY])
        self.assertTrue(any("fractional" in item and "29.97" in item for item in result["reasons"]))
        self.assertNotIn("30", result["preservedResults"])
        joined = " ".join(result["reasons"] + result["preservedResults"])
        self.assertNotIn("30", joined)

    def test_manual_timing_pending_stays_open(self):
        result = evaluate(payload(manualTimingPending=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotEqual(result["decision"], "fixed_cadence")
        self.assertEqual(result["openQuestions"], [_AE_ONLY, _MANUAL])
        self.assertIn("30", result["preservedResults"])
        self.assertSizePreserved(result)
        self.assertTrue(any(_MANUAL == item for item in result["openQuestions"]))

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
        self.assertEqual(result["openQuestions"], [_MANUAL])
        self.assertEqual(result["preservedResults"], ["24", "1280x720"])
        self.assertSizePreserved(result, "1280x720")

    def test_constant_timestamps_do_not_upgrade_variable_timing(self):
        for nominal, rate_class in (("30", "integer"), ("29.97", "fractional")):
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
            self.assertSizePreserved(result)
            self.assertTrue(
                any("constant container timestamps" in item for item in result["reasons"])
            )

    def test_fixed_rate_evidence_without_manual_pending_is_fixed_cadence(self):
        for nominal, rate_class, size in (
            ("30", "integer", _SIZE),
            ("29.97", "fractional", "4096x2160"),
        ):
            result = evaluate(
                payload(
                    nominalFps=nominal,
                    rateClass=rate_class,
                    fixedRateEvidence=True,
                    aeRangeIncludesNominal=True,
                    constantContainerTimestamps=False,
                    manualTimingPending=False,
                    advertisedSize=size,
                )
            )
            self.assertEqual(result["decision"], "fixed_cadence")
            self.assertEqual(result["openQuestions"], [])
            self.assertEqual(result["rejectedClaims"], [])
            self.assertEqual(result["preservedResults"], [nominal, size])
            self.assertSizePreserved(result, size)
            self.assertTrue(result["reasons"])

    def test_constant_timestamps_are_rejected_even_when_fixed_evidence_exists(self):
        result = evaluate(
            payload(fixedRateEvidence=True, constantContainerTimestamps=True, aeRangeIncludesNominal=False)
        )
        self.assertEqual(result["decision"], "fixed_cadence")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["constant-timestamps"])
        self.assertSizePreserved(result)
        self.assertIn("30", result["preservedResults"])

    def test_no_ae_inclusion_and_no_evidence_is_withheld_without_ae_question(self):
        result = evaluate(payload(aeRangeIncludesNominal=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["openQuestions"], [])
        self.assertEqual(result["preservedResults"], ["30", _SIZE])

    def test_advertised_size_is_preserved_in_every_decision(self):
        variants = [
            payload(),
            payload(nominalFps="29.97", rateClass="fractional"),
            payload(manualTimingPending=True),
            payload(constantContainerTimestamps=True),
            payload(fixedRateEvidence=True, aeRangeIncludesNominal=False),
            payload(fixedRateEvidence=True, manualTimingPending=True, advertisedSize="720x480"),
        ]
        for item in variants:
            result = evaluate(item)
            self.assertContract(result)
            self.assertIn(item["advertisedSize"], result["preservedResults"])
            self.assertIn(item["nominalFps"], result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "nominalFps"},
            {**valid, "extra": True},
            {**valid, "nominalFps": 30},
            {**valid, "nominalFps": "30.0"},
            {**valid, "nominalFps": "029"},
            {**valid, "nominalFps": ""},
            {**valid, "nominalFps": "29.97"},
            {**valid, "nominalFps": "29.97", "rateClass": "integer"},
            {**valid, "rateClass": "fractional"},
            {**valid, "nominalFps": "29.970", "rateClass": "fractional"},
            {**valid, "nominalFps": "30.0", "rateClass": "fractional"},
            {**valid, "nominalFps": "29.", "rateClass": "fractional"},
            {**valid, "rateClass": "Integer"},
            {**valid, "rateClass": "fixed"},
            {**valid, "advertisedSize": "3840X2160"},
            {**valid, "advertisedSize": "3840x"},
            {**valid, "advertisedSize": "03840x2160"},
            {**valid, "advertisedSize": 3840},
            {**valid, "aeRangeIncludesNominal": "true"},
            {**valid, "fixedRateEvidence": 1},
            {**valid, "constantContainerTimestamps": 0},
            {**valid, "manualTimingPending": None},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
