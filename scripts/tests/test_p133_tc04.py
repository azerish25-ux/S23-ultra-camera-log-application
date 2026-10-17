"""Tests for TC-P133-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p133_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p133_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def histogram(state):
    return _GATE.make_control(
        "color-histogram",
        "Color histogram",
        "button",
        "button",
        family="monitoring",
        state_description=state,
    )


def payload(state="domain rgb8-preview; freshness fresh; not a sensor measurement", **overrides):
    aid = histogram(state)
    base = {
        "evidenceId": "p133-tc04",
        "repeat": "color histogram",
        "controls": _GATE.fixture_controls() + [aid],
        "focusOrder": _GATE.fixture_focus_order() + [aid["id"]],
        "aidId": aid["id"],
        "measurementDomain": "rgb8-preview",
        "fresh": True,
        "certifiesSourceBitDepth": False,
        "certifiesSensorClipping": False,
    }
    base.update(overrides)
    return base


class TCP13304(unittest.TestCase):
    def assert_contract(self, result, evidence="p133-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P133-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_rgb8_preview_does_not_certify_the_sensor(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("color-histogram", result["preservedResults"][1]["focusOrder"])
        self.assertEqual(result["preservedResults"][4]["measurementDomain"], "rgb8-preview")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "rgb8-preview-certifies-source-bit-depth-or-clipping")

    def test_rgb8_histogram_that_certifies_bit_depth_is_rejected(self):
        result = evaluate(payload(certifiesSourceBitDepth=True, repeat="waveform"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p133-tc04", result["preservedResults"])

    def test_spoken_certification_is_rejected_even_when_the_flag_is_false(self):
        result = evaluate(
            payload(
                "domain rgb8-preview; freshness fresh; certifies sensor clipping",
                repeat="false color",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_stale_scope_cannot_report_sensor_clipping(self):
        result = evaluate(
            payload(
                "domain rgb8-preview; freshness stale; display clip only",
                fresh=False,
                certifiesSensorClipping=True,
                repeat="focus peaking",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STALE_CERTIFIES, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(measurementDomain="sensor-raw"))
        with self.assertRaises(ValueError):
            evaluate(payload(aidId="record"))
