"""Tests for TC-P154-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p154_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p154_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="SM-S911B")
    base.update({
        "inspected": ["kernel driver interfaces", "public camera HAL headers"],
        "unknownComponents": [_GATE.PROPRIETARY_COMPONENT],
        "calledComplete": False,
        "deviceVariant": "SM-S911B",
        "softwareVersion": "public-kernel-source-only",
    })
    base.update(overrides)
    return base


class TCP15402(unittest.TestCase):
    def assert_contract(self, result, evidence="p154-firmware-hal-survey"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P154-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_incomplete_package_keeps_the_missing_component_unknown(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(_GATE.PROPRIETARY_COMPONENT, result["preservedResults"][3]["unknownComponents"])
        self.assertEqual(result["preservedResults"][3]["deviceVariant"], "SM-S911B")
        self.assertEqual(_MODULE.CASE["name"], "Incomplete public source")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "source-archive-called-complete-without-evidence")

    def test_calling_the_archive_complete_is_rejected(self):
        result = evaluate(payload(calledComplete=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p154-firmware-hal-survey", result["preservedResults"])

    def test_missing_component_described_as_inspected_is_rejected(self):
        result = evaluate(payload(inspected=["kernel driver interfaces", _GATE.PROPRIETARY_COMPONENT]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LISTED_AS_INSPECTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_dropping_the_unknown_component_is_rejected(self):
        result = evaluate(payload(unknownComponents=["public-hal-headers"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_UNKNOWN, result["rejectedClaims"])

    def test_non_public_source_is_still_rejected(self):
        private = _GATE.private_source()
        result = evaluate(payload(
            sources=_GATE.fixture_sources() + [private],
            usedAsEvidence=[private["url"]],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.NON_PUBLIC_EVIDENCE, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p154-tc02-sm-s911u"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="SM-S911U",
            deviceVariant="SM-S911U",
            softwareVersion="different-public-drop",
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(inspected=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(calledComplete="yes"))
