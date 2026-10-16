"""Tests for TC-P104-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p104_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p104_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p104-tc01",
        "cachedFilename": "depth.tflite",
        "cachedDigest": "aaa111",
        "actualFilename": "depth.tflite",
        "actualDigest": "bbb222",
        "precision": "fp16",
        "runtimeVersion": "1.2.0",
        "variant": "quantized",
        "reportedIdentity": "bbb222",
        "acceptDepth": False,
    }
    base.update(overrides)
    return base


class TCP10401(unittest.TestCase):
    def assert_contract(self, result, evidence="p104-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P104-01")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.NEGATIVE, "A filename match alone must not establish identical weights.")
        self.assertIn("precision changes", _MODULE.REPEAT)

    def test_good_substitution_reports_the_actual_digest(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("filename-match:true", result["preservedResults"])
        self.assertIn("weights-match:false", result["preservedResults"])
        self.assertIn("accept-depth:false", result["preservedResults"])
        self.assertIn("actual-digest:bbb222", result["preservedResults"])
        self.assertIn("precision:fp16", result["preservedResults"])

    def test_negative_filename_match_does_not_accept_different_weights(self):
        result = evaluate(payload(acceptDepth=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("cached-digest:aaa111", result["preservedResults"])
        self.assertIn("actual-digest:bbb222", result["preservedResults"])

    def test_evidence_change(self):
        evidence = "p104-tc01-repeat"
        result = evaluate(payload(evidenceId=evidence, precision="int8", runtimeVersion="2.0", variant="float"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("precision:int8", result["preservedResults"])
        self.assertIn("variant:float", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = (
            {},
            {**valid, "applyNegative": True},
            {k: v for k, v in valid.items() if k != "acceptDepth"},
            payload(acceptDepth="yes"),
            payload(actualDigest=""),
            payload(reportedIdentity="bbb222 "),
        )
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
