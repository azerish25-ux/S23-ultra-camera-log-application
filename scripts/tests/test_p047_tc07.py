"""TC-P047-07 attractive color without context is not a measured default."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p047_tc07", Path(__file__).resolve().parents[1] / "gates" / "p047_tc07.py"
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
        "sampleId": "sample-a",
        "illuminant": "d65",
        "exposure": "0.01",
        "targetIdentity": "cc24",
        "sourceRevision": "rev-3",
        "attractiveColor": False,
        "evidenceKind": "measured",
    }
    base.update(overrides)
    return base


class TcP04707(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P047-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("sample:sample-a", result["preservedResults"])

    def test_constants(self):
        self.assertIn("source revision", _MODULE.INTERVENTION)
        self.assertIn("exploratory research", _MODULE.EXPECTED)
        self.assertIn("default measured profile", _MODULE.NEGATIVE)

    def test_complete_measured_context_is_recorded(self):
        result = evaluate(payload(attractiveColor=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "context_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("illuminant:d65", result["preservedResults"])
        self.assertIn("exposure:0.01", result["preservedResults"])
        self.assertIn("targetIdentity:cc24", result["preservedResults"])
        self.assertIn("sourceRevision:rev-3", result["preservedResults"])
        self.assertIn("attractive color was not promoted", " ".join(result["reasons"]))
        self.assertIn("recorded context is not physical S23 qualification", result["openQuestions"])

    def test_missing_illuminant_with_attractive_color_is_rejected(self):
        result = evaluate(payload(illuminant=None, attractiveColor=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing:illuminant", result["rejectedClaims"])
        self.assertIn("not-default-measured-profile", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("missing:illuminant", result["preservedResults"])
        self.assertIn("exploratory-data-retained:sample-a", result["openQuestions"])
        self.assertNotIn("illuminant:d65", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "context_recorded"})

    def test_missing_exposure_is_downgraded_and_retained(self):
        result = evaluate(payload(exposure=None))
        self.assertEqual(result["decision"], "downgraded")
        self.assertIn("missing:exposure", result["rejectedClaims"])
        self.assertIn("missing:exposure", result["preservedResults"])
        self.assertIn("targetIdentity:cc24", result["preservedResults"])
        self.assertIn("data retained for exploratory research", result["reasons"])

    def test_author_assertion_repeat(self):
        result = evaluate(payload(evidenceKind="author-assertion", attractiveColor=True))
        self.assertEqual(result["decision"], "downgraded")
        self.assertIn("author-assertion", result["rejectedClaims"])
        self.assertIn("not-default-measured-profile", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("illuminant:d65", result["preservedResults"])
        self.assertIn("sample:sample-a", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "context_recorded"})

    def test_manufacturer_metadata_repeat(self):
        result = evaluate(payload(evidenceKind="manufacturer-metadata", sourceRevision=None))
        self.assertEqual(result["decision"], "downgraded")
        self.assertIn("manufacturer-metadata", result["rejectedClaims"])
        self.assertIn("missing:sourceRevision", result["rejectedClaims"])
        self.assertIn("missing:sourceRevision", result["preservedResults"])
        self.assertIn("evidence:manufacturer-metadata", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "evidenceKind": "guess"},
            {**valid, "attractiveColor": "yes"},
            {**valid, "illuminant": ""},
            {**valid, "sampleId": "Sample"},
            {k: v for k, v in valid.items() if k != "targetIdentity"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
