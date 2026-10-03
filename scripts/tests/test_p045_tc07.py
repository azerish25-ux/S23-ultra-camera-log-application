"""TC-P045-07 unrecorded measurement conditions."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p045_tc07", Path(__file__).resolve().parents[1] / "gates" / "p045_tc07.py"
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
        "dataId": "chart-run-1",
        "missing": [],
        "sourceKind": "measured",
        "attractiveResult": False,
        "makeDefault": False,
    }
    base.update(overrides)
    return base


class TcP04507(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P045-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("data:chart-run-1", result["preservedResults"])

    def test_complete_measured_context_stays_contextual(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "contextual")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source:measured", result["preservedResults"])

    def test_negative_attractive_default_without_context_is_rejected(self):
        result = evaluate(
            payload(missing=["illuminant", "exposure"], attractiveResult=True, makeDefault=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("default-without-context", result["rejectedClaims"])
        self.assertIn("attractive-without-context", result["rejectedClaims"])
        self.assertIn("missing:illuminant", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("data:chart-run-1", result["preservedResults"])
        self.assertIn("missing:exposure", result["preservedResults"])

    def test_missing_target_is_exploratory_and_retains_the_data(self):
        result = evaluate(payload(missing=["target", "revision"], attractiveResult=True))
        self.assertEqual(result["decision"], "exploratory")
        self.assertIn("missing:target", result["rejectedClaims"])
        self.assertIn("missing:revision", result["preservedResults"])
        self.assertIn("attractive:yes", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "contextual"})

    def test_repeat_author_assertion(self):
        result = evaluate(payload(sourceKind="author_assertion", dataId="note-9"))
        self.assertEqual(result["decision"], "exploratory")
        self.assertIn("author-assertion", result["rejectedClaims"])
        self.assertIn("data:note-9", result["preservedResults"])
        self.assertIn("source:author_assertion", result["preservedResults"])

    def test_repeat_manufacturer_metadata_starting_profile(self):
        result = evaluate(payload(sourceKind="manufacturer_metadata", attractiveResult=True, makeDefault=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("default-without-context", result["rejectedClaims"])
        self.assertIn("manufacturer-metadata", result["rejectedClaims"])
        self.assertIn("source:manufacturer_metadata", result["preservedResults"])
        self.assertIn("data:chart-run-1", result["preservedResults"])

    def test_make_default_with_full_context_does_not_qualify(self):
        result = evaluate(payload(makeDefault=True, attractiveResult=True))
        self.assertEqual(result["decision"], "contextual")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(any("does not install a default measured profile" in item for item in result["openQuestions"]))
        self.assertEqual(result["rejectedClaims"], [])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "dataId"},
            {**valid, "extra": True},
            {**valid, "missing": ["lens"]},
            {**valid, "missing": ["illuminant", "illuminant"]},
            {**valid, "sourceKind": "guess"},
            {**valid, "attractiveResult": 1},
            {**valid, "makeDefault": "yes"},
            {**valid, "dataId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
