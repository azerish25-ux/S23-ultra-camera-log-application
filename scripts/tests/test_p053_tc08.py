"""TC-P053-08 independent reference disagreement."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p053_tc08", Path(__file__).resolve().parents[1] / "gates" / "p053_tc08.py"
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
        "sourceSize": 8,
        "seed": "seed-a",
        "independentOracle": True,
        "copiedImplementation": False,
        "intentionalDifference": False,
        "numericMismatch": False,
        "geometricMismatch": False,
        "differenceNote": "",
    }
    base.update(overrides)
    return base


class TcP05308(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P053-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_rational_and_double_precisions_can_agree(self):
        rational = evaluate(payload())
        double = evaluate(payload(precision="double", sourceSize=16))
        self.assertContract(rational)
        self.assertEqual(rational["decision"], "independent_check")
        self.assertEqual(double["decision"], "independent_check")
        self.assertIn("precision:rational", rational["preservedResults"])
        self.assertIn("precision:double", double["preservedResults"])
        self.assertIn("source-size:8", rational["preservedResults"])
        self.assertIn("source-size:16", double["preservedResults"])
        self.assertEqual(rational["rejectedClaims"], [])

    def test_distinct_seeds_stay_independent(self):
        first = evaluate(payload(seed="seed-a", precision="single", sourceSize=4))
        second = evaluate(payload(seed="seed-b", precision="half", sourceSize=32))
        self.assertEqual(first["decision"], "independent_check")
        self.assertEqual(second["decision"], "independent_check")
        self.assertIn("seed:seed-a", first["preservedResults"])
        self.assertIn("seed:seed-b", second["preservedResults"])
        self.assertIn("precision:half", second["preservedResults"])

    def test_copying_the_implementation_is_not_an_oracle(self):
        copied = evaluate(payload(copiedImplementation=True, independentOracle=False))
        self.assertContract(copied)
        self.assertEqual(copied["decision"], "rejected")
        self.assertEqual(copied["rejectedClaims"], ["self-oracle"])
        self.assertIn(_MODULE.NEGATIVE, copied["reasons"])
        self.assertIn("precision:rational", copied["preservedResults"])
        self.assertIn("seed:seed-a", copied["preservedResults"])
        self.assertNotIn(copied["decision"], {"qualified", "allowed", "independent_check"})
        dependent = evaluate(payload(independentOracle=False))
        self.assertEqual(dependent["decision"], "rejected")
        self.assertIn("self-oracle", dependent["rejectedClaims"])

    def test_unintended_mismatch_fails_and_an_explained_difference_does_not_qualify(self):
        mismatch = evaluate(payload(numericMismatch=True, geometricMismatch=True, precision="single"))
        self.assertEqual(mismatch["decision"], "rejected")
        self.assertEqual(mismatch["rejectedClaims"], ["numeric-mismatch", "geometric-mismatch"])
        self.assertIn("precision:single", mismatch["preservedResults"])
        explained = evaluate(
            payload(
                intentionalDifference=True,
                numericMismatch=True,
                differenceNote="lower median is declared",
                sourceSize=8,
                seed="seed-c",
            )
        )
        self.assertEqual(explained["decision"], "explained")
        self.assertNotIn(explained["decision"], {"qualified", "allowed"})
        self.assertIn("note:lower median is declared", explained["preservedResults"])
        self.assertIn("seed:seed-c", explained["preservedResults"])
        self.assertTrue(any("lower median is declared" in item for item in explained["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "precision": "float"},
            {**valid, "sourceSize": 0},
            {**valid, "seed": ""},
            {**valid, "independentOracle": 1},
            {**valid, "intentionalDifference": True, "differenceNote": ""},
            {**valid, "differenceNote": "unused"},
            {key: value for key, value in valid.items() if key != "seed"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
