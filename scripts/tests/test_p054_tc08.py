"""TC-P054-08 independent reference disagreement."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p054_tc08", Path(__file__).resolve().parents[1] / "gates" / "p054_tc08.py"
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
        "precision": "fp64",
        "sourceSize": "8x8",
        "seed": "1",
        "oracleKind": "independent",
        "numericDelta": "0",
        "geometricDelta": "0",
        "intentional": False,
        "explanation": "none",
    }
    base.update(overrides)
    return base


class TcP05408(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P054-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_independent_match_is_oracle_agreed(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "oracle-agreed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("fp64", result["preservedResults"])
        self.assertIn("8x8", result["preservedResults"])
        self.assertIn("seed:1", result["preservedResults"])

    def test_negative_copied_oracle_is_not_independent(self):
        result = evaluate(payload(oracleKind="copied-implementation", precision="fp32", seed="7"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["copied-oracle"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("fp32", result["preservedResults"])
        self.assertIn("seed:7", result["preservedResults"])
        self.assertIn("copied-implementation", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "oracle-agreed"})

    def test_repeat_fp64_precision(self):
        result = evaluate(payload(precision="fp64", sourceSize="16x16", seed="2"))
        self.assertEqual(result["decision"], "oracle-agreed")
        self.assertIn("fp64", result["preservedResults"])
        self.assertIn("16x16", result["preservedResults"])
        self.assertIn("seed:2", result["preservedResults"])

    def test_repeat_decimal_precision(self):
        result = evaluate(payload(precision="decimal", sourceSize="3x5", seed="0"))
        self.assertEqual(result["decision"], "oracle-agreed")
        self.assertIn("decimal", result["preservedResults"])
        self.assertIn("3x5", result["preservedResults"])
        self.assertIn("seed:0", result["preservedResults"])

    def test_repeat_source_size_and_seed(self):
        result = evaluate(payload(precision="fp32", sourceSize="32x18", seed="42"))
        self.assertEqual(result["decision"], "oracle-agreed")
        self.assertIn("32x18", result["preservedResults"])
        self.assertIn("seed:42", result["preservedResults"])
        self.assertIn("numeric:0", result["preservedResults"])

    def test_unintended_numeric_and_geometric_mismatch_fail(self):
        numeric = evaluate(payload(numericDelta="0.002", seed="9", sourceSize="8x8"))
        self.assertEqual(numeric["decision"], "rejected")
        self.assertEqual(numeric["rejectedClaims"], ["numeric-mismatch"])
        self.assertIn("numeric:0.002", numeric["preservedResults"])
        self.assertIn("seed:9", numeric["preservedResults"])
        both = evaluate(payload(numericDelta="0.002", geometricDelta="1", precision="decimal"))
        self.assertEqual(both["rejectedClaims"], ["numeric-mismatch", "geometric-mismatch"])
        self.assertIn("geometric:1", both["preservedResults"])
        self.assertIn("decimal", both["preservedResults"])
        self.assertNotIn(both["decision"], {"qualified", "allowed", "oracle-agreed"})

    def test_intentional_difference_is_explained(self):
        result = evaluate(
            payload(
                numericDelta="0.002",
                intentional=True,
                explanation="half-up-tie",
                precision="fp32",
                sourceSize="4x4",
                seed="11",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("numeric-mismatch", result["rejectedClaims"])
        self.assertTrue(any("half-up-tie" in item for item in result["reasons"]))
        self.assertIn("fp32", result["preservedResults"])
        self.assertIn("4x4", result["preservedResults"])
        self.assertIn("seed:11", result["preservedResults"])
        explained = evaluate(
            payload(intentional=True, explanation="half-up-tie", numericDelta="0", geometricDelta="0")
        )
        self.assertEqual(explained["decision"], "explained-difference")
        self.assertEqual(explained["rejectedClaims"], [])
        self.assertTrue(any("half-up-tie" in item for item in explained["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "precision"},
            {**valid, "extra": True},
            {**valid, "precision": "fp16"},
            {**valid, "sourceSize": "08x8"},
            {**valid, "sourceSize": "8"},
            {**valid, "seed": "01"},
            {**valid, "oracleKind": "same"},
            {**valid, "numericDelta": "0.000"},
            {**valid, "intentional": True, "explanation": "none"},
            {**valid, "intentional": False, "explanation": "note"},
            {**valid, "intentional": 0},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
