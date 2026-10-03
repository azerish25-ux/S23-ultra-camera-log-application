"""TC-P044-07 unrecorded measurement conditions."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p044_tc07", Path(__file__).resolve().parents[1] / "gates" / "p044_tc07.py"
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
        "targetIdentity": "grey-card",
        "sourceRevision": "d4deac8fc82832fd23396a01065c5f0bf9da6670",
        "colorResult": "neutral-swatch",
        "claimMeasured": False,
        "origin": "measured",
        "samples": ["patch-a", "patch-b"],
    }
    base.update(overrides)
    return base


class TcP04407(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P044-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_intervention_expected_and_negative(self):
        self.assertIn("source revision", _MODULE.INTERVENTION)
        self.assertIn("exploratory research", _MODULE.EXPECTED)
        self.assertIn("default measured profile", _MODULE.NEGATIVE)

    def test_complete_context_stays_exploratory(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "exploratory")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sample:patch-a", result["preservedResults"])
        self.assertIn("sample:patch-b", result["preservedResults"])
        self.assertIn("color:neutral-swatch", result["preservedResults"])
        self.assertIn("illuminant:D65", result["preservedResults"])
        self.assertIn("revision:d4deac8fc82832fd23396a01065c5f0bf9da6670", result["preservedResults"])

    def test_removed_illuminant_is_downgraded_and_samples_remain(self):
        result = evaluate(payload(illuminant=""))
        self.assertEqual(result["decision"], "downgraded")
        self.assertEqual(result["rejectedClaims"], ["removed:illuminant"])
        self.assertIn("sample:patch-a", result["preservedResults"])
        self.assertIn("illuminant:removed", result["preservedResults"])
        self.assertIn("color:neutral-swatch", result["preservedResults"])
        self.assertIn("retained for exploratory research", result["openQuestions"])

    def test_author_assertion_repeat_is_not_a_measurement(self):
        result = evaluate(payload(origin="author_assertion"))
        self.assertEqual(result["decision"], "downgraded")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "exploratory"})
        self.assertEqual(result["rejectedClaims"], ["author-assertion"])
        self.assertIn("sample:patch-b", result["preservedResults"])
        self.assertIn("origin:author_assertion", result["preservedResults"])
        self.assertIn("target:grey-card", result["preservedResults"])

    def test_manufacturer_metadata_repeat_keeps_the_color_result(self):
        result = evaluate(payload(origin="manufacturer_metadata", colorResult="pretty-amber"))
        self.assertEqual(result["decision"], "downgraded")
        self.assertEqual(result["rejectedClaims"], ["manufacturer-metadata"])
        self.assertIn("color:pretty-amber", result["preservedResults"])
        self.assertIn("sample:patch-a", result["preservedResults"])
        self.assertIn("exposure:1/50", result["preservedResults"])

    def test_negative_attractive_result_without_context_cannot_qualify(self):
        result = evaluate(
            payload(
                illuminant="",
                exposure="",
                targetIdentity="",
                sourceRevision="",
                claimMeasured=True,
                colorResult="pretty-amber",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "exploratory"})
        self.assertEqual(
            result["rejectedClaims"],
            ["removed:illuminant", "removed:exposure", "removed:target", "removed:revision"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("color:pretty-amber", result["preservedResults"])
        self.assertIn("sample:patch-a", result["preservedResults"])
        self.assertIn("sample:patch-b", result["preservedResults"])

    def test_claim_with_full_context_is_still_not_the_default_profile(self):
        result = evaluate(payload(claimMeasured=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["not-default-measured-profile"])
        self.assertIn("color:neutral-swatch", result["preservedResults"])
        self.assertIn("sample:patch-a", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "samples"},
            {**valid, "extra": True},
            {**valid, "samples": []},
            {**valid, "samples": [" "]},
            {**valid, "origin": "imported"},
            {**valid, "claimMeasured": "true"},
            {**valid, "colorResult": ""},
            {**valid, "illuminant": " D65"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
