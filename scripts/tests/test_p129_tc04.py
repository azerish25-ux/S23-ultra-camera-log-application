"""Tests for TC-P129-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p129_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p129_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p129-tc04",
        "repeat": "histogram",
        "aid": "histogram",
        "freshnessSeconds": 1.0,
        "domain": "preview-rgb8",
        "claimedSourceBitDepth": None,
        "reportsSensorClipping": False,
        "sourceClipped": False,
        "displayClipped": True,
        "capture": ["record", "stop"],
        "monitoring": ["histogram"],
        "processing": [],
        "warnings": ["storage"],
        "record_in_scroll_only": False,
        "warnings_visible": True,
    }
    base.update(overrides)
    return base


class TCP12904(unittest.TestCase):
    def assert_contract(self, result, evidence="p129-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P129-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Stale or wrong-domain scope")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Feed a monitoring aid delayed preview samples or a display-clipped image from an unclipped source.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Identify freshness and measurement domain instead of falsely reporting sensor conditions.",
        )
        self.assertEqual(
            _MODULE.NEGATIVE,
            "An RGB8 preview histogram must not certify source bit depth or sensor clipping.",
        )
        self.assertEqual(_MODULE.REPEAT, "Repeat waveform, false color, focus peaking, and color histogram.")

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("domain=preview-rgb8", result["preservedResults"])
        self.assertIn("freshness=stale", result["preservedResults"])
        self.assertIn("claimedSourceBitDepth=none", result["preservedResults"])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(claimedSourceBitDepth=8, reportsSensorClipping=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("p129-tc04", result["preservedResults"])

    def test_display_clip_is_not_sensor_clip(self):
        result = evaluate(payload(
            aid="waveform",
            domain="display",
            freshnessSeconds=0.0,
            reportsSensorClipping=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.WRONG_DOMAIN_CLIP, result["rejectedClaims"])
        self.assertIn("freshness=fresh", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(domain="sensor-clip"))
