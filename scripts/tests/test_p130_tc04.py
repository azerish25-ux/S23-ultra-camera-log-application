"""Tests for TC-P130-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p130_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p130_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p130-tc04",
        "repeat": "waveform",
        "committed": _GATE.make_selection(),
        "proposed": _GATE.imax_proposal(),
        "measurementDomain": "waveform",
        "fresh": False,
        "certifiesSourceBitDepth": False,
        "certifiesSensorClipping": False,
    }
    base.update(overrides)
    return base


class TCP13004(unittest.TestCase):
    def assert_contract(self, result, evidence="p130-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P130-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_stale_scope_is_identified_without_certifying_the_sensor(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("freshness=stale", result["preservedResults"])
        self.assertIn("measurementDomain=waveform", result["preservedResults"])
        self.assertEqual(result["preservedResults"][1]["source_transfer"], "bt709")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "rgb8-preview-certifies-source-bit-depth-or-clipping")

    def test_rgb8_preview_cannot_certify_source_depth_or_clipping(self):
        result = evaluate(payload(
            measurementDomain="rgb8-preview",
            fresh=True,
            certifiesSourceBitDepth=True,
            certifiesSensorClipping=True,
            repeat="color histogram",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertNotIn(_MODULE.STALE_CERTIFIES, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)

    def test_stale_scope_that_reports_clipping_is_rejected(self):
        result = evaluate(payload(measurementDomain="source", certifiesSensorClipping=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STALE_CERTIFIES, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(measurementDomain="preview"))
