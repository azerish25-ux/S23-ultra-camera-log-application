"""TC-P041-07 unrecorded measurement conditions."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p041_tc07", Path(__file__).resolve().parents[1] / "gates" / "p041_tc07.py"
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
        "missingFields": [],
        "authorAssertion": "measured",
        "origin": "measurement",
        "attractiveColor": False,
        "exploratoryToken": "lab-series-a",
    }
    base.update(overrides)
    return base


class TcP04107(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P041-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_attractive_color_without_context_is_not_the_default_profile(self):
        result = evaluate(payload(missingFields=["illuminant", "exposure"], attractiveColor=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["attractive-color-without-context", "missing-illuminant", "missing-exposure"],
        )
        self.assertIn("data:lab-series-a", result["preservedResults"])
        self.assertIn("assertion:measured", result["preservedResults"])
        self.assertIn("missing:illuminant,exposure", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("retained for exploratory research", result["openQuestions"])

    def test_missing_target_downgrades_and_retains_data(self):
        result = evaluate(payload(missingFields=["target"], exploratoryToken="chart-notes"))
        self.assertEqual(result["decision"], "exploratory")
        self.assertEqual(result["rejectedClaims"], ["missing-target"])
        self.assertIn("data:chart-notes", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_missing_source_revision_is_exploratory(self):
        result = evaluate(payload(missingFields=["source-revision"]))
        self.assertEqual(result["decision"], "exploratory")
        self.assertIn("missing-source-revision", result["rejectedClaims"])
        self.assertIn("data:lab-series-a", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_imported_author_assertion_repeat_is_retained_separately(self):
        result = evaluate(payload(origin="author-import", authorAssertion="measured"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "assertion_retained")
        self.assertEqual(result["rejectedClaims"], ["imported-author-assertion"])
        self.assertIn("assertion:measured", result["preservedResults"])
        self.assertIn("origin:author-import", result["preservedResults"])
        self.assertIn("author assertion is not importer status", result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_manufacturer_metadata_repeat_stays_provisional(self):
        result = evaluate(
            payload(origin="manufacturer-metadata", authorAssertion="provisional", attractiveColor=True)
        )
        self.assertEqual(result["decision"], "provisional")
        self.assertEqual(result["rejectedClaims"], ["manufacturer-starting-profile"])
        self.assertIn("origin:manufacturer-metadata", result["preservedResults"])
        self.assertIn("data:lab-series-a", result["preservedResults"])
        self.assertIn("not a measured profile", result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_complete_measurement_conditions_are_recorded_not_qualified(self):
        result = evaluate(payload(attractiveColor=True))
        self.assertEqual(result["decision"], "conditions_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("missing:none", result["preservedResults"])
        self.assertIn("recorded conditions are not physical S23 qualification", result["openQuestions"])
        self.assertTrue(any("attractive color was not the measurement claim" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "missingFields": ["illuminant", "illuminant"]},
            {**valid, "missingFields": ["gain"]},
            {**valid, "origin": "camera"},
            {**valid, "authorAssertion": "measured profile"},
            {**valid, "attractiveColor": "yes"},
            {**valid, "exploratoryToken": ""},
            {**valid, "missingFields": "illuminant"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
