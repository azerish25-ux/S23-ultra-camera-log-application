"""Tests for TC-P128-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p128_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p128_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _long_form(**overrides):
    value = {
        "expected_frames": 6,
        "accounted_frames": [0, 1, 2, 3, 4, 5],
        "checkpoint_frames": [0, 2, 5],
        "audio_duration": 0.25,
        "video_duration": 0.25,
        "audio_absent": False,
        "spot_check_only": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p128-evidence",
        "repeat": "Repeat",
        "thumbnailPresent": True,
        "sourceGrant": "revoked",
        "sourceFilePresent": False,
        "historicalMetadataPreserved": True,
        "availability": "unavailable",
    }
    base.update(_long_form())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12806(unittest.TestCase):
    def assert_contract(self, result, evidence="p128-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P128-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("frameAccount=", blob(result))
        self.assertTrue(result["reasons"])

    def test_revoked_source_keeps_the_thumbnail_unavailable(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("actualAvailability=unavailable", result["preservedResults"])
        self.assertIn("thumbnail retained; not treated as accessible media", result["reasons"])
        self.assertIn("historical metadata preserved", result["reasons"])

    def test_granted_file_is_available(self):
        result = evaluate(payload(
            sourceGrant="granted",
            sourceFilePresent=True,
            availability="available",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("actualAvailability=available", result["preservedResults"])

    def test_thumbnail_does_not_certify_a_revoked_source(self):
        result = evaluate(payload(availability="available"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_dropped_historical_metadata_is_rejected(self):
        result = evaluate(payload(historicalMetadataPreserved=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.METADATA_TOKEN, result["rejectedClaims"])

    def test_duplicate_frame_is_rejected_inside_the_case(self):
        result = evaluate(payload(accounted_frames=[0, 1, 2, 3, 3, 4, 5]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-frame-index", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p128-grant"
        result = evaluate(payload(evidenceId=evidence, repeat="grant"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
