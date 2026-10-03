"""TC-P050-08 a copied oracle is not independent validation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p050_tc08", Path(__file__).resolve().parents[1] / "gates" / "p050_tc08.py"
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
        "size": 4,
        "seed": 1,
        "oracleKind": "independent",
        "mismatch": "none",
        "explanation": "",
    }
    base.update(overrides)
    return base


class TcP05008(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P050-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("oracle:independent", result["preservedResults"])

    def test_constants(self):
        self.assertIn("mathematical oracle", _MODULE.INTERVENTION)
        self.assertIn("intentional algorithm differences", _MODULE.EXPECTED)
        self.assertIn("own test oracle", _MODULE.NEGATIVE)

    def test_repeat_precisions_sizes_and_seeds(self):
        cases = (
            ("f32", 2, 1),
            ("f64", 8, 7),
            ("int", 16, 3),
        )
        for precision, size, seed in cases:
            result = evaluate(payload(precision=precision, size=size, seed=seed))
            self.assertContract(result)
            self.assertEqual(result["decision"], "agreed")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(f"precision:{precision}", result["preservedResults"])
            self.assertIn(f"size:{size}", result["preservedResults"])
            self.assertIn(f"seed:{seed}", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_copied_oracle_is_not_independent(self):
        result = evaluate(payload(oracleKind="copied", precision="f64", size=8, seed=7))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "agreed"})
        self.assertEqual(result["rejectedClaims"], ["copied-oracle"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("oracle:copied", result["preservedResults"])
        self.assertIn("precision:f64", result["preservedResults"])
        self.assertIn("size:8", result["preservedResults"])

    def test_unintended_mismatch_fails_and_intentional_is_explained(self):
        numeric = evaluate(payload(mismatch="numeric", precision="int", size=2, seed=11))
        self.assertEqual(numeric["decision"], "rejected")
        self.assertEqual(numeric["rejectedClaims"], ["unintended-mismatch"])
        self.assertIn("mismatch:numeric", numeric["preservedResults"])
        geometric = evaluate(payload(mismatch="geometric"))
        self.assertEqual(geometric["decision"], "rejected")
        self.assertIn("mismatch:geometric", geometric["preservedResults"])
        explained = evaluate(
            payload(
                mismatch="intentional",
                explanation="nearest fill versus bilinear on a flat field",
            )
        )
        self.assertEqual(explained["decision"], "explained")
        self.assertNotIn(explained["decision"], {"qualified", "allowed"})
        self.assertIn("nearest fill versus bilinear on a flat field", explained["reasons"])
        self.assertIn("seed:1", explained["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "precision": "f16"},
            {**valid, "size": 0},
            {**valid, "oracleKind": "self"},
            {**valid, "mismatch": "intentional", "explanation": ""},
            {**valid, "explanation": "extra"},
            {k: v for k, v in valid.items() if k != "seed"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
