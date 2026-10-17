"""Tests for TC-P142-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p142_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p142_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p142-tc01",
        "repeat": "lens",
        "source": _GATE.fixture_source(),
        "reference": _GATE.fixture_reference(),
        "suggestion": _GATE.fixture_suggestion(),
        "facts": _MODULE.clean_facts(),
    }
    base.update(overrides)
    return base


class TCP14201(unittest.TestCase):
    def assert_contract(self, result, evidence="p142-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P142-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])
        self.assertFalse(result["preservedResults"][1]["newSource"])

    def test_unknown_fact_and_labelled_reconstruction_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        statuses = {item["field"]: item["status"] for item in result["preservedResults"][2:]}
        self.assertEqual(statuses["lens"], "unknown")
        self.assertEqual(statuses["stock"], "guess")
        self.assertEqual(result["preservedResults"][1]["role"], "parameter-suggestion")
        self.assertEqual(_MODULE.CASE["name"], "Missing production fact")

    def test_documented_guess_is_rejected_and_evidence_remains(self):
        facts = _MODULE.clean_facts(lens={
            "status": "guess",
            "documented": True,
            "value": "50mm spherical",
            "label": "creative-reconstruction",
        })
        result = evaluate(payload(facts=facts))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)

    def test_filled_unknown_is_rejected(self):
        facts = _MODULE.clean_facts(release_version={
            "status": "unknown",
            "documented": False,
            "value": "director's cut",
            "label": None,
        })
        result = evaluate(payload(facts=facts, repeat="release-version"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNKNOWN_FILLED, result["rejectedClaims"])

    def test_camera_repeat_preserves_a_different_evidence_id(self):
        evidence = "p142-tc01-camera"
        result = evaluate(payload(evidenceId=evidence, repeat="camera"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_stylized_pixels_are_rejected_even_when_facts_are_clean(self):
        suggestion = _GATE.fixture_suggestion()
        suggestion["method"] = "stylize"
        suggestion["output_sha256"] = _GATE.ALTERED_OUTPUT_SHA256
        suggestion["label"] = "faithful-source"
        result = evaluate(payload(suggestion=suggestion))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.STYLIZE_CHANGED_PIXELS, result["rejectedClaims"])
        self.assertIn(_GATE.LABELLED_SOURCE_FOOTAGE, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(facts=[]))
