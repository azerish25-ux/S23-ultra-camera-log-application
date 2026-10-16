"""Tests for TC-P122-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p122_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p122_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
PRIVATE = "/data/user/0/com.s23log/files/clip.mov"


def payload(**overrides):
    base = {
        "evidenceId": "p122-tc08",
        "repeat": "Repeat clean Log, rendered SDR, HDR-derived looks, and unverified partial exports.",
        "kind": "log-master",
        "privatePaths": [PRIVATE],
        "exportedPaths": ["bundle/recipe.json", "bundle/picture.mov"],
        "interpretationRecordPresent": True,
        "recipeMetadataPresent": True,
        "presentedAsSelfDescribing": False,
        "versions": _MODULE.valid_versions(),
        "mutatedInPlace": False,
    }
    base.update(overrides)
    return base


class TCP12208(unittest.TestCase):
    def assert_contract(self, result, evidence="p122-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P122-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("preimage=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_log_master_with_interpretation_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("kind=log-master", result["preservedResults"])
        self.assertIn("leakedCount=0", result["preservedResults"])

    def test_self_describing_log_without_interpretation_is_rejected(self):
        result = evaluate(payload(interpretationRecordPresent=False, presentedAsSelfDescribing=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.MISSING_INTERPRETATION, result["rejectedClaims"])

    def test_private_path_leak_is_rejected(self):
        result = evaluate(payload(kind="rendered-sdr", exportedPaths=["bundle/recipe.json", PRIVATE]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LEAK_TOKEN, result["rejectedClaims"])

    def test_hdr_derived_look_can_be_recorded(self):
        result = evaluate(payload(kind="hdr-derived"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_partial_export_presented_as_self_describing_is_rejected(self):
        result = evaluate(payload(kind="partial-unverified", presentedAsSelfDescribing=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PARTIAL_TOKEN, result["rejectedClaims"])

    def test_recipe_hash_mismatch_is_rejected(self):
        versions = _MODULE.valid_versions()
        versions[0]["version_sha256"] = "2" * 64
        result = evaluate(payload(versions=versions))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("version-sha256-mismatch", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p122-tc08-sdr"
        result = evaluate(payload(evidenceId=evidence, repeat="rendered SDR", kind="rendered-sdr"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(kind="display-p3"))
