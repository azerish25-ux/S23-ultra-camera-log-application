"""TC-P056-08 an independent oracle is not a copy of the implementation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p056_tc08", Path(__file__).resolve().parents[1] / "gates" / "p056_tc08.py"
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
        "precision": "decimal",
        "sourceSize": "4x4",
        "seed": "s0",
        "oracleCopied": False,
        "numericMismatch": False,
        "geometricMismatch": False,
        "intentionalDifference": False,
        "differenceNote": "",
    }
    base.update(overrides)
    return base


class TcP05608(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P056-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_decimal_and_integer_precisions_stay_withheld(self):
        for precision, size, seed in (
            ("decimal", "4x4", "s0"),
            ("integer", "8x2", "seed-b"),
        ):
            result = evaluate(payload(precision=precision, sourceSize=size, seed=seed))
            self.assertContract(result)
            self.assertEqual(result["decision"], "withheld")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(f"precision:{precision}", result["preservedResults"])
            self.assertIn(f"size:{size}", result["preservedResults"])
            self.assertIn(f"seed:{seed}", result["preservedResults"])

    def test_binary32_seed_is_preserved_when_withheld(self):
        result = evaluate(payload(precision="binary32", sourceSize="16x16", seed="a1"))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("precision:binary32", result["preservedResults"])
        self.assertIn("seed:a1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_copied_oracle_is_not_independent(self):
        result = evaluate(payload(oracleCopied=True, precision="integer", seed="copy"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["copied-oracle"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("precision:integer", result["preservedResults"])
        self.assertIn("seed:copy", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld", "explained"})

    def test_unintended_numeric_and_geometric_mismatches_fail(self):
        numeric = evaluate(payload(numericMismatch=True, sourceSize="3x5"))
        geometric = evaluate(payload(geometricMismatch=True, sourceSize="2x2", seed="g"))
        self.assertEqual(numeric["decision"], "rejected")
        self.assertEqual(numeric["rejectedClaims"], ["numeric-mismatch"])
        self.assertIn("size:3x5", numeric["preservedResults"])
        self.assertEqual(geometric["rejectedClaims"], ["geometric-mismatch"])
        self.assertIn("seed:g", geometric["preservedResults"])

    def test_intentional_difference_is_explained_not_qualified(self):
        note = "cubic support crosses the bin that the box oracle averages"
        result = evaluate(
            payload(
                numericMismatch=True,
                intentionalDifference=True,
                differenceNote=note,
                precision="binary32",
            )
        )
        self.assertEqual(result["decision"], "explained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(note, result["reasons"])
        self.assertIn("precision:binary32", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_copied_oracle_still_lists_a_numeric_mismatch(self):
        result = evaluate(payload(oracleCopied=True, numericMismatch=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["copied-oracle", "numeric-mismatch"])
        self.assertIn("size:4x4", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "precision": "float"},
            {**valid, "sourceSize": "4X4"},
            {**valid, "seed": ""},
            {**valid, "oracleCopied": "no"},
            {**valid, "intentionalDifference": True, "differenceNote": ""},
            {**valid, "differenceNote": "orphan"},
            {k: v for k, v in valid.items() if k != "seed"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
