"""TC-P048-07 context-free color is not the default measured profile."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p048_tc07", Path(__file__).resolve().parents[1] / "gates" / "p048_tc07.py"
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
        "illuminant": "D65",
        "exposure": "1/50",
        "targetIdentity": "chart-18",
        "sourceRevision": "fw-1-0-0",
        "colorResult": "pleasing",
        "claimMeasured": False,
        "origin": "measured",
        "samples": ["patch-a", "patch-b"],
    }
    base.update(overrides)
    return base


class TcP04807(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P048-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("sample:patch-a", result["preservedResults"])
        self.assertIn("color:pleasing", result["preservedResults"])

    def test_constants(self):
        self.assertIn("target identity", _MODULE.INTERVENTION)
        self.assertIn("exploratory research", _MODULE.EXPECTED)
        self.assertIn("default measured profile", _MODULE.NEGATIVE)

    def test_negative_context_free_color_is_rejected(self):
        result = evaluate(payload(illuminant="", claimMeasured=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("removed:illuminant", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("sample:patch-b", result["preservedResults"])
        self.assertIn("illuminant:removed", result["preservedResults"])

    def test_repeat_author_assertion(self):
        result = evaluate(payload(origin="author_assertion", claimMeasured=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("author-assertion", result["rejectedClaims"])
        self.assertIn("origin:author_assertion", result["preservedResults"])
        self.assertIn("sample:patch-a", result["preservedResults"])

    def test_repeat_manufacturer_metadata(self):
        result = evaluate(payload(origin="manufacturer_metadata", claimMeasured=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "downgraded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("manufacturer-metadata", result["rejectedClaims"])
        self.assertIn("sample:patch-a", result["preservedResults"])
        self.assertIn("color:pleasing", result["preservedResults"])

    def test_full_context_is_still_not_the_default_profile(self):
        result = evaluate(payload(claimMeasured=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("not-default-measured-profile", result["rejectedClaims"])
        self.assertIn("revision:fw-1-0-0", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        for item in (None, {}, {**valid, "samples": []}, {**valid, "origin": "imported"}):
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
