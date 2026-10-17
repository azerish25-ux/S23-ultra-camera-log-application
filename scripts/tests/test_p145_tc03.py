"""Tests for TC-P145-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p145_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p145_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def import_file(**overrides):
    base = {
        "name": "clip.mp4",
        "extension": ".mp4",
        "declaredLength": 1200,
        "actualLength": 1200,
        "width": 1920,
        "height": 1080,
        "transform": [1, 0, 0, 1],
        "path": "imports/clip.mp4",
        "headerValidated": True,
        "trustExtensionOnly": False,
        "accepted": True,
        "escapedStorage": False,
        "retainedSha256": _GATE.RETAINED_MEDIA_SHA256,
        "retainedSha256After": _GATE.RETAINED_MEDIA_SHA256,
    }
    base.update(overrides)
    return base


def payload(**overrides):
    layers = overrides.pop("layers", None)
    base = {
        "evidenceId": "p145-tc03",
        "repeat": "parser-truncation",
        "pressure": "parser-truncation",
        "attempts": 1,
        "importFile": import_file(),
    }
    base.update(_GATE.layer_fields(layers))
    base.update(overrides)
    return base


class TCP14503(unittest.TestCase):
    def assert_contract(self, result, evidence="p145-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P145-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_case_text_matches_the_spec(self):
        self.assertEqual(_MODULE.CASE["name"], "Hostile imported file")
        self.assertEqual(_MODULE.CASE["negative"], "Trusting extensions or unvalidated headers must fail.")

    def test_valid_import_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][2]["hostile"])
        self.assertEqual(result["preservedResults"][2]["retainedSha256"], _GATE.RETAINED_MEDIA_SHA256)

    def test_rejected_hostile_file_keeps_retained_media(self):
        hostile = import_file(
            declaredLength=100,
            actualLength=5000,
            width=90000,
            transform=[float("nan")],
            path="../etc/passwd",
            headerValidated=False,
            trustExtensionOnly=True,
            accepted=False,
        )
        result = evaluate(payload(
            importFile=hostile,
            pressure="decompression-pressure",
            repeat="decompression-pressure",
            attempts=3,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][2]["hostile"])
        self.assertTrue(result["preservedResults"][2]["pathEscapes"])
        self.assertTrue(result["preservedResults"][2]["nonfinite"])
        self.assertEqual(result["preservedResults"][2]["attempts"], 3)

    def test_trusting_an_unvalidated_header_is_rejected(self):
        result = evaluate(payload(importFile=import_file(headerValidated=False, trustExtensionOnly=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["retainedSha256"], _GATE.RETAINED_MEDIA_SHA256)

    def test_accepted_traversal_that_escapes_storage_is_rejected(self):
        result = evaluate(payload(importFile=import_file(
            path="../../private/take",
            accepted=True,
            escapedStorage=True,
            retainedSha256After="ab" * 32,
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HOSTILE_ACCEPTED, result["rejectedClaims"])
        self.assertIn(_MODULE.STORAGE_ESCAPE, result["rejectedClaims"])
        self.assertIn(_MODULE.MEDIA_CORRUPTED, result["rejectedClaims"])

    def test_decompression_over_the_limit_is_rejected_when_accepted(self):
        declared = 10
        actual = declared * _GATE.IMPORT_MAX_EXPANSION + 1
        result = evaluate(payload(
            pressure="decompression-pressure",
            importFile=import_file(declaredLength=declared, actualLength=actual, accepted=True),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RESOURCE_EXCEEDED, result["rejectedClaims"])
        self.assertIn(_MODULE.HOSTILE_ACCEPTED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p145-tc03-repeat"
        result = evaluate(payload(evidenceId=evidence, repeat="repeated-invalid-imports", pressure="repeated-invalid-imports"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(attempts=0))
        with self.assertRaises(ValueError):
            evaluate(payload(importFile=import_file(transform=["wide"])))
