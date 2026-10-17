"""Tests for TC-P138-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p138_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p138_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p138-tc07",
        "repeat": "faces",
        "family": _GATE.sample_family(),
        "max_entries": 12,
        "declaredParameters": ["grade", "grain"],
        "contentChanges": [],
        "acceptGeneratedScene": False,
    }
    base.update(overrides)
    return base


class TCP13807(unittest.TestCase):
    def assert_contract(self, result, evidence="p138-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P138-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_declared_rendering_parameters_do_not_change_the_family(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        detail = result["preservedResults"][2]
        self.assertEqual(detail["declaredParameters"], ["grade", "grain"])
        self.assertEqual(detail["contentChanges"], [])
        self.assertIn("5219", detail["stockUnchanged"])
        self.assertIn("Cooke S4 35mm", detail["lensUnchanged"])
        self.assertEqual(_MODULE.CASE["name"], "Parameter matching alters content")

    def test_content_synthesis_and_generated_scene_are_rejected(self):
        result = evaluate(payload(
            repeat="text",
            declaredParameters=["grade"],
            contentChanges=["facial-geometry", "scene-texture"],
            acceptGeneratedScene=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unrequested-content-synthesis", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["entries"][0]["stock"], "5219")

    def test_fine_patterns_repeat_preserves_a_different_evidence_id(self):
        evidence = "p138-tc07-patterns"
        result = evaluate(payload(evidenceId=evidence, repeat="fine patterns", declaredParameters=["halation"]))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_moving_objects_are_rejected(self):
        result = evaluate(payload(repeat="moving objects", contentChanges=["moving-objects"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unrequested-content-synthesis", result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(declaredParameters=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(contentChanges=["grade"]))
