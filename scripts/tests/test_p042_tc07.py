"""TC-P042-07 unrecorded measurement conditions."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p042_tc07", Path(__file__).resolve().parents[1] / "gates" / "p042_tc07.py"
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
        "exposure": "10000000ns",
        "targetId": "neutral-18",
        "sourceRevision": "d4deac8fc828",
        "origin": "measured",
        "colorAppeal": "pleasing-skin",
        "profileRequested": False,
    }
    base.update(overrides)
    return base


class TcP04207(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P042-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("illuminant", _MODULE.INTERVENTION)
        self.assertIn("exploratory", _MODULE.EXPECTED)
        self.assertIn("attractive color", _MODULE.NEGATIVE)

    def test_attractive_color_without_illuminant_is_rejected(self):
        result = evaluate(payload(illuminant=None, profileRequested=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unrecorded-conditions", "default-profile"])
        self.assertIn("missing:illuminant", result["preservedResults"])
        self.assertIn("color:pleasing-skin", result["preservedResults"])
        self.assertIn("exposure:10000000ns", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertNotIn("profile:pleasing-skin", result["preservedResults"])

    def test_repeat_author_assertion_is_downgraded(self):
        result = evaluate(payload(origin="author_assertion", profileRequested=False))
        self.assertEqual(result["decision"], "downgraded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("origin:author_assertion", result["preservedResults"])
        self.assertIn("targetId:neutral-18", result["preservedResults"])
        self.assertIn("color:pleasing-skin", result["preservedResults"])
        self.assertIn(
            "exploratory research is not the default measured profile",
            result["openQuestions"],
        )

    def test_repeat_manufacturer_metadata_cannot_be_requested_as_default(self):
        result = evaluate(payload(origin="manufacturer_metadata", profileRequested=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("origin:manufacturer_metadata", result["preservedResults"])
        self.assertIn("default-profile", result["rejectedClaims"])
        self.assertIn("sourceRevision:d4deac8fc828", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_missing_exposure_keeps_the_other_fields(self):
        result = evaluate(payload(exposure=None))
        self.assertEqual(result["decision"], "downgraded")
        self.assertIn("missing:exposure", result["preservedResults"])
        self.assertIn("illuminant:D65", result["preservedResults"])
        self.assertIn("color:pleasing-skin", result["preservedResults"])

    def test_complete_measured_context_is_withheld(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("illuminant:D65", result["preservedResults"])
        self.assertIn("color:pleasing-skin", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "origin": "guess"},
            {**valid, "illuminant": ""},
            {**valid, "profileRequested": "yes"},
            {**valid, "colorAppeal": "pretty skin"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
