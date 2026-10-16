"""Tests for TC-P129-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p129_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p129_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p129-tc06",
        "repeat": "encoder-drain",
        "bannerPercent": 40,
        "verificationComplete": False,
        "publicationComplete": False,
        "remainingStage": "encoder-drain",
        "capture": ["record", "stop"],
        "monitoring": [],
        "processing": [],
        "warnings": ["storage"],
        "record_in_scroll_only": False,
        "warnings_visible": True,
    }
    base.update(overrides)
    return base


class TCP12906(unittest.TestCase):
    def assert_contract(self, result, evidence="p129-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P129-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Premature success indication")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Finish frame submission while verification or publication still remains incomplete.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Show the actual remaining stage and withhold accepted completion until its gate passes.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "A one-hundred-percent banner before required verification must fail.")
        self.assertEqual(_MODULE.REPEAT, "Repeat encoder drain, full decode, sidecar export, and gallery commit.")

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("remainingStage=encoder-drain", result["preservedResults"])
        self.assertIn("bannerPercent=40", result["preservedResults"])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(bannerPercent=100, remainingStage="gallery-commit"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("p129-tc06", result["preservedResults"])

    def test_accepted_before_publication_is_rejected(self):
        result = evaluate(payload(
            bannerPercent=80,
            verificationComplete=True,
            publicationComplete=False,
            remainingStage="accepted",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PREMATURE_ACCEPTED, result["rejectedClaims"])

    def test_completed_gate_can_be_recorded(self):
        result = evaluate(payload(
            evidenceId="p129-tc06-done",
            bannerPercent=100,
            verificationComplete=True,
            publicationComplete=True,
            remainingStage="accepted",
        ))
        self.assert_contract(result, "p129-tc06-done")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(bannerPercent=101))
