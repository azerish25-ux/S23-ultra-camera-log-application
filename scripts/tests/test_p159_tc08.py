"""Tests for TC-P159-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p159_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p159_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def records():
    return [
        {"id": "capture", "outcome": "favorable", "setupIncluded": True},
        {"id": "optics", "outcome": "failed", "setupIncluded": True},
    ]


def payload(**overrides):
    base = _GATE.core_payload(repeat="capture")
    base.update({
        "records": records(),
        "promotionalReelOnly": False,
    })
    base.update(overrides)
    return base


class TCP15908(unittest.TestCase):
    def assert_contract(self, result, evidence="p159-computational-optics"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P159-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_failed_experiments_with_setup_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["outcomes"], ["favorable", "failed"])
        self.assertEqual(_MODULE.CASE["name"], "Unreproducible research closure")

    def test_promotional_reel_is_rejected(self):
        result = evaluate(payload(promotionalReelOnly=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], [_MODULE.NEGATIVE_TOKEN])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_favorable_only_archive_is_rejected(self):
        rows = [
            {"id": "capture", "outcome": "favorable", "setupIncluded": True},
            {"id": "film-rendering", "outcome": "favorable", "setupIncluded": True},
        ]
        result = evaluate(payload(records=rows))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FAILED_OMITTED, result["rejectedClaims"])
        self.assertIn(_MODULE.FAVORABLE_ONLY, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["expected"], result["reasons"])

    def test_missing_setup_is_rejected(self):
        rows = records()
        rows[1] = {"id": "optics", "outcome": "failed", "setupIncluded": False}
        result = evaluate(payload(records=rows))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SETUP_OMITTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p159-tc08-rejected-hypotheses"
        result = evaluate(payload(evidenceId=evidence, repeat="rejected hypotheses"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(records=[]))
        with self.assertRaises(ValueError):
            rows = records()
            rows[0] = {"id": "capture", "outcome": "pretty", "setupIncluded": True}
            evaluate(payload(records=rows))
