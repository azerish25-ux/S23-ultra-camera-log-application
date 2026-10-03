"""TC-P043-07 unrecorded measurement conditions."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p043_tc07", Path(__file__).resolve().parents[1] / "gates" / "p043_tc07.py"
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
        "datasetId": "flat-set",
        "missing": "none",
        "origin": "measured-attempt",
        "attractiveColor": False,
        "samplesRetained": "samples-flat-set",
    }
    base.update(overrides)
    return base


class TcP04307(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P043-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("dataset:flat-set", result["preservedResults"])
        self.assertIn("samples:samples-flat-set", result["preservedResults"])

    def test_attractive_color_without_context_is_not_a_measured_profile(self):
        result = evaluate(payload(missing="illuminant", attractiveColor=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "context_recorded", "downgraded"})
        self.assertIn("attractive-without-context", result["rejectedClaims"])
        self.assertIn("missing:illuminant", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("samples:samples-flat-set", result["preservedResults"])

    def test_missing_exposure_downgrades_and_keeps_samples(self):
        result = evaluate(payload(missing="exposure"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "downgraded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("missing:exposure", result["rejectedClaims"])
        self.assertIn("samples:samples-flat-set", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_author_assertion_is_downgraded(self):
        result = evaluate(payload(origin="author-assertion"))
        self.assertEqual(result["decision"], "downgraded")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "context_recorded"})
        self.assertIn("author-assertion", result["rejectedClaims"])
        self.assertIn("origin:author-assertion", result["preservedResults"])
        self.assertIn("samples:samples-flat-set", result["preservedResults"])

    def test_manufacturer_metadata_is_downgraded(self):
        result = evaluate(payload(origin="manufacturer-metadata"))
        self.assertEqual(result["decision"], "downgraded")
        self.assertIn("manufacturer-metadata", result["rejectedClaims"])
        self.assertIn("samples:samples-flat-set", result["preservedResults"])
        self.assertIn("dataset:flat-set", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_recorded_context_is_not_the_default_profile(self):
        result = evaluate(payload(attractiveColor=True))
        self.assertEqual(result["decision"], "context_recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("samples:samples-flat-set", result["preservedResults"])
        self.assertTrue(any("not the default measured profile" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "missing": "lens"},
            {**valid, "origin": "guess"},
            {**valid, "samplesRetained": ""},
            {**valid, "attractiveColor": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
