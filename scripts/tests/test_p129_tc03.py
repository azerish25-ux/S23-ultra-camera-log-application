"""Tests for TC-P129-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p129_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p129_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p129-tc03",
        "repeat": "shutter",
        "control": "shutter",
        "committed": 180.0,
        "draft": "18.",
        "minimum": 1.0,
        "maximum": 360.0,
        "applied": False,
        "cameraValue": 180.0,
        "capture": ["record", "stop"],
        "monitoring": [],
        "processing": ["manual-controls"],
        "warnings": ["storage"],
        "record_in_scroll_only": False,
        "warnings_visible": True,
    }
    base.update(overrides)
    return base


class TCP12903(unittest.TestCase):
    def assert_contract(self, result, evidence="p129-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P129-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Invalid control draft")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Enter an incomplete or out-of-range numeric value and interrupt editing before Apply.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Preserve committed settings and keep the draft visibly unapplied or invalid.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "Partially typed input reaching the camera must fail.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat shutter, ISO, focus distance, ROI coordinates, and output dimensions.",
        )

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("committed=180", result["preservedResults"])
        self.assertIn("draft=18.", result["preservedResults"])
        self.assertIn("draft is visibly invalid", result["reasons"])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(cameraValue=18.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("committed=180", result["preservedResults"])
        self.assertIn("p129-tc03", result["preservedResults"])

    def test_out_of_range_apply_is_rejected(self):
        result = evaluate(payload(draft=900, applied=True, cameraValue=900))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("committed=180", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(committed=0))
