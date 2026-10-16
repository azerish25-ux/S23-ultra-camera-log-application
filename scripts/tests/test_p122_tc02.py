"""Tests for TC-P122-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p122_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p122_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p122-tc02",
        "repeat": "Repeat stock, focus, grain seed, output range, and source interpretation changes.",
        "versions": _MODULE.valid_versions(),
        "runningExportRecipeId": "rv-1",
        "liveParameters": {"grain": 0.33, "focus": 0.72},
        "readLiveSliders": False,
        "mutatedInPlace": False,
    }
    base.update(overrides)
    return base


class TCP12202(unittest.TestCase):
    def assert_contract(self, result, evidence="p122-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P122-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("preimage=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_frozen_export_and_new_version_are_recorded(self):
        versions = payload()["versions"]
        before = versions[0]["version_sha256"]
        result = evaluate(payload(versions=versions))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(versions[0]["version_sha256"], before)
        self.assertIn("new edit identity rv-2", result["reasons"])
        self.assertIn("runningExportRecipeId=rv-1", result["preservedResults"])

    def test_live_sliders_are_rejected_and_evidence_remains(self):
        result = evaluate(payload(readLiveSliders=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_in_place_mutation_is_rejected(self):
        result = evaluate(payload(mutatedInPlace=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("in-place-recipe-mutation", result["rejectedClaims"])

    def test_export_following_the_edit_is_rejected(self):
        result = evaluate(payload(runningExportRecipeId="rv-2"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("export-followed-live-edit", result["rejectedClaims"])

    def test_changed_source_is_rejected(self):
        versions = _MODULE.valid_versions()
        other = "c" * 64
        versions[1]["source_sha256"] = other
        versions[1]["version_sha256"] = __import__("hashlib").sha256(
            (
                '{"params":{"focus":0.72,"grain":0.33},"parent":"rv-1","source":"' + other + '"}'
            ).encode("utf-8")
        ).hexdigest()
        result = evaluate(payload(versions=versions))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("source-sha256-changed", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p122-tc02-grain"
        result = evaluate(payload(evidenceId=evidence, repeat="grain seed"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
