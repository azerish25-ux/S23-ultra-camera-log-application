"""Tests for TC-P126-05."""

from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p126_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p126_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
RULE = "present-and-verified-and-matching-hash-and-positive-byte-count"
REQUIRED = _MODULE.required_bytes(1000, 200, 400, 50, 900)


def _library(clips=None, omitted=None):
    content = "paired-result"
    encoded = content.encode("utf-8")
    default = [{
        "clip_id": "clip-result",
        "content_sha256": hashlib.sha256(encoded).hexdigest(),
        "byte_count": len(encoded),
        "present": True,
        "playable": True,
        "verification": "verified",
        "content": content,
        "role": "result",
        "bundle_id": "take-1",
    }]
    return {"clips": default if clips is None else clips, "omitted_ids": [] if omitted is None else omitted}


def _absent_playable():
    encoded = b"gone"
    return {
        "clip_id": "clip-gone",
        "content_sha256": hashlib.sha256(encoded).hexdigest(),
        "byte_count": len(encoded),
        "present": False,
        "playable": True,
        "verification": "missing",
    }


def payload(**overrides):
    base = {
        "evidenceId": "p126-evidence",
        "repeat": "Repeat",
        "sourceBytes": 1000,
        "proxyBytes": 200,
        "temporaryBytes": 400,
        "finalizationBytes": 50,
        "publicationBytes": 900,
        "finalOutputBytes": 800,
        "remainingBytes": 100000,
        "reserveBytes": 100,
        "budgetBytes": REQUIRED,
        "sourceRetained": True,
    }
    base.update(_library())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12605(unittest.TestCase):
    def assert_contract(self, result, evidence="p126-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P126-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("playableRule=" + RULE, blob(result))
        self.assertTrue(result["reasons"])

    def test_full_budget_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(f"requiredBytes={REQUIRED}", result["preservedResults"])
        self.assertIn("source-retained", result["reasons"])
        self.assertNotEqual(REQUIRED, 800)

    def test_final_output_only_budget_is_rejected(self):
        result = evaluate(payload(budgetBytes=800))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("p126-evidence", result["preservedResults"])

    def test_shortage_pauses_before_source_loss(self):
        result = evaluate(payload(remainingBytes=10))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("paused-before-source-loss", result["reasons"])
        self.assertNotIn(_MODULE.LOST_TOKEN, result["rejectedClaims"])

    def test_shortage_that_drops_the_source_is_rejected(self):
        result = evaluate(payload(remainingBytes=10, sourceRetained=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOST_TOKEN, result["rejectedClaims"])

    def test_playable_without_bytes_is_rejected(self):
        result = evaluate(payload(**_library(clips=[_absent_playable()])))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("playable-absent-bytes", result["rejectedClaims"])
        self.assertIn("missing:clip-gone", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p126-assembly"
        result = evaluate(payload(evidenceId=evidence, repeat="assembly"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(temporaryBytes=-1))
