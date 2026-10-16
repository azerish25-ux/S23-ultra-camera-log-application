"""Tests for TC-P129-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p129_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p129_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p129-tc01",
        "repeat": "landscape-large-text",
        "fontScale": 1.5,
        "orientation": "landscape",
        "advancedOpen": True,
        "activeTake": True,
        "sourceStatusReachable": True,
        "warningsReadable": True,
        "viewfinderReplaced": False,
        "capture": ["record", "stop", "source-mode", "exposure", "audio"],
        "monitoring": ["microphone-meters"],
        "processing": ["manual-controls"],
        "warnings": ["storage", "audio"],
        "record_in_scroll_only": False,
        "warnings_visible": True,
    }
    base.update(overrides)
    return base


class TCP12901(unittest.TestCase):
    def assert_contract(self, result, evidence="p129-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P129-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Landscape and large-text stress")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Open advanced controls with increased font scale in landscape during an active take.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Keep Record or Stop, essential warnings, and selected source status reachable and readable.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "Critical actions hidden inside scrolling content must fail.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat small display settings, orientation changes, and simultaneous audio and storage warnings.",
        )

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("capture=record,stop,source-mode,exposure,audio", result["preservedResults"])
        self.assertIn("warnings=storage,audio", result["preservedResults"])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(record_in_scroll_only=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("p129-tc01", result["preservedResults"])

    def test_stop_only_in_processing_is_rejected(self):
        result = evaluate(payload(
            capture=["record", "source-mode"],
            processing=["stop", "manual-controls"],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_unreadable_warning_and_hidden_source_are_rejected(self):
        result = evaluate(payload(sourceStatusReachable=False, warningsReadable=False, fontScale=1.0, orientation="portrait"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SOURCE_UNREACHABLE, result["rejectedClaims"])
        self.assertIn(_MODULE.WARNINGS_UNREADABLE, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(fontScale=0))
