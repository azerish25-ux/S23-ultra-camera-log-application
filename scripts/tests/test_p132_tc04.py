"""Tests for TC-P132-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p132_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p132_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p132-tc04",
        "repeat": "waveform",
        "scopes": _GATE.fixture_scopes(),
        "source": _GATE.fixture_source(),
        "applyMutant": False,
        "reportedDomain": "display_sdr",
        "reportedFresh": False,
        "certifiesSourceBitDepth": False,
        "certifiesSensorClipping": False,
    }
    base.update(overrides)
    return base


class TCP13204(unittest.TestCase):
    def assert_contract(self, result, evidence="p132-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P132-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_stale_display_waveform_is_identified_without_source_clipping(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("freshness=stale", result["preservedResults"])
        self.assertIn("measurementDomain=display_sdr", result["preservedResults"])
        self.assertEqual(result["preservedResults"][1]["sourceClippingCount"], 0)
        self.assertEqual(result["preservedResults"][1]["previewClippingCount"], 3)
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "rgb8-preview-certifies-source-bit-depth-or-clipping")

    def test_rgb8_preview_cannot_certify_source_depth_or_clipping(self):
        result = evaluate(payload(
            certifiesSourceBitDepth=True,
            certifiesSensorClipping=True,
            repeat="color histogram",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["previewClippingCount"], 3)

    def test_scope_flags_that_certify_rgb8_precision_are_rejected(self):
        scopes = _GATE.replace_scope(
            _GATE.fixture_scopes(),
            "preview-histogram",
            certifiesSensorClipping=True,
            certifiesSourceBitDepth=True,
        )
        result = evaluate(payload(scopes=scopes))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.RGB8_CERTIFIES_SENSOR, result["rejectedClaims"])
        self.assertIn(_GATE.RGB8_CERTIFIES_BIT_DEPTH, result["rejectedClaims"])

    def test_wrong_domain_or_hidden_staleness_is_rejected(self):
        domain = evaluate(payload(reportedDomain="sensor_code"))
        self.assertEqual(domain["decision"], "rejected")
        self.assertIn(_MODULE.WRONG_DOMAIN, domain["rejectedClaims"])
        fresh = evaluate(payload(reportedFresh=True))
        self.assertEqual(fresh["decision"], "rejected")
        self.assertIn(_MODULE.FRESHNESS_MISREPORTED, fresh["rejectedClaims"])
        self.assertEqual(fresh["preservedResults"][1]["sourceClippingCount"], 0)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(reportedDomain="preview"))
