"""Tests for TC-P125-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p125_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p125_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
FROZEN = {"stock": "neutral", "focus": 10, "grain-seed": 7, "output-range": "legal", "source-interpretation": "raw"}


def payload(**overrides):
    base = {
        "evidenceId": "p125-recipe",
        "repeat": "focus",
        "frozenRecipe": dict(FROZEN),
        "liveSliders": dict(FROZEN),
        "frameValues": [dict(FROZEN), dict(FROZEN)],
        "newVersionCreated": False,
    }
    base.update(overrides)
    return base


class TCP12502(unittest.TestCase):
    def assert_contract(self, result, evidence="p125-recipe"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P125-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Mutable recipe during export")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Reading live slider values for successive output frames must fail.",
        )
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat stock, focus, grain seed, output range, and source interpretation changes.",
        )

    def test_frozen_frames_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["driftedFrames"], [])

    def test_live_slider_frames_are_rejected(self):
        live = dict(FROZEN)
        live["focus"] = 4
        drifted = dict(live)
        result = evaluate(payload(liveSliders=live, frameValues=[dict(FROZEN), drifted], newVersionCreated=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["frozenRecipe"]["focus"], 10)
        self.assertEqual(result["preservedResults"][1]["driftedFrames"], [1])

    def test_slider_change_without_a_new_version_is_rejected(self):
        live = dict(FROZEN)
        live["grain-seed"] = 9
        result = evaluate(payload(repeat="grain-seed", liveSliders=live, newVersionCreated=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.VERSION_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.LIVE_TOKEN, result["rejectedClaims"])

    def test_new_version_keeps_the_running_job_frozen(self):
        live = dict(FROZEN)
        live["output-range"] = "full"
        result = evaluate(
            payload(repeat="output-range", liveSliders=live, newVersionCreated=True, evidenceId="p125-version")
        )
        self.assert_contract(result, "p125-version")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["frameCount"], 2)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frameValues=[]))
