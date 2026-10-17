"""Tests for TC-P147-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p147_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p147_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def features():
    return [
        {"id": "source-mode", "state": "implemented", "scope": "host"},
        {"id": "live-depth", "state": "experimental", "scope": "experimental"},
        {"id": "calibration", "state": "experimental", "scope": "experimental"},
    ]


def payload(**overrides):
    base = _GATE.core_payload(repeat="source modes")
    base.update({"features": features(), "implementedList": ["source-mode"]})
    base.update(overrides)
    return base


def replace_import(import_id, **overrides):
    rows = _GATE.fixture_imports()
    for row in rows:
        if row["id"] == import_id:
            row.update(overrides)
    return rows


class TCP14707(unittest.TestCase):
    def assert_contract(self, result, evidence="p147-secure-import"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P147-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_scoped_notes_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["implementedList"], ["source-mode"])

    def test_copying_the_roadmap_into_implemented_is_rejected(self):
        result = evaluate(payload(implementedList=["source-mode", "live-depth"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_camera_equivalence_without_physical_qualification_is_rejected(self):
        notes = features() + [{"id": "camera", "state": "implemented", "scope": "camera-equivalence"}]
        result = evaluate(payload(features=notes, implementedList=["source-mode", "camera"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNSUPPORTED_SCOPE, result["rejectedClaims"])

    def test_physically_qualified_native_resolution_is_recorded(self):
        notes = features() + [{"id": "native", "state": "physically-qualified", "scope": "native-resolution"}]
        result = evaluate(payload(features=notes, implementedList=["source-mode", "native"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_header_allocation_is_rejected_inside_the_case(self):
        result = evaluate(payload(imports=replace_import("profile-json", header_validated=False, allocated=32)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.UNVALIDATED_HEADER, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p147-tc07-depth"
        result = evaluate(payload(evidenceId=evidence, repeat="live depth"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(features=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(implementedList=["missing-feature"]))
