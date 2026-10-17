"""Tests for TC-P149-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p149_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p149_tc03.py",
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


class TCP14903(unittest.TestCase):
    def assert_contract(self, result, evidence="p149-thermal-endurance"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P149-03")
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

    def test_accepted_traversal_or_nonfinite_transform_is_rejected(self):
        traversal = evaluate(payload(imported=imported(path="../escape", accepted=True)))
        self.assertEqual(traversal["decision"], "rejected")
        self.assertIn(_MODULE.HOSTILE_ACCEPTED, traversal["rejectedClaims"])
        nonfinite = evaluate(payload(imported=imported(transform=[1, 0, 0, 0, float("nan"), 0, 0, 0, 1], accepted=True)))
        self.assertEqual(nonfinite["decision"], "rejected")
        self.assertIn(_MODULE.HOSTILE_ACCEPTED, nonfinite["rejectedClaims"])
        refused = evaluate(payload(imported=imported(path="../escape", accepted=False, length=-1)))
        self.assertEqual(refused["decision"], "recorded")

    def test_storage_escape_is_rejected(self):
        result = evaluate(payload(imported=imported(escapedStorage=True, corruptedRetainedMedia=True, accepted=False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STORAGE_DAMAGE, result["rejectedClaims"])

    def test_short_frame_rate_guarantee_rejects_the_case(self):
        result = evaluate(payload(sampleDurationSeconds=2, frameRateGuaranteeClaimed=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.FRAME_RATE_FROM_SHORT_SAMPLE, result["rejectedClaims"])
        self.assertIn(_GATE.FRAME_RATE_WITHOUT_MEASURED_ENVELOPE, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p149-tc03-decompress"
        result = evaluate(payload(evidenceId=evidence, repeat="decompression pressure"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(imported=imported(length="huge")))
