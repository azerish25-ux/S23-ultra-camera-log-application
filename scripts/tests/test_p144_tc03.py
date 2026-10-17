"""Tests for TC-P144-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p144_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p144_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
FACTS = {"camera": "body-a", "lens": None, "stock": "unknown"}


def payload(**overrides):
    base = {
        "evidenceId": "p144-tc03",
        "repeat": "recipe save",
        "edit": "grain",
        "parent_version_id": "rv-1",
        "new_version_id": "rv-2",
        "historical_facts": dict(FACTS),
        "derivative_facts": dict(FACTS),
        "preference_replaced_sourced_metadata": False,
        "recipe": _GATE.preferred_recipe(),
    }
    base.update(overrides)
    return base


class TCP14403(unittest.TestCase):
    def assert_contract(self, result, evidence="p144-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P144-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_new_version_keeps_historical_facts(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertEqual(record["new_version_id"], "rv-2")
        self.assertTrue(record["historical_facts_unchanged"])
        self.assertFalse(record["report"]["identification"]["correct"])
        self.assertIn("\u2019", _MODULE.CASE["negative"])

    def test_preference_replacing_metadata_is_rejected(self):
        recipe = _GATE.preferred_recipe()
        recipe["identification"]["status"] = "correct"
        recipe["identification"]["evidence_kind"] = "preference"
        result = evaluate(payload(preference_replaced_sourced_metadata=True, recipe=recipe))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PREFERENCE_REPLACED, result["rejectedClaims"])
        self.assertIn(_GATE.HIGH_ENJOYMENT_DOES_NOT_CERTIFY, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertFalse(result["preservedResults"][1]["report"]["identification"]["correct"])

    def test_changed_historical_facts_are_rejected(self):
        changed = dict(FACTS)
        changed["lens"] = "guessed-50mm"
        result = evaluate(payload(edit="aperture", derivative_facts=changed))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FACTS_CHANGED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p144-tc03-rename"
        result = evaluate(payload(evidenceId=evidence, repeat="rename", edit="grade"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(edit="crop"))
