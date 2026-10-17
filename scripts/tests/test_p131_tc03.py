"""Tests for TC-P131-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p131_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p131_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p131-tc03",
        "repeat": "shutter",
        "committed": _GATE.make_control(),
        "proposed": _GATE.held_proposal(),
    }
    base.update(overrides)
    return base


class TCP13103(unittest.TestCase):
    def assert_contract(self, result, evidence="p131-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P131-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_interrupted_partial_draft_stays_unapplied(self):
        for draft in ("1.", ""):
            result = evaluate(payload(proposed=_GATE.held_proposal(draft=draft)))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "recorded", draft)
            self.assertEqual(result["rejectedClaims"], [], draft)
            self.assertEqual(result["preservedResults"][1]["applied"], 180, draft)
            self.assertEqual(result["preservedResults"][1]["draft"], draft)
            self.assertEqual(result["preservedResults"][2]["draftKind"], "incomplete", draft)
            self.assertEqual(result["preservedResults"][2]["previousApplied"], 180, draft)
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "partial-draft-reached-camera")

    def test_partial_draft_reaching_the_camera_is_rejected(self):
        result = evaluate(payload(proposed=_GATE.held_proposal(draft="1.", apply_partial=True, applied=1)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["applied"], 180)
        self.assertEqual(result["preservedResults"][1]["source_configuration"], _GATE.FIXTURE_SOURCE)

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p131-tc03-iso"
        result = evaluate(payload(evidenceId=evidence, repeat="ISO"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["applied"], 180)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(proposed=_GATE.held_proposal(minimum=20, maximum=5)))
