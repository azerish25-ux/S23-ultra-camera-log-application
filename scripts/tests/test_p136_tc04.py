"""Tests for TC-P136-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p136_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p136-tc04",
        "repeat": "histogram",
        "report": _GATE.honest_report(),
        "aid": "histogram",
        "sampleDomain": "preview-rgb8",
        "freshness": "delayed",
        "sourceClipped": False,
        "reportedSensorClipping": False,
        "sourceBitDepth": 10,
        "reportedBitDepth": None,
        "certifiesSource": False,
    }
    base.update(overrides)
    return base


class TCP13604(unittest.TestCase):
    def assert_contract(self, result, evidence="p136-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P136-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.CASE["name"], "Stale or wrong-domain scope")
        self.assertEqual(
            _MODULE.CASE["intervention"],
            "Feed a monitoring aid delayed preview samples or a display-clipped image from an unclipped source.",
        )
        self.assertEqual(
            _MODULE.CASE["expected"],
            "Identify freshness and measurement domain instead of falsely reporting sensor conditions.",
        )
        self.assertEqual(
            _MODULE.CASE["negative"],
            "An RGB8 preview histogram must not certify source bit depth or sensor clipping.",
        )
        self.assertEqual(
            _MODULE.CASE["repeat"],
            "Repeat waveform, false color, focus peaking, and color histogram.",
        )

    def test_labelled_rgb8_histogram_is_recorded_as_not_run(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        view = result["preservedResults"][2]
        self.assertEqual(view["sampleDomain"], "preview-rgb8")
        self.assertEqual(view["freshness"], "delayed")
        self.assertTrue(view["rgb8Histogram"])
        self.assertFalse(view["certifiesSource"])
        self.assertEqual(result["preservedResults"][1]["status"], "not-run")
        self.assertIsNone(result["preservedResults"][1]["shootingWorkflow"])

    def test_rgb8_histogram_certifying_source_is_rejected(self):
        result = evaluate(payload(certifiesSource=True, reportedBitDepth=10))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_preview_clipping_reported_as_sensor_is_rejected(self):
        result = evaluate(payload(aid="false-color", sampleDomain="display", reportedSensorClipping=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.WRONG_DOMAIN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_screenshot_approval_is_rejected(self):
        result = evaluate(payload(report=_GATE.honest_report(approved=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.DESKTOP_SCREENSHOT_APPROVAL, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p136-tc04-waveform"
        result = evaluate(
            payload(
                evidenceId=evidence,
                repeat="waveform",
                aid="waveform",
                sampleDomain="source",
                freshness="fresh",
                sourceClipped=True,
                reportedSensorClipping=True,
            )
        )
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(aid="vectorscope"))
        with self.assertRaises(ValueError):
            evaluate(payload(sourceBitDepth=True))
