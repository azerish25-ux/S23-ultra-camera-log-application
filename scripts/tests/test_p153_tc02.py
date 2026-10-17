"""Tests for TC-P153-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p153_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p153_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.example_payload(**overrides)


class TCP15302(unittest.TestCase):
    def assert_contract(self, result, evidence="p153-blocked-capability"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P153-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_omitted_components_stay_unknown(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"][3]["unknownComponents"],
            ["proprietary-imaging-hal", "isp-firmware"],
        )
        self.assertEqual(result["preservedResults"][3]["inspected"], ["public-kernel"])
        self.assertFalse(result["preservedResults"][3]["claimed_complete"])
        self.assertEqual(_MODULE.CASE["name"], "Incomplete public source")

    def test_complete_archive_claim_without_evidence_is_rejected(self):
        result = evaluate(payload(claimed_complete=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ARCHIVE_COMPLETE, result["rejectedClaims"])
        self.assertIn(_MODULE.OMITTED_UNKNOWN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(
            result["preservedResults"][3]["unknownComponents"],
            ["proprietary-imaging-hal", "isp-firmware"],
        )

    def test_complete_claim_without_omissions_still_needs_evidence(self):
        result = evaluate(payload(claimed_complete=True, omitted_components=[], completeness_evidence=None))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ARCHIVE_COMPLETE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.OMITTED_UNKNOWN, result["rejectedClaims"])

    def test_empty_inspection_is_rejected(self):
        result = evaluate(payload(inspected=[]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.INSPECTED_MISSING, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p153-tc02-variant"
        result = evaluate(payload(evidenceId=evidence, repeat="software-version"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(inspected=["proprietary-imaging-hal"]))
