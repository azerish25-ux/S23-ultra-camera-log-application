"""Tests for TC-P134-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p134_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p134_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    progress = overrides.pop(
        "progress",
        _GATE.fixture_progress(
            success=False,
            failure_reason="thermal warning interrupted gallery publication",
            failure_kind="retained-recoverable-footage",
            footage_retained=True,
        ),
    )
    base = {
        "evidenceId": "p134-tc08",
        "repeat": "one-handed operation",
        "progress": progress,
        "physicalObserved": False,
        "desktopMockupSubstituted": False,
        "savedFootageDisclosed": True,
        "interruption": "thermal",
        "nextAction": "review retained footage",
    }
    base.update(overrides)
    return base


class TCP13408(unittest.TestCase):
    def assert_contract(self, result, evidence="p134-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P134-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_disclosed_save_is_recorded_without_a_physical_claim(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["success"], False)
        self.assertTrue(result["preservedResults"][1]["footage_retained"])
        self.assertEqual(
            result["preservedResults"][1]["failure_reason"],
            "thermal warning interrupted gallery publication",
        )
        self.assertIsNone(result["preservedResults"][1]["fraction"])

    def test_desktop_mockup_cannot_substitute_for_the_phone(self):
        result = evaluate(payload(desktopMockupSubstituted=True, repeat="outdoor visibility"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_claimed_physical_observation_is_rejected(self):
        result = evaluate(payload(physicalObserved=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNOBSERVED, result["rejectedClaims"])

    def test_hidden_save_is_rejected_and_the_reason_remains(self):
        result = evaluate(payload(savedFootageDisclosed=False, repeat="finding an interrupted take"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HIDDEN_SAVE, result["rejectedClaims"])
        self.assertEqual(
            result["preservedResults"][1]["failure_kind"],
            "retained-recoverable-footage",
        )

    def test_failure_without_a_reason_raises(self):
        progress = _GATE.fixture_progress(success=False, failure_reason=None, failure_kind=None)
        with self.assertRaises(ValueError):
            evaluate(payload(progress=progress))

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(interruption="crash"))
