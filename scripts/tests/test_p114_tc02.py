"""Tests for TC-P114-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p114_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p114-evidence",
        "repeat": "short exposure",
        "shutter_angle_degrees": 180.0,
        "fps": 24.0,
        "contains_estimated": False,
        "disclosed": True,
        "labelled_as_longer_sensor_exposure": False,
        "frames": [{"origin": "captured", "weight": 1.0}],
        "source_blur": "short",
        "claim_exact_conversion": False,
        "unsupported_labelled": False,
    }
    base.update(overrides)
    return base


class TCP11402(unittest.TestCase):
    def assert_contract(self, result, evidence="p114-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P114-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_short_exposure_additional_processing_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_exact_conversion_from_any_source_is_rejected(self):
        for blur in ("short", "long", "undersampled_thin"):
            result = evaluate(payload(
                source_blur=blur,
                claim_exact_conversion=True,
                unsupported_labelled=True,
                repeat=blur,
            ))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "rejected")
            self.assertIn("exact-arbitrary-shutter-conversion", result["rejectedClaims"])

    def test_blurred_and_undersampled_sources_must_be_labelled_unsupported(self):
        labelled = evaluate(payload(source_blur="long", unsupported_labelled=True, repeat="long exposure"))
        self.assertEqual(labelled["decision"], "recorded")
        self.assertTrue(any("unsupported reconstruction labelled" in item for item in labelled["reasons"]))
        hidden = evaluate(payload(source_blur="undersampled_thin", unsupported_labelled=False, repeat="undersampled thin motion"))
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn("unsupported-reconstruction-unlabelled", hidden["rejectedClaims"])
        self.assertIn("p114-evidence", hidden["preservedResults"])

    def test_scope_rules_still_reject_hidden_and_unnormalized_input(self):
        hidden = evaluate(payload(
            frames=[{"origin": "estimated", "weight": 1.0}],
            contains_estimated=True,
            disclosed=False,
        ))
        self.assertIn("hidden-hallucination", hidden["rejectedClaims"])
        weights = evaluate(payload(frames=[{"origin": "captured", "weight": 0.2}]))
        self.assertIn("unnormalized-temporal-weights", weights["rejectedClaims"])
        labelled = evaluate(payload(labelled_as_longer_sensor_exposure=True))
        self.assertIn("labelled-as-longer-sensor-exposure", labelled["rejectedClaims"])
        missing = evaluate(payload(shutter_angle_degrees=None))
        self.assertIn("missing-shutter-angle", missing["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p114-long"
        result = evaluate(payload(evidenceId=evidence, source_blur="long", unsupported_labelled=True, repeat="long exposure"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(source_blur="medium"))
