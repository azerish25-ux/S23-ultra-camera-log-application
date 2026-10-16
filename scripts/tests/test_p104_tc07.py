"""Tests for TC-P104-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p104_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p104_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p104-tc07",
        "scene": "transparent",
        "unstable": True,
        "claimedCertainty": True,
        "calibrated": False,
        "presentedAsProbability": False,
        "renderingReliance": "reduced",
    }
    base.update(overrides)
    return base


class TCP10407(unittest.TestCase):
    def assert_contract(self, result, evidence="p104-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P104-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")

    def test_good_uncalibrated_confidence_reduces_reliance(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("calibrated:false", result["preservedResults"])
        self.assertIn("presented-as-probability:false", result["preservedResults"])
        self.assertIn("rendering-reliance:reduced", result["preservedResults"])

    def test_negative_arbitrary_score_is_not_a_probability(self):
        result = evaluate(payload(presentedAsProbability=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("claimed-certainty:true", result["preservedResults"])
        full = evaluate(payload(renderingReliance="full", scene="mirror"))
        self.assertEqual(full["decision"], "rejected")
        self.assertIn("unstable-rendering-not-reduced", full["rejectedClaims"])
        self.assertIn("scene:mirror", full["preservedResults"])

    def test_evidence_change(self):
        evidence = "p104-tc07-wall"
        result = evaluate(payload(evidenceId=evidence, scene="low-texture"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        unfamiliar = evaluate(payload(scene="unfamiliar", unstable=False, claimedCertainty=False, renderingReliance="full"))
        self.assertEqual(unfamiliar["decision"], "recorded")

    def test_invalid_payload_raises(self):
        cases = (
            {},
            {**payload(), "applyNegative": True},
            payload(scene="skin"),
            payload(renderingReliance="none"),
            payload(calibrated=1),
            payload(unstable="yes"),
        )
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
