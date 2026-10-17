"""Tests for TC-P157-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p157_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p157_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload()
    base.update({
        "repeat": "SM-S911B",
        "components": [
            {
                "name": "public-kernel",
                "inspectable": True,
                "status": "inspected",
                "evidence": "a" * 64,
            },
            {
                "name": "proprietary-imaging",
                "inspectable": False,
                "status": "unknown",
                "evidence": None,
            },
        ],
        "labelledCompleteCameraFirmware": False,
        "deviceVariant": "SM-S911B",
        "softwareVersion": "public-kernel-1",
    })
    base.update(overrides)
    if "experiments" in overrides and "checksum" not in overrides:
        base["checksum"] = _GATE.protocol_checksum(base["experiments"])
    return base


class TCP15702(unittest.TestCase):
    def assert_contract(self, result, evidence="p157-instrumented-experiment-design"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P157-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unknown_proprietary_imaging_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["unknownComponents"], ["proprietary-imaging"])
        self.assertEqual(_MODULE.CASE["name"], "Incomplete public source")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "source-archive-called-complete-firmware")

    def test_calling_the_archive_complete_firmware_is_rejected(self):
        result = evaluate(payload(labelledCompleteCameraFirmware=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p157-instrumented-experiment-design", result["preservedResults"])

    def test_unknown_component_marked_inspectable_is_rejected(self):
        components = payload()["components"]
        components[1]["inspectable"] = True
        result = evaluate(payload(components=components))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNKNOWN_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p157-tc02-variant"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="software version",
            deviceVariant="SM-S916B",
            softwareVersion="public-kernel-2",
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][3]["deviceVariant"], "SM-S916B")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        components = payload()["components"]
        components[1]["evidence"] = "not-unknown"
        with self.assertRaises(ValueError):
            evaluate(payload(components=components))
