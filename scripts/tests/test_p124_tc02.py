"""Tests for TC-P124-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p124_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p124_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
FROZEN = "eadc91002f653754d1de6d142ef034fb6acb64da1d9e4aa54a126b0beb5fbbc5"
LIVE = "42da64428d7b7bd8d5f57fa2c1645c3054795a07f3ec2a60b8702282bd994753"


def payload(**overrides):
    base = {
        "evidenceId": "p124-evidence",
        "repeat": "Repeat",
        "jobId": "job-running",
        "frozenRecipeSha256": FROZEN,
        "liveRecipeSha256": FROZEN,
        "frameRecipes": [FROZEN, FROZEN],
        "newVersionId": None,
    }
    base.update(overrides)
    return base


class TCP12402(unittest.TestCase):
    def assert_contract(self, result, evidence="p124-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P124-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("frozenRecipeSha256=" + FROZEN, result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_frozen_recipe_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_live_slider_frames_are_rejected(self):
        result = evaluate(payload(liveRecipeSha256=LIVE, frameRecipes=[FROZEN, LIVE], newVersionId="job-v2"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LIVE_SLIDER, result["rejectedClaims"])
        self.assertIn("p124-evidence", result["preservedResults"])

    def test_live_change_without_a_new_version_is_rejected(self):
        result = evaluate(payload(liveRecipeSha256=LIVE, frameRecipes=[FROZEN, FROZEN], newVersionId=None))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RECIPE_CHANGE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.LIVE_SLIDER, result["rejectedClaims"])

    def test_new_version_keeps_running_frames_frozen(self):
        result = evaluate(payload(liveRecipeSha256=LIVE, frameRecipes=[FROZEN, FROZEN], newVersionId="job-v2"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("subsequent edits use new version job-v2", result["reasons"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p124-grain"
        result = evaluate(payload(evidenceId=evidence, repeat="grain"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
