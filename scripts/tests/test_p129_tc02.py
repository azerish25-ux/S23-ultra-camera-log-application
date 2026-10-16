"""Tests for TC-P129-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p129_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p129_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p129-tc02",
        "repeat": "preset-change",
        "sourceMode": "1080p-sdr",
        "displayedSource": "1080p-sdr",
        "sourceEvidence": "experimental",
        "lookName": "large-format-film",
        "lookEvidence": "simulated",
        "capture": ["record", "stop", "source-mode"],
        "monitoring": [],
        "processing": ["large-format-film"],
        "warnings": ["storage"],
        "record_in_scroll_only": False,
        "warnings_visible": True,
    }
    base.update(overrides)
    return base


class TCP12902(unittest.TestCase):
    def assert_contract(self, result, evidence="p129-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P129-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Source-look label confusion")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Select a large-format film recipe while the underlying source remains a lower-resolution SDR or experimental RAW route.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Display the actual source and simulated look independently with their evidence status.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "Renaming a source mode after the virtual format must fail.")
        self.assertEqual(_MODULE.REPEAT, "Repeat preset changes, saved recipe reopening, and export sharing.")

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source=1080p-sdr:experimental", result["preservedResults"])
        self.assertIn("look=large-format-film:simulated", result["preservedResults"])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(displayedSource="large-format-film"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("source=1080p-sdr:experimental", result["preservedResults"])
        self.assertIn("p129-tc02", result["preservedResults"])

    def test_shared_source_identity_with_processing_is_rejected(self):
        result = evaluate(payload(processing=["source-mode"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("shared-control-identity", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sourceEvidence="renamed"))
