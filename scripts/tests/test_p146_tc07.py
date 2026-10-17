"""Tests for TC-P146-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p146_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p146_tc07.py",
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


class TCP14607(unittest.TestCase):
    def assert_contract(self, result, evidence="p146-property-mutation"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P146-07")
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
        self.assertEqual(_MODULE.CASE["name"], "Release claim exceeds evidence")

    def test_copying_the_roadmap_into_implemented_is_rejected(self):
        result = evaluate(payload(implementedList=["source-mode", "live-depth"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_camera_equivalence_without_physical_qualification_is_rejected(self):
        rows = features()
        rows[0] = {"id": "source-mode", "state": "implemented", "scope": "camera-equivalence"}
        result = evaluate(payload(features=rows))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNSUPPORTED_SCOPE, result["rejectedClaims"])

    def test_physically_qualified_native_resolution_is_recorded(self):
        rows = features() + [{
            "id": "native-4k",
            "state": "physically-qualified",
            "scope": "native-resolution",
        }]
        result = evaluate(payload(features=rows, implementedList=["source-mode", "native-4k"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p146-tc07-calibration"
        result = evaluate(payload(evidenceId=evidence, repeat="calibration status"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(implementedList=["not-a-feature"]))
        with self.assertRaises(ValueError):
            rows = features()
            rows[1] = {"id": "live-depth", "state": "qualified", "scope": "experimental"}
            evaluate(payload(features=rows))
