"""Tests for TC-P151-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p151_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p151_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def imported(**overrides):
    value = {
        "length": 128,
        "width": 1920,
        "height": 1080,
        "transform": [1, 0, 0, 0, 1, 0, 0, 0, 1],
        "path": "clips/take.raw",
        "extension": "raw",
        "headerValidated": True,
        "trustedExtension": False,
        "accepted": True,
        "escapedStorage": False,
        "corruptedRetainedMedia": False,
        "bytesAllocated": 4096,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="parser truncation")
    base.update({"imported": imported()})
    base.update(overrides)
    return base


class TCP15103(unittest.TestCase):
    def assert_contract(self, result, evidence="p151-release-notes"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P151-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_bounded_valid_import_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["path"], "clips/take.raw")
        self.assertEqual(_MODULE.CASE["name"], "Hostile imported file")

    def test_rejected_hostile_path_is_recorded(self):
        result = evaluate(payload(imported=imported(path="../escape", accepted=False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_trusted_extension_is_rejected(self):
        result = evaluate(payload(imported=imported(trustedExtension=True, headerValidated=False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_accepted_traversal_is_rejected(self):
        result = evaluate(payload(imported=imported(path="../escape", accepted=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HOSTILE_ACCEPTED, result["rejectedClaims"])

    def test_storage_escape_is_rejected(self):
        result = evaluate(payload(imported=imported(escapedStorage=True, corruptedRetainedMedia=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STORAGE_DAMAGE, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p151-tc03-pressure"
        result = evaluate(payload(evidenceId=evidence, repeat="decompression pressure"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(imported=imported(length="big")))
