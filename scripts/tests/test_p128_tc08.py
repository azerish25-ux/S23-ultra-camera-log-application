"""Tests for TC-P128-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p128_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p128_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
PRIVATE = "/home/ada/private/take.mov"


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
        "bundleKind": "log",
        "privatePaths": [PRIVATE],
        "redactedReport": "interpretation=LogC3-EI800 recipe=frozen-v1 signal=logc3 source=redacted",
        "interpretationRecordPresent": True,
        "signalMetadataPresent": True,
        "recipeMetadataPresent": True,
        "presentedAsComplete": True,
    }
    base.update(_long_form())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12808(unittest.TestCase):
    def assert_contract(self, result, evidence="p128-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P128-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("frameAccount=", blob(result))
        self.assertTrue(result["reasons"])

    def test_log_master_keeps_interpretation_and_redacts_paths(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("log interpretation record retained", result["reasons"])
        self.assertIn("personal paths redacted", result["reasons"])
        self.assertIn("frameAccount=6/6", blob(result))

    def test_log_master_without_interpretation_is_rejected(self):
        result = evaluate(payload(interpretationRecordPresent=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_private_path_in_the_report_is_rejected(self):
        result = evaluate(payload(redactedReport="source=" + PRIVATE + " interpretation=LogC3-EI800"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LEAK_TOKEN, result["rejectedClaims"])

    def test_rendered_sdr_does_not_require_a_log_record(self):
        result = evaluate(payload(
            bundleKind="sdr",
            interpretationRecordPresent=False,
            redactedReport="signal=rec709 recipe=frozen-v1 source=redacted",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_partial_export_presented_as_complete_is_rejected(self):
        result = evaluate(payload(
            bundleKind="partial",
            interpretationRecordPresent=False,
            signalMetadataPresent=False,
            recipeMetadataPresent=False,
            presentedAsComplete=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PARTIAL_TOKEN, result["rejectedClaims"])

    def test_unverified_partial_export_can_stay_incomplete(self):
        result = evaluate(payload(
            bundleKind="partial",
            interpretationRecordPresent=False,
            signalMetadataPresent=False,
            recipeMetadataPresent=False,
            presentedAsComplete=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_duplicate_frame_is_rejected_inside_the_case(self):
        result = evaluate(payload(accounted_frames=[5, 4, 3, 2, 1, 0, 0]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-frame-index", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p128-hdr"
        result = evaluate(payload(evidenceId=evidence, repeat="hdr-derived", bundleKind="hdr-derived"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
