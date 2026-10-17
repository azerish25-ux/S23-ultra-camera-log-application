"""Tests for TC-P135-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p135_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p135_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    comparison = overrides.pop("comparison", _GATE.make_comparison())
    base = {
        "evidenceId": "p135-tc02",
        "repeat": "preset",
        "comparison": comparison,
        "displayedSourceSha256": comparison["left"]["source_sha256"],
        "displayedLeftTransfer": comparison["left"]["transfer"],
        "displayedRightTransfer": comparison["right"]["transfer"],
        "sourceEvidenceStatus": "source",
        "lookEvidenceStatus": "simulated",
        "virtualFormatRenamedSource": False,
    }
    base.update(overrides)
    return base


class TCP13502(unittest.TestCase):
    def assert_contract(self, result, evidence="p135-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P135-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_source_and_simulated_look_stay_independent(self):
        result = evaluate(payload(displayedLeftTransfer="BT.709", displayedRightTransfer="HLG"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["left"]["transfer"], "bt709")
        self.assertEqual(result["preservedResults"][1]["right"]["transfer"], "hlg")
        self.assertTrue(result["preservedResults"][1]["transfersDiffer"])
        self.assertTrue(result["preservedResults"][2]["sourceMatches"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "renamed-source-mode-after-virtual-format")

    def test_renaming_the_source_after_a_virtual_format_is_rejected(self):
        result = evaluate(payload(virtualFormatRenamedSource=True, displayedSourceSha256="ab" * 32))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["left"]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)

    def test_qualified_look_evidence_is_rejected(self):
        result = evaluate(payload(lookEvidenceStatus="qualified"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOOK_EVIDENCE_QUALIFIED, result["rejectedClaims"])
        self.assertIn(_MODULE.LOOK_HIDDEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p135-tc02-export"
        result = evaluate(payload(evidenceId=evidence, repeat="export sharing"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(displayedLeftTransfer=""))
