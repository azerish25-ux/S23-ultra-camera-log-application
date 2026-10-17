"""Tests for TC-P135-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p135_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p135_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p135-tc04",
        "repeat": "waveform",
        "comparison": _GATE.make_comparison(),
        "measurementDomain": "waveform",
        "fresh": True,
        "certifiesSourceBitDepth": False,
        "certifiesSensorClipping": False,
    }
    base.update(overrides)
    return base


class TCP13504(unittest.TestCase):
    def assert_contract(self, result, evidence="p135-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P135-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_fresh_waveform_does_not_certify_the_sensor(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("measurementDomain=waveform", result["preservedResults"])
        self.assertIn("freshness=fresh", result["preservedResults"])
        self.assertTrue(result["preservedResults"][1]["matchedInputs"])

    def test_rgb8_preview_cannot_certify_source_depth_or_clipping(self):
        result = evaluate(payload(
            measurementDomain="rgb8-preview",
            certifiesSourceBitDepth=True,
            certifiesSensorClipping=True,
            repeat="color histogram",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_stale_scope_cannot_report_sensor_conditions(self):
        result = evaluate(payload(
            measurementDomain="source",
            fresh=False,
            certifiesSensorClipping=True,
            repeat="false color",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STALE_CERTIFIES, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_fresh_source_domain_may_describe_the_source(self):
        result = evaluate(payload(
            measurementDomain="focus-peaking",
            fresh=True,
            certifiesSourceBitDepth=False,
            certifiesSensorClipping=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(measurementDomain="histogram"))
