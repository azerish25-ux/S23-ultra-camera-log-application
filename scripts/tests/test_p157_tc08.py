"""Tests for TC-P157-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p157_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p157_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def records():
    return [
        {"id": "capture-pass", "favorable": True, "setup": "capture-setup", "domain": "capture"},
        {"id": "film-pass", "favorable": True, "setup": "film-setup", "domain": "film-rendering"},
        {"id": "optics-pass", "favorable": True, "setup": "optics-setup", "domain": "optics"},
        {"id": "rejected-run", "favorable": False, "setup": "rejected-setup", "domain": "rejected-hypotheses"},
    ]


def payload(**overrides):
    base = _GATE.core_payload()
    base.update({
        "repeat": "fresh-maintainer reproduction",
        "records": records(),
        "promotionalReelOnly": False,
        "reproductionDomains": ["capture", "film-rendering", "optics", "rejected-hypotheses"],
    })
    base.update(overrides)
    if "experiments" in overrides and "checksum" not in overrides:
        base["checksum"] = _GATE.protocol_checksum(base["experiments"])
    return base


class TCP15708(unittest.TestCase):
    def assert_contract(self, result, evidence="p157-instrumented-experiment-design"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P157-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_archive_with_failures_and_setup_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["failedRecordIds"], ["rejected-run"])
        self.assertEqual(_MODULE.CASE["name"], "Unreproducible research closure")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "promotional-reel-substitutes-for-archive")

    def test_promotional_reel_is_rejected(self):
        result = evaluate(payload(promotionalReelOnly=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_omitting_failed_experiments_is_rejected(self):
        kept = [row for row in records() if row["favorable"]]
        result = evaluate(payload(records=kept))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FAILED_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.REPRODUCTION_TOKEN, result["rejectedClaims"])

    def test_blank_setup_is_rejected(self):
        rows = records()
        rows[0]["setup"] = ""
        result = evaluate(payload(records=rows))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SETUP_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p157-tc08-optics"
        result = evaluate(payload(evidenceId=evidence, repeat="optics"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(records=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(reproductionDomains=["capture", "capture", "optics", "rejected-hypotheses"]))
