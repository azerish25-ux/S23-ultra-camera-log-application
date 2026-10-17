"""Tests for TC-P147-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p147_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p147_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def subject(**overrides):
    value = _GATE.make_import("subject-lut", "lut", "cube", "cube")
    value["accepted"] = True
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="parser truncation")
    base.update({"subject": subject()})
    base.update(overrides)
    return base


class TCP14703(unittest.TestCase):
    def assert_contract(self, result, evidence="p147-secure-import"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P147-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_validated_import_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["decision"], "recorded")
        self.assertEqual(_MODULE.CASE["name"], "Hostile imported file")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "trusted-extension-or-unvalidated-header")

    def test_trusting_an_extension_or_header_is_rejected(self):
        trusted = evaluate(payload(subject=subject(
            magic="PK",
            trust_extension=True,
            header_validated=False,
            accepted=True,
            allocated=0,
        )))
        self.assert_contract(trusted)
        self.assertEqual(trusted["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, trusted["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], trusted["reasons"])
        self.assertIn(_GATE.TRUSTED_EXTENSION, trusted["preservedResults"][3]["faults"])
        self.assertIn(_GATE.UNVALIDATED_HEADER, trusted["preservedResults"][3]["faults"])

    def test_accepted_traversal_or_size_mismatch_is_rejected(self):
        traversal = evaluate(payload(subject=subject(paths=["../escape"], accepted=True)))
        self.assertEqual(traversal["decision"], "rejected")
        self.assertIn(_MODULE.HOSTILE_ACCEPTED, traversal["rejectedClaims"])
        mismatch = evaluate(payload(subject=subject(actual_size=1025, accepted=True)))
        self.assertEqual(mismatch["decision"], "rejected")
        self.assertIn(_MODULE.HOSTILE_ACCEPTED, mismatch["rejectedClaims"])
        self.assertIn(_GATE.SIZE_MISMATCH, mismatch["preservedResults"][3]["faults"])
        refused = evaluate(payload(subject=subject(paths=["../escape"], accepted=False, allocated=0)))
        self.assertEqual(refused["decision"], "recorded")
        self.assertEqual(refused["preservedResults"][3]["decision"], "rejected")

    def test_storage_escape_is_rejected(self):
        result = evaluate(payload(subject=subject(
            escaped=True,
            source_corrupted=True,
            accepted=False,
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STORAGE_DAMAGE, result["rejectedClaims"])

    def test_nonfinite_subject_is_rejected_when_accepted(self):
        values = _GATE.identity_matrix()
        values[4] = float("nan")
        result = evaluate(payload(subject=subject(kind="profile", extension="json", magic="json", values=values)))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HOSTILE_ACCEPTED, result["rejectedClaims"])
        self.assertIn(_GATE.NONFINITE, result["preservedResults"][3]["faults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p147-tc03-decompress"
        result = evaluate(payload(evidenceId=evidence, repeat="decompression pressure"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(subject=subject(declared_size="huge")))
        with self.assertRaises(ValueError):
            evaluate(payload(subject=subject(applyNegative=True)))
