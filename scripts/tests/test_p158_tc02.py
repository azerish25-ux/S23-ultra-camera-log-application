"""Tests for TC-P158-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p158_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p158_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.case_payload(**overrides)


class TCP15802(unittest.TestCase):
    def assert_contract(self, result, evidence="p158-advanced-capture"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P158-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_omitted_imaging_stays_unknown(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(_MODULE.CASE["name"], "Incomplete public source")
        self.assertIn(_GATE.MOTION_RULE, " ".join(result["reasons"]))

    def test_complete_firmware_claim_is_rejected(self):
        result = evaluate(payload(claimedCompleteFirmware=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_omitted_component_called_known_is_rejected(self):
        result = evaluate(payload(
            unknownComponents=["unspecified-blob"],
            proprietaryImagingOmitted=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_NOT_UNKNOWN, result["rejectedClaims"])

    def test_non_experimental_label_is_rejected_inside_the_case(self):
        result = evaluate(payload(experimentLabel="production"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.LABEL_NOT_EXPERIMENTAL, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p158-tc02-variant"
        result = evaluate(payload(evidenceId=evidence, repeat="software-version"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(inspectable=["proprietary-imaging"], unknownComponents=["proprietary-imaging"]))
