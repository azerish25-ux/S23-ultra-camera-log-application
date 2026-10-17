"""Tests for TC-P148-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p148_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p148_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
IDENTITY = [1, 0, 0, 0, 1, 0, 0, 0, 1]


def imported(**overrides):
    value = {
        "length": 1024,
        "width": 1920,
        "height": 1080,
        "transform": list(IDENTITY),
        "path": "imports/clip.json",
        "extension": "json",
        "headerValidated": True,
        "trustedExtension": False,
        "accepted": True,
        "escapedStorage": False,
        "corruptedRetainedMedia": False,
        "bytesAllocated": 1024,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="parser truncation")
    base.update({"imported": imported()})
    base.update(overrides)
    return base


class TCP14803(unittest.TestCase):
    def assert_contract(self, result, evidence="p148-offline-privacy"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P148-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_validated_local_import_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["path"], "imports/clip.json")
        self.assertEqual(_MODULE.CASE["name"], "Hostile imported file")

    def test_trusted_extension_is_rejected(self):
        result = evaluate(payload(imported=imported(trustedExtension=True, headerValidated=False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_traversal_path_that_is_accepted_is_rejected(self):
        result = evaluate(payload(imported=imported(path="../escape", accepted=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HOSTILE_ACCEPTED, result["rejectedClaims"])

    def test_storage_escape_is_rejected(self):
        result = evaluate(payload(imported=imported(escapedStorage=True, accepted=False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STORAGE_DAMAGE, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p148-tc03-pressure"
        result = evaluate(payload(evidenceId=evidence, repeat="decompression pressure"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(imported=imported(length="big")))
