"""Tests for TC-P104-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p104_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p104_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p104-tc03",
        "scene": "hair",
        "loads": True,
        "depthError": 0.02,
        "boundaryError": 0.03,
        "depthTolerance": 0.05,
        "boundaryTolerance": 0.05,
        "status": "within-tolerance",
    }
    base.update(overrides)
    return base


class TCP10403(unittest.TestCase):
    def assert_contract(self, result, evidence="p104-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P104-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")

    def test_good_within_tolerance_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("within-tolerance:true", result["preservedResults"])
        self.assertTrue(any("not qualified" in item for item in result["reasons"]))

    def test_negative_running_model_outside_tolerance_is_not_qualified(self):
        result = evaluate(payload(scene="glass", depthError=0.4, boundaryError=0.2, status="within-tolerance"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("loads:true", result["preservedResults"])
        self.assertIn("within-tolerance:false", result["preservedResults"])
        experimental = evaluate(payload(scene="low-light", depthError=0.4, status="experimental"))
        self.assertEqual(experimental["decision"], "recorded")
        self.assertIn("status:experimental", experimental["preservedResults"])

    def test_evidence_change(self):
        evidence = "p104-tc03-thin"
        result = evaluate(payload(evidenceId=evidence, scene="thin-objects"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        saturated = evaluate(payload(scene="saturated"))
        self.assertEqual(saturated["decision"], "recorded")

    def test_invalid_payload_raises(self):
        cases = (
            {},
            {**payload(), "applyNegative": True},
            payload(scene="daylight"),
            payload(status="qualified"),
            payload(depthError=-0.1),
            payload(loads="yes"),
            payload(boundaryError=float("nan")),
        )
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
