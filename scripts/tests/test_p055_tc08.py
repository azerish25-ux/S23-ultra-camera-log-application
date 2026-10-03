"""TC-P055-08 independent reference disagreement."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p055_tc08", Path(__file__).resolve().parents[1] / "gates" / "p055_tc08.py"
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
        "precision": "float64",
        "sourceSize": "8",
        "seed": "seed-1",
        "copiedOracle": False,
        "mismatch": "none",
        "intentionalNote": "",
    }
    base.update(overrides)
    return base


class TcP05508(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P055-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Copying the implementation into its own test oracle must not count as independent validation.",
        )
        self.assertIn("mathematical oracle", _MODULE.INTERVENTION)

    def test_independent_agreement_is_compared(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "compared")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("precision:float64", result["preservedResults"])
        self.assertIn("size:8", result["preservedResults"])
        self.assertIn("seed:seed-1", result["preservedResults"])

    def test_negative_copied_oracle_is_rejected(self):
        result = evaluate(payload(copiedOracle=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["copied-oracle"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("precision:float64", result["preservedResults"])
        self.assertIn("seed:seed-1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "compared"})

    def test_unintended_numeric_mismatch_fails(self):
        result = evaluate(payload(mismatch="numeric"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unintended-numeric"])
        self.assertIn("mismatch:numeric", result["preservedResults"])

    def test_intentional_geometric_difference_is_explained(self):
        result = evaluate(payload(mismatch="geometric", intentionalNote="axis-swap"))
        self.assertEqual(result["decision"], "explained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("note:axis-swap", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_float32_and_float16(self):
        narrow = evaluate(payload(precision="float32", sourceSize="32", seed="seed-2"))
        half = evaluate(payload(precision="float16", sourceSize="64", seed="seed-3"))
        self.assertEqual(narrow["decision"], "compared")
        self.assertIn("precision:float32", narrow["preservedResults"])
        self.assertIn("size:32", narrow["preservedResults"])
        self.assertIn("seed:seed-2", narrow["preservedResults"])
        self.assertEqual(half["decision"], "compared")
        self.assertIn("precision:float16", half["preservedResults"])
        self.assertIn("size:64", half["preservedResults"])

    def test_copied_oracle_still_fails_when_values_match(self):
        result = evaluate(
            payload(precision="float32", sourceSize="16", seed="seed-9", copiedOracle=True, mismatch="none")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("copied-oracle", result["rejectedClaims"])
        self.assertIn("size:16", result["preservedResults"])
        self.assertIn("seed:seed-9", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "precision": "double"},
            {**valid, "mismatch": "color"},
            {**valid, "copiedOracle": "no"},
            {**valid, "intentionalNote": "has space"},
            {**valid, "seed": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
