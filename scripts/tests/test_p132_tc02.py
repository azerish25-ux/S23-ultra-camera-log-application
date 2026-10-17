"""Tests for TC-P132-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p132_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p132_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p132-tc02",
        "repeat": "preset changes",
        "scopes": _GATE.fixture_scopes(),
        "source": _GATE.fixture_source(),
        "applyMutant": False,
        "displayedSourceDomain": "sensor_code",
        "displayedHistogramDomain": "display_sdr",
        "displayedHistogramLabel": "display_preview",
        "virtualFormatName": "large-format-simulated",
        "sourceEvidenceStatus": "not-qualified",
        "lookEvidenceStatus": "simulated",
    }
    base.update(overrides)
    return base


class TCP13202(unittest.TestCase):
    def assert_contract(self, result, evidence="p132-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P132-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_source_domain_and_display_histogram_stay_independent(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["sourceDomain"], "sensor_code")
        self.assertEqual(result["preservedResults"][1]["previewClippingCount"], 3)

    def test_renaming_the_source_after_the_virtual_format_is_rejected(self):
        result = evaluate(payload(displayedSourceDomain="large-format-simulated"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["sourceClippingCount"], 0)

    def test_qualified_evidence_status_is_rejected(self):
        result = evaluate(payload(lookEvidenceStatus="qualified"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.EVIDENCE_QUALIFIED, result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_collapsing_source_and_look_labels_is_rejected(self):
        scopes = _GATE.replace_scope(
            _GATE.fixture_scopes(),
            "preview-histogram",
            label="sensor_code",
            sampleEncoding="unspecified",
            samples=[0.2, 0.4],
            samplingResolution="ten_bit",
        )
        result = evaluate(payload(
            scopes=scopes,
            displayedHistogramLabel="sensor_code",
            displayedSourceDomain="sensor_code",
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOOK_HIDDEN, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(displayedSourceDomain=""))
