"""Tests for TC-P133-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p133_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p133_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def surface(state):
    progress = _GATE.make_control(
        "development-progress",
        "Development progress",
        "button",
        "button",
        family="monitoring",
        state_description=state,
    )
    return _GATE.fixture_controls() + [progress], _GATE.fixture_focus_order() + [progress["id"]]


def payload(state="remaining stage verification", **overrides):
    controls, order = surface(state)
    base = {
        "evidenceId": "p133-tc06",
        "repeat": "encoder drain",
        "controls": controls,
        "focusOrder": order,
        "progressControlId": "development-progress",
        "progressBannerPercent": 40,
        "verificationComplete": False,
        "publicationComplete": False,
        "remainingStage": "verification",
    }
    base.update(overrides)
    return base


class TCP13306(unittest.TestCase):
    def assert_contract(self, result, evidence="p133-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P133-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_remaining_stage_is_spoken_before_completion(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["remainingStage"], "verification")
        self.assertFalse(result["preservedResults"][2]["gatesPassed"])
        self.assertIn("verification", result["preservedResults"][2]["spokenState"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "premature-complete-banner")

    def test_one_hundred_percent_banner_before_verification_is_rejected(self):
        result = evaluate(payload(progressBannerPercent=100, repeat="full decode"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p133-tc06", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_spoken_complete_before_the_gate_is_rejected(self):
        result = evaluate(
            payload("complete", progressBannerPercent=80, remainingStage="sidecar-export", repeat="sidecar export")
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.STAGE_UNSPOKEN, result["rejectedClaims"])

    def test_completion_after_verification_and_publication_is_recorded(self):
        result = evaluate(
            payload(
                "complete",
                progressBannerPercent=100,
                verificationComplete=True,
                publicationComplete=True,
                remainingStage=None,
                repeat="gallery commit",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][2]["gatesPassed"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(progressBannerPercent=101))
        with self.assertRaises(ValueError):
            evaluate(payload(remainingStage="done"))
