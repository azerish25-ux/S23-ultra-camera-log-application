"""TC-P009-05 ambiguous timing support."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p009_tc05", Path(__file__).resolve().parents[1] / "gates" / "p009_tc05.py"
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
_RATES = (("30", "integer"), ("29.97", "fractional"))


def timing(**overrides):
    base = {
        "nominalFps": "30",
        "aeRangeIncludesNominal": True,
        "fixedRateEvidence": False,
        "constantContainerTimestamps": False,
        "manualTimingPending": False,
        "rateClass": "integer",
    }
    base.update(overrides)
    return base


class TcP00905(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P009-05")
        self.assertIn(result["decision"], {"withheld", "fixed_cadence"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_integer_and_fractional_variable_ae_withholds_fixed_cadence(self):
        for nominal, rate_class in _RATES:
            result = evaluate(
                timing(
                    nominalFps=nominal,
                    rateClass=rate_class,
                    aeRangeIncludesNominal=True,
                    fixedRateEvidence=False,
                    constantContainerTimestamps=False,
                    manualTimingPending=False,
                )
            )
            self.assertContract(result)
            self.assertEqual(result["decision"], "withheld")
            self.assertIn("native fixed cadence is not certified", result["reasons"])
            self.assertIn(f"{rate_class} nominal {nominal} fps", result["reasons"])
            self.assertEqual(result["rejectedClaims"], [])
            self.assertEqual(result["preservedResults"], [nominal])
            self.assertEqual(result["openQuestions"], ["variable AE range only"])

    def test_constant_container_timestamps_do_not_upgrade_variable_timing(self):
        for nominal, rate_class in _RATES:
            result = evaluate(
                timing(
                    nominalFps=nominal,
                    rateClass=rate_class,
                    aeRangeIncludesNominal=True,
                    fixedRateEvidence=False,
                    constantContainerTimestamps=True,
                    manualTimingPending=False,
                )
            )
            self.assertContract(result)
            self.assertEqual(result["decision"], "withheld")
            self.assertNotIn(result["decision"], {"qualified", "allowed", "fixed_cadence"})
            self.assertIn("native fixed cadence is not certified", result["reasons"])
            self.assertIn("constant container timestamps do not certify native cadence", result["reasons"])
            self.assertEqual(result["rejectedClaims"], ["constant-timestamps"])
            self.assertEqual(result["preservedResults"], [nominal])
            self.assertIn("variable AE range only", result["openQuestions"])

    def test_manual_timing_pending_for_integer_and_fractional_rates(self):
        for nominal, rate_class in _RATES:
            result = evaluate(
                timing(
                    nominalFps=nominal,
                    rateClass=rate_class,
                    aeRangeIncludesNominal=True,
                    fixedRateEvidence=False,
                    constantContainerTimestamps=False,
                    manualTimingPending=True,
                )
            )
            self.assertContract(result)
            self.assertEqual(result["decision"], "withheld")
            self.assertNotEqual(result["decision"], "fixed_cadence")
            self.assertIn("native fixed cadence is not certified", result["reasons"])
            self.assertEqual(result["preservedResults"], [nominal])
            self.assertEqual(
                result["openQuestions"],
                [
                    "variable AE range only",
                    "manual timing awaiting result confirmation",
                ],
            )

    def test_manual_timing_pending_blocks_certification_even_with_fixed_evidence(self):
        result = evaluate(
            timing(
                nominalFps="24",
                rateClass="integer",
                aeRangeIncludesNominal=True,
                fixedRateEvidence=True,
                constantContainerTimestamps=True,
                manualTimingPending=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"fixed_cadence", "qualified", "allowed"})
        self.assertIn("native fixed cadence is not certified", result["reasons"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["24"])
        self.assertEqual(result["openQuestions"], ["manual timing awaiting result confirmation"])
        self.assertNotIn("variable AE range only", result["openQuestions"])

    def test_fixed_rate_evidence_certifies_without_using_container_timestamps(self):
        for timestamps in (False, True):
            for nominal, rate_class in _RATES:
                result = evaluate(
                    timing(
                        nominalFps=nominal,
                        rateClass=rate_class,
                        aeRangeIncludesNominal=True,
                        fixedRateEvidence=True,
                        constantContainerTimestamps=timestamps,
                        manualTimingPending=False,
                    )
                )
                self.assertContract(result)
                self.assertEqual(result["decision"], "fixed_cadence")
                self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})
                self.assertIn("native fixed cadence is certified", result["reasons"])
                self.assertNotIn("native fixed cadence is not certified", result["reasons"])
                self.assertEqual(result["rejectedClaims"], [])
                self.assertEqual(result["preservedResults"], [nominal])
                self.assertEqual(result["openQuestions"], [])

    def test_ae_range_outside_nominal_is_withheld_without_that_question(self):
        result = evaluate(
            timing(
                nominalFps="29.97",
                rateClass="fractional",
                aeRangeIncludesNominal=False,
                fixedRateEvidence=False,
                constantContainerTimestamps=False,
                manualTimingPending=False,
            )
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["openQuestions"], [])
        self.assertEqual(result["preservedResults"], ["29.97"])
        self.assertIn("native fixed cadence is not certified", result["reasons"])

    def test_flag_matrix_never_promotes_timestamps_or_ae_range(self):
        for nominal, rate_class in _RATES:
            for fixed in (False, True):
                for timestamps in (False, True):
                    for pending in (False, True):
                        for ae_includes in (False, True):
                            result = evaluate(
                                timing(
                                    nominalFps=nominal,
                                    rateClass=rate_class,
                                    fixedRateEvidence=fixed,
                                    constantContainerTimestamps=timestamps,
                                    manualTimingPending=pending,
                                    aeRangeIncludesNominal=ae_includes,
                                )
                            )
                            self.assertContract(result)
                            self.assertEqual(result["preservedResults"], [nominal])
                            if fixed and not pending:
                                self.assertEqual(result["decision"], "fixed_cadence")
                            else:
                                self.assertEqual(result["decision"], "withheld")
                                self.assertIn(
                                    "native fixed cadence is not certified",
                                    result["reasons"],
                                )
                            if timestamps and not fixed:
                                self.assertIn("constant-timestamps", result["rejectedClaims"])
                                self.assertNotIn(
                                    result["decision"],
                                    {"qualified", "allowed", "fixed_cadence"},
                                )
                            else:
                                self.assertNotIn("constant-timestamps", result["rejectedClaims"])
                            expected_questions = []
                            if ae_includes and not fixed:
                                expected_questions.append("variable AE range only")
                            if pending:
                                expected_questions.append(
                                    "manual timing awaiting result confirmation"
                                )
                            self.assertEqual(result["openQuestions"], expected_questions)

    def test_invalid_payload_raises(self):
        valid = timing()
        cases = [
            None,
            [],
            {},
            {"nominalFps": "30"},
            {**valid, "extra": True},
            {k: v for k, v in valid.items() if k != "rateClass"},
            {**valid, "nominalFps": 30},
            {**valid, "nominalFps": 29.97},
            {**valid, "nominalFps": ""},
            {**valid, "nominalFps": "30fps"},
            {**valid, "nominalFps": "0"},
            {**valid, "nominalFps": "-30"},
            {**valid, "nominalFps": " 30"},
            {**valid, "aeRangeIncludesNominal": 1},
            {**valid, "aeRangeIncludesNominal": "true"},
            {**valid, "fixedRateEvidence": 0},
            {**valid, "constantContainerTimestamps": "false"},
            {**valid, "manualTimingPending": None},
            {**valid, "rateClass": "Integer"},
            {**valid, "rateClass": "integer|fractional"},
            {**valid, "rateClass": 30},
            {**valid, "rateClass": None},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
