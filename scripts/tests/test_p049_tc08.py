"""TC-P049-08 a copied implementation is not an independent oracle."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p049_tc08", Path(__file__).resolve().parents[1] / "gates" / "p049_tc08.py"
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
        "sourceSize": "small",
        "seed": "1",
        "oracleKind": "independent",
        "mismatch": "none",
    }
    base.update(overrides)
    return base


class TcP04908(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P049-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertIn("mathematical oracle", _MODULE.INTERVENTION)
        self.assertIn("algorithm differences", _MODULE.EXPECTED)
        self.assertIn("own test oracle", _MODULE.NEGATIVE)

    def test_integer_and_rational_precisions_can_agree(self):
        for precision in ("integer", "rational"):
            result = evaluate(payload(precision=precision, seed="0"))
            self.assertContract(result)
            self.assertEqual(result["decision"], "compared")
            self.assertIn(f"precision:{precision}", result["preservedResults"])
            self.assertIn("seed:0", result["preservedResults"])
            self.assertEqual(result["rejectedClaims"], [])

    def test_tiny_and_medium_sizes_stay_in_the_inventory(self):
        tiny = evaluate(payload(sourceSize="tiny", seed="7"))
        medium = evaluate(payload(sourceSize="medium", seed="11", precision="high"))
        self.assertEqual(tiny["decision"], "compared")
        self.assertEqual(medium["decision"], "compared")
        self.assertIn("source-size:tiny", tiny["preservedResults"])
        self.assertIn("source-size:medium", medium["preservedResults"])
        self.assertIn("seed:7", tiny["preservedResults"])
        self.assertIn("seed:11", medium["preservedResults"])

    def test_copied_oracle_does_not_count(self):
        result = evaluate(payload(oracleKind="copied-implementation", mismatch="none"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["copied-implementation-oracle"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("oracle:copied-implementation", result["preservedResults"])
        self.assertIn("precision:rational", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "compared"})

    def test_numeric_and_geometric_mismatches_fail(self):
        numeric = evaluate(payload(mismatch="numeric"))
        geometric = evaluate(payload(mismatch="geometric", sourceSize="tiny"))
        self.assertEqual(numeric["decision"], "rejected")
        self.assertEqual(numeric["rejectedClaims"], ["numeric-mismatch"])
        self.assertEqual(geometric["decision"], "rejected")
        self.assertEqual(geometric["rejectedClaims"], ["geometric-mismatch"])
        self.assertIn("source-size:tiny", geometric["preservedResults"])

    def test_intentional_difference_is_explained_not_passed(self):
        result = evaluate(payload(mismatch="intentional", precision="high", seed="3"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("intentional algorithm difference" in item for item in result["reasons"]))
        self.assertIn("seed:3", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "compared"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "precision": "float"},
            {**valid, "sourceSize": "large"},
            {**valid, "seed": "01"},
            {**valid, "oracleKind": "same"},
            {**valid, "mismatch": "color"},
            {k: v for k, v in valid.items() if k != "seed"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
