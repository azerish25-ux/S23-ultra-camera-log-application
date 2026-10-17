"""Tests for TC-P136-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p136_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p136-tc06",
        "repeat": "decode",
        "report": _GATE.honest_report(),
        "framesSubmitted": True,
        "shownStage": "verification",
        "verificationComplete": False,
        "publicationComplete": False,
        "bannerPercent": 40,
        "acceptedComplete": False,
    }
    base.update(overrides)
    return base


class TCP13606(unittest.TestCase):
    def assert_contract(self, result, evidence="p136-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P136-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.CASE["name"], "Premature success indication")
        self.assertEqual(
            _MODULE.CASE["intervention"],
            "Finish frame submission while verification or publication still remains incomplete.",
        )
        self.assertEqual(
            _MODULE.CASE["expected"],
            "Show the actual remaining stage and withhold accepted completion until its gate passes.",
        )
        self.assertEqual(
            _MODULE.CASE["negative"],
            "A one-hundred-percent banner before required verification must fail.",
        )
        self.assertEqual(
            _MODULE.CASE["repeat"],
            "Repeat encoder drain, full decode, sidecar export, and gallery commit.",
        )

    def test_remaining_verification_is_recorded_as_not_run(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["remainingStage"], "verification")
        self.assertEqual(result["preservedResults"][1]["status"], "not-run")
        self.assertIsNone(result["preservedResults"][1]["shootingWorkflow"])

    def test_hundred_percent_before_verification_is_rejected(self):
        result = evaluate(payload(bannerPercent=100, shownStage="complete", acceptedComplete=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.ACCEPTED_EARLY, result["rejectedClaims"])
        self.assertIn(_MODULE.STAGE_HIDDEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_publication_banner_and_hidden_stage_are_rejected(self):
        result = evaluate(
            payload(
                verificationComplete=True,
                publicationComplete=False,
                shownStage="complete",
                bannerPercent=100,
                acceptedComplete=True,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.BEFORE_PUBLICATION, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][2]["remainingStage"], "publication")

    def test_screenshot_approval_is_rejected(self):
        result = evaluate(payload(report=_GATE.honest_report(approved=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.DESKTOP_SCREENSHOT_APPROVAL, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p136-tc06-gallery"
        result = evaluate(payload(evidenceId=evidence, repeat="gallery", bannerPercent=None))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertIsNone(result["preservedResults"][2]["bannerPercent"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(shownStage="done"))
        with self.assertRaises(ValueError):
            evaluate(payload(bannerPercent=101))
