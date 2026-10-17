"""Tests for TC-P159-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p159_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p159_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="device variants")
    base.update({
        "archiveId": "public-kernel",
        "inspectedComponents": ["public-kernel", "scheduler"],
        "missingComponents": ["proprietary-imaging"],
        "claimedCompleteFirmware": False,
    })
    base.update(overrides)
    return base


class TCP15902(unittest.TestCase):
    def assert_contract(self, result, evidence="p159-computational-optics"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P159-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_incomplete_archive_keeps_missing_components_unknown(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["missingComponents"], ["proprietary-imaging"])
        self.assertEqual(_MODULE.CASE["name"], "Incomplete public source")

    def test_calling_the_archive_complete_firmware_is_rejected(self):
        result = evaluate(payload(claimedCompleteFirmware=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_omitting_the_unknown_component_is_rejected(self):
        result = evaluate(payload(missingComponents=[], claimedCompleteFirmware=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_UNKNOWN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_inspected_proprietary_imaging_can_support_a_completeness_claim(self):
        result = evaluate(payload(
            inspectedComponents=["public-kernel", "proprietary-imaging"],
            missingComponents=[],
            claimedCompleteFirmware=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p159-tc02-software-version"
        result = evaluate(payload(evidenceId=evidence, repeat="software versions"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(inspectedComponents=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(archiveId=""))
