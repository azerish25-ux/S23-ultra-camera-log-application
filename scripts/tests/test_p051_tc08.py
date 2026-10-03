"""TC-P051-08 a copied oracle is not independent validation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p051_tc08", Path(__file__).resolve().parents[1] / "gates" / "p051_tc08.py"
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
        "precision": "rational",
        "sourceSize": "2x2",
        "seed": 3,
        "oracleKind": "independent",
        "mismatch": "none",
        "intentional": "",
    }
    base.update(overrides)
    return base


class TcP05108(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P051-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants(self):
        self.assertIn("mathematical oracle", _MODULE.INTERVENTION)
        self.assertIn("intentional algorithm differences", _MODULE.EXPECTED)
        self.assertIn("own test oracle", _MODULE.NEGATIVE)

    def test_closed_form_is_not_a_replayed_loop(self):
        self.assertEqual(_MODULE.independent_total("2x2", 3), 18)
        self.assertEqual(sum(3 + i for i in range(4)), 18)
        self.assertEqual(_MODULE.independent_total("4x4", 1), 136)

    def test_repeat_precisions_and_sizes(self):
        for precision, size, seed in (
            ("float32", "2x2", 3),
            ("float64", "4x4", 1),
            ("rational", "6x6", 0),
        ):
            result = evaluate(payload(precision=precision, sourceSize=size, seed=seed))
            self.assertContract(result)
            self.assertEqual(result["decision"], "oracle_agreed")
            self.assertEqual(result["rejectedClaims"], [])
            total = _MODULE.independent_total(size, seed)
            self.assertIn(f"independent:{total}", result["preservedResults"])
            self.assertIn(f"implementation:{total}", result["preservedResults"])
            self.assertIn(f"precision:{precision}", result["preservedResults"])
            self.assertIn(f"seed:{seed}", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_second_seed(self):
        result = evaluate(payload(sourceSize="4x4", seed=7, precision="float64"))
        self.assertEqual(result["decision"], "oracle_agreed")
        self.assertIn(
            f"independent:{_MODULE.independent_total('4x4', 7)}",
            result["preservedResults"],
        )
        self.assertIn("seed:7", result["preservedResults"])

    def test_unintended_numeric_and_geometric_mismatches_fail(self):
        numeric = evaluate(payload(mismatch="numeric"))
        self.assertEqual(numeric["decision"], "rejected")
        self.assertEqual(numeric["rejectedClaims"], ["numeric-mismatch"])
        self.assertIn("independent:18", numeric["preservedResults"])
        self.assertIn("implementation:19", numeric["preservedResults"])
        geometric = evaluate(payload(mismatch="geometric", sourceSize="6x6", seed=2))
        self.assertEqual(geometric["decision"], "rejected")
        self.assertEqual(geometric["rejectedClaims"], ["geometric-mismatch"])
        self.assertIn("origin:1", geometric["preservedResults"])
        self.assertIn(f"independent:{_MODULE.independent_total('6x6', 2)}", geometric["preservedResults"])
        self.assertNotIn(numeric["decision"], {"qualified", "allowed", "oracle_agreed"})

    def test_intentional_difference_is_explained_not_qualified(self):
        note = "candidate kernel uses a wider halo than the bilinear reference"
        result = evaluate(payload(mismatch="numeric", intentional=note, precision="float32"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "difference_explained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(note, result["reasons"])
        self.assertIn("independent:18", result["preservedResults"])
        self.assertIn("implementation:19", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_copied_oracle_does_not_count(self):
        result = evaluate(payload(oracleKind="copied", precision="float64", sourceSize="4x4", seed=1))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["copied-oracle"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("independent:136", result["preservedResults"])
        self.assertIn("precision:float64", result["preservedResults"])
        self.assertIn("seed:1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "oracle_agreed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "precision": "decimal"},
            {**valid, "sourceSize": "3x3"},
            {**valid, "seed": -1},
            {**valid, "oracleKind": "same"},
            {**valid, "mismatch": "none", "intentional": "excuse"},
            {**valid, "oracleKind": "copied", "intentional": "excuse"},
            {k: v for k, v in valid.items() if k != "seed"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
