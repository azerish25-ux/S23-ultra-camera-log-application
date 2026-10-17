"""Tests for TC-P134-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p134_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p134_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p134-tc06",
        "repeat": "encoder drain",
        "progress": _GATE.fixture_progress(),
        "remainingStage": "encoder-drain",
        "sidecarExported": False,
    }
    base.update(overrides)
    return base


class TCP13406(unittest.TestCase):
    def assert_contract(self, result, evidence="p134-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P134-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_final_frame_keeps_encoder_drain_visible(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("remainingStage=encoder-drain", result["preservedResults"])
        self.assertIsNone(result["preservedResults"][1]["fraction"])
        self.assertFalse(result["preservedResults"][1]["drain_complete"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "premature-complete-banner")

    def test_one_hundred_percent_before_drain_is_rejected(self):
        progress = _GATE.fixture_progress(displayed_percent=100, success=True)
        result = evaluate(payload(progress=progress, repeat="gallery commit"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_GATE.HUNDRED_BEFORE_DRAIN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIsNone(result["preservedResults"][1]["fraction"])

    def test_one_hundred_percent_before_verification_is_rejected(self):
        progress = _GATE.fixture_progress(
            stage="verification",
            drain_complete=True,
            displayed_percent=100,
            success=None,
            verification_complete=False,
            publication_complete=False,
        )
        result = evaluate(payload(progress=progress, remainingStage="full-decode", repeat="full decode"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["fraction"], 1.0)
        self.assertFalse(result["preservedResults"][1]["acceptance_satisfied"])

    def test_accepted_publication_is_recorded_not_qualified(self):
        progress = _GATE.fixture_progress(
            stage="publication",
            drain_complete=True,
            displayed_percent=100,
            success=True,
            verification_complete=True,
            publication_complete=True,
        )
        result = evaluate(payload(
            progress=progress,
            remainingStage=None,
            sidecarExported=True,
            repeat="sidecar export",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("remainingStage=none", result["preservedResults"])
        self.assertTrue(result["preservedResults"][1]["acceptance_satisfied"])

    def test_hidden_remaining_stage_is_rejected(self):
        result = evaluate(payload(remainingStage=None))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.REMAINING_HIDDEN, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(remainingStage="done"))
        with self.assertRaises(ValueError):
            evaluate(payload(progress=_GATE.fixture_progress(displayed_percent=140)))
