"""Tests for TC-P112-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p112_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p112_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
BRIGHTNESS = [0.40, 0.42, 0.41, 0.43, 0.40, 0.44, 0.41, 0.42]
EDGE = [0.80, 0.81, 0.79, 0.82, 0.78, 0.80, 0.81, 0.79]
FOCUS = [2.0, 2.0, 2.1, 2.1, 2.0, 2.2, 2.2, 2.0]


def frames(severity=0.1):
    rows = []
    for index in range(8):
        boundary = severity[index] if isinstance(severity, list) else severity
        rows.append({
            "edge_energy": EDGE[index],
            "brightness": BRIGHTNESS[index],
            "focus_distance": FOCUS[index],
            "boundary_severity": boundary,
        })
    return rows


def payload(**overrides):
    base = {
        "evidenceId": "p112-tc08",
        "repeat": "moderate-blur",
        "claim": "synthetic-host-fixture",
        "playback_fps": 24,
        "frames": frames(),
        "flicker_limit": 0.05,
        "edge_crawl_limit": 0.05,
        "severity_limit": 1.0,
        "still_as_playback": False,
        "still_sharpness": 0.92,
        "measured_on_device": False,
        "claims_physical_lens_qualification": False,
        "applyMutant": False,
    }
    base.update(overrides)
    return base


class TCP11208(unittest.TestCase):
    def assert_contract(self, result, evidence="p112-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P112-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("focus_distance_variance=") for item in result["preservedResults"]))
        self.assertTrue(any(item.startswith("flicker=") for item in result["preservedResults"]))
        self.assertTrue(any(item.startswith("edge_crawl=") for item in result["preservedResults"]))

    def test_whole_clip_inside_limits_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_favorable_mean_cannot_hide_a_severe_frame(self):
        severity = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 5.0]
        result = evaluate(payload(frames=frames(severity)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("severe-boundary-failure-not-averaged-into-a-pass", result["rejectedClaims"])
        text = " ".join(result["preservedResults"])
        self.assertIn("mean_boundary_severity=", text)
        self.assertIn("peak_boundary_severity=", text)

    def test_still_frames_and_mutant_are_rejected(self):
        evidence = "p112-tc08-stills"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="aggressive-blur",
            still_as_playback=True,
            applyMutant=True,
            still_sharpness=50.0,
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("still-frame-sharpness-cannot-qualify-playback", result["rejectedClaims"])
        self.assertTrue(any("selected still frames" in item for item in result["rejectedClaims"]))

    def test_short_clip_is_rejected(self):
        result = evaluate(payload(frames=frames()[:7], playback_fps=30))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("frame-count-below-playback-minimum", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(playback_fps=48))
