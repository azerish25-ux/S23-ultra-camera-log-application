"""TC-P052-08 independent reference disagreement."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p052_tc08", Path(__file__).resolve().parents[1] / "gates" / "p052_tc08.py"
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
        "precision": "f32",
        "sourceSize": 8,
        "seed": "seed-1",
        "independentOracle": True,
        "intentional": False,
        "explained": False,
        "numericMismatch": False,
        "geometricMismatch": False,
    }
    base.update(overrides)
    return base


class TcP05208(unittest.TestCase):
    def test_independent_match_is_not_qualification(self):
        result = evaluate(payload())
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P052-08")
        self.assertEqual(result["decision"], "matched")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("precision:f32", result["preservedResults"])
        self.assertIn("size:8", result["preservedResults"])
        self.assertIn("seed:seed-1", result["preservedResults"])
        self.assertIn("independent:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_copied_oracle_keeps_precision(self):
        result = evaluate(payload(independentOracle=False, numericMismatch=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("copied-oracle", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("precision:f32", result["preservedResults"])
        self.assertIn("independent:false", result["preservedResults"])
        self.assertIn("size:8", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "matched"})

    def test_repeat_f64_unintended_numeric(self):
        result = evaluate(payload(precision="f64", sourceSize=16, seed="seed-2", numericMismatch=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unintended-numeric", result["rejectedClaims"])
        self.assertIn("precision:f64", result["preservedResults"])
        self.assertIn("size:16", result["preservedResults"])
        self.assertIn("seed:seed-2", result["preservedResults"])

    def test_repeat_decimal_explained_difference(self):
        result = evaluate(
            payload(
                precision="decimal",
                sourceSize=32,
                seed="seed-3",
                intentional=True,
                explained=True,
                geometricMismatch=True,
            )
        )
        self.assertEqual(result["decision"], "explained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("precision:decimal", result["preservedResults"])
        self.assertIn("size:32", result["preservedResults"])
        self.assertIn("geometric-mismatch:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_unexplained_intentional_difference_fails(self):
        result = evaluate(payload(precision="f32", intentional=True, explained=False, numericMismatch=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unexplained-difference", result["rejectedClaims"])
        self.assertIn("numeric-mismatch:true", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "precision"},
            {**valid, "extra": True},
            {**valid, "precision": "f16"},
            {**valid, "independentOracle": "true"},
            {**valid, "sourceSize": 0},
            {**valid, "seed": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
