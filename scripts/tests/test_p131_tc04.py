"""Tests for TC-P131-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p131_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p131_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p131-tc04",
        "repeat": "histogram",
        "committed": _GATE.make_control(observed=171),
        "proposed": _GATE.held_proposal(observed=171),
        "measurementDomain": "rgb8-preview",
        "fresh": False,
        "certifiesSourceBitDepth": False,
        "certifiesSensorClipping": False,
    }
    base.update(overrides)
    return base


class TCP13104(unittest.TestCase):
    def assert_contract(self, result, evidence="p131-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P131-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_stale_scope_is_identified_without_certifying_the_sensor(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("measurementDomain=rgb8-preview", result["preservedResults"])
        self.assertIn("freshness=stale", result["preservedResults"])
        self.assertEqual(result["preservedResults"][1]["observed"], 171)
        self.assertEqual(result["preservedResults"][1]["applied"], 180)
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "rgb8-preview-certifies-source-bit-depth-or-clipping")

    def test_rgb8_preview_cannot_certify_source_depth_or_clipping(self):
        result = evaluate(payload(fresh=True, certifiesSourceBitDepth=True, certifiesSensorClipping=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["applied"], 180)
        self.assertEqual(result["preservedResults"][1]["observed"], 171)

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p131-tc04-waveform"
        result = evaluate(
            payload(evidenceId=evidence, repeat="waveform", measurementDomain="waveform", fresh=True)
        )
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(measurementDomain="sensor-bits"))
