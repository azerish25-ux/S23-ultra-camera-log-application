"""Tests for TC-P147-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p147_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p147_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="startup")
    base.update({"offlineDefault": True, "transmissions": []})
    base.update(overrides)
    return base


def replace_import(import_id, **overrides):
    rows = _GATE.fixture_imports()
    for row in rows:
        if row["id"] == import_id:
            row.update(overrides)
    return rows


class TCP14704(unittest.TestCase):
    def assert_contract(self, result, evidence="p147-secure-import"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P147-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_offline_silence_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["bytes"], 0)
        self.assertEqual(_MODULE.CASE["name"], "Unexpected network transmission")

    def test_analytics_thumbnail_is_rejected(self):
        result = evaluate(payload(transmissions=[{
            "kind": "thumbnail",
            "bytes": 128,
            "endpoint": "https://analytics.example/upload",
        }]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_private_frames_under_offline_default_are_rejected(self):
        result = evaluate(payload(transmissions=[{
            "kind": "frames",
            "bytes": 64,
            "endpoint": "https://upload.example/frames",
        }]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OFFLINE_TRANSMISSION, result["rejectedClaims"])

    def test_disabling_offline_default_is_rejected(self):
        result = evaluate(payload(offlineDefault=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OFFLINE_DISABLED, result["rejectedClaims"])

    def test_traversal_import_is_rejected_inside_the_case(self):
        result = evaluate(payload(imports=replace_import("archive-zip", paths=["../escape"])))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.PATH_TRAVERSAL, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p147-tc04-export"
        result = evaluate(payload(evidenceId=evidence, repeat="export"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(transmissions=[{"kind": "thumbnail", "bytes": -1, "endpoint": "local"}]))
