"""Tests for TC-P101-01."""

from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p101_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p101_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _identity(content, precision, runtime):
    hasher = hashlib.sha256()
    hasher.update(content.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(precision.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(runtime.encode("utf-8"))
    return hasher.hexdigest()


def payload(**overrides):
    base = {
        "evidenceId": "p101-tc01",
        "repeat": "precision changes",
        "filename": "depth-small.tflite",
        "content": "approved-weights-v1",
        "precision": "fp16",
        "runtimeVersion": "tflite-2.16.1",
        "cachedFilename": "depth-small.tflite",
        "cachedContent": "approved-weights-v1",
        "cachedPrecision": "fp16",
        "cachedRuntimeVersion": "tflite-2.16.1",
        "keepCachedDepth": True,
    }
    base.update(overrides)
    return base


class TCP10101(unittest.TestCase):
    def assert_contract(self, result, evidence="p101-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P101-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))
        self.assertTrue(result["reasons"])

    def test_matching_identity_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        text = " ".join(result["reasons"])
        self.assertIn(_identity("approved-weights-v1", "fp16", "tflite-2.16.1"), text)
        self.assertIn("cache-compatible", text)
        self.assertIn("filename was not used as the identity", text)

    def test_filename_match_with_different_digest_is_rejected(self):
        result = evaluate(payload(content="converted-weights-v2", keepCachedDepth=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("filename-match-alone-establish-identical-weights", result["rejectedClaims"])
        self.assertIn("cache-invalidated", " ".join(result["reasons"]))
        self.assertIn("digest", " ".join(result["reasons"]))

    def test_precision_or_runtime_change_invalidates_kept_cache(self):
        precision = evaluate(payload(precision="fp32", keepCachedDepth=True))
        runtime = evaluate(payload(runtimeVersion="tflite-2.17.0", keepCachedDepth=True))
        self.assert_contract(precision)
        self.assert_contract(runtime)
        self.assertIn("filename-match-alone-establish-identical-weights", precision["rejectedClaims"])
        self.assertIn("filename-match-alone-establish-identical-weights", runtime["rejectedClaims"])
        self.assertIn("precision", " ".join(precision["reasons"]))
        self.assertIn("runtime", " ".join(runtime["reasons"]))

    def test_invalidated_cache_is_recorded_when_depth_is_dropped(self):
        result = evaluate(payload(content="converted-weights-v2", keepCachedDepth=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        text = " ".join(result["reasons"])
        self.assertIn("cache-invalidated", text)
        self.assertIn(_identity("converted-weights-v2", "fp16", "tflite-2.16.1"), text)

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p101-tc01-runtime"
        result = evaluate(payload(evidenceId=evidence, repeat="runtime versions"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(content=""))
