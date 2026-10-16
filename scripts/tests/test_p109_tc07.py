"""Tests for TC-P109-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p109_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p109_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p109-evidence",
        "repeat": "perfect-depth",
        "uniformBackgroundBlur": False,
        "foregroundCoverage": [1.0, 0.35, 0.0],
        "kernelEnergy": [0.25, 0.5, 0.25],
        "missingBackgroundDeclared": True,
        "inpaint_glass": False,
    }
    base.update(overrides)
    return base


class TCP10907(unittest.TestCase):
    def assert_contract(self, result, evidence="p109-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P109-07")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_layered_normalized_bokeh_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("kernel-energy 1.000000", " ".join(result["reasons"]))

    def test_negative_uniform_blur_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(uniformBackgroundBlur=True, foregroundCoverage=[0.0, 1.0, 1.0]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("uniform-background-blur-without-foreground-coverage", result["rejectedClaims"])

    def test_mutant_inpaint_glass_is_rejected(self):
        result = evaluate(payload(inpaint_glass=True, repeat="estimated-depth"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("inpaint_glass", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p109-estimated-depth"
        result = evaluate(payload(evidenceId=evidence, repeat="estimated-depth"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
