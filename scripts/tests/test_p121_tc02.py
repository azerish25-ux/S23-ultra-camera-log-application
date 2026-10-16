"""Tests for TC-P121-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p121_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p121_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p121-recipe",
        "repeat": "stock",
        "parameter": "stock",
        "frozenValue": "kodak-2383",
        "liveValue": "kodak-2383",
        "jobStarted": True,
        "framesUsedLiveValue": False,
        "editAfterStart": False,
    }
    base.update(overrides)
    return base


class TCP12102(unittest.TestCase):
    def assert_contract(self, result, evidence="p121-recipe"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P121-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Mutable recipe during export")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Change UI parameters after a render has begun but before it finishes.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Keep the running job bound to its frozen recipe and create a new version for subsequent edits.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "Reading live slider values for successive output frames must fail.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat stock, focus, grain seed, output range, and source interpretation changes.",
        )

    def test_running_job_stays_on_the_frozen_recipe(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["boundValue"], "kodak-2383")
        self.assertIsNone(kept["newVersion"])

    def test_live_slider_frames_are_rejected(self):
        result = evaluate(payload(liveValue="kodak-2393", framesUsedLiveValue=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["boundValue"], "kodak-2383")
        self.assertEqual(result["preservedResults"][1]["liveValue"], "kodak-2393")

    def test_edit_after_start_creates_a_new_version(self):
        result = evaluate(
            payload(
                evidenceId="p121-grain",
                repeat="grain-seed",
                parameter="grain-seed",
                frozenValue="17",
                liveValue="18",
                editAfterStart=True,
            )
        )
        self.assert_contract(result, "p121-grain")
        self.assertEqual(result["decision"], "recorded")
        kept = result["preservedResults"][1]
        self.assertEqual(kept["boundValue"], "17")
        self.assertEqual(kept["newVersion"], "17+v2")

    def test_focus_and_unversioned_drift(self):
        focus = evaluate(
            payload(
                repeat="focus",
                parameter="focus",
                frozenValue="0.35",
                liveValue="0.35",
            )
        )
        self.assertEqual(focus["decision"], "recorded")
        drift = evaluate(payload(liveValue="kodak-2393"))
        self.assertEqual(drift["decision"], "rejected")
        self.assertIn("unversioned-recipe-drift", drift["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(repeat="focus"))
        with self.assertRaises(ValueError):
            evaluate(payload(jobStarted="yes"))
