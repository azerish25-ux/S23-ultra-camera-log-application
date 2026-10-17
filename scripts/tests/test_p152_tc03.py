"""Tests for TC-P152-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p152_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p152_tc03.py",
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


class TCP15203(unittest.TestCase):
    def assert_contract(self, result, evidence="p152-production-readiness"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P152-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_validated_import_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(_MODULE.CASE["name"], "Hostile imported file")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "trusted-extension-or-unvalidated-header")

    def test_trusting_an_extension_or_header_is_rejected(self):
        result = evaluate(payload(imported=imported(trustedExtension=True, headerValidated=False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_traversal_and_nonfinite_transform_are_rejected(self):
        traversal = evaluate(payload(imported=imported(path="../escape/clip.json", accepted=True)))
        self.assertEqual(traversal["decision"], "rejected")
        self.assertIn(_MODULE.HOSTILE_ACCEPTED, traversal["rejectedClaims"])
        transform = evaluate(payload(imported=imported(transform=[1, 0, 0, 0, float("nan"), 0, 0, 0, 1], accepted=True)))
        self.assertEqual(transform["decision"], "rejected")
        self.assertIn(_MODULE.HOSTILE_ACCEPTED, transform["rejectedClaims"])

    def test_storage_escape_is_rejected(self):
        result = evaluate(payload(imported=imported(escapedStorage=True, corruptedRetainedMedia=True, accepted=False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STORAGE_DAMAGE, result["rejectedClaims"])

    def test_rejected_hostile_import_can_still_be_recorded(self):
        result = evaluate(payload(imported=imported(
            path="../escape/clip.json",
            accepted=False,
            headerValidated=True,
            trustedExtension=False,
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p152-tc03-decompression"
        result = evaluate(payload(evidenceId=evidence, repeat="decompression pressure"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(imported=imported(length=True)))
