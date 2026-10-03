"""TC-P073-02 exposure-domain confusion."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p073_tc02", Path(__file__).resolve().parents[1] / "gates" / "p073_tc02.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def payload(**overrides):
    base = {
        "control": "exposure",
        "stageDeclared": "incident-exposure",
        "stageApplied": "post-negative",
        "presentsAsIncident": True,
        "postLutContrastOnly": False,
    }
    base.update(overrides)
    return base


class TcP07302(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P073-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        for axis in ("shadow", "highlight", "texture"):
            self.assertIn(axis, result["preservedResults"])

    def test_packet_strings(self):
        self.assertIn("incident exposure", _MODULE.INTERVENTION)
        self.assertIn("post-LUT", _MODULE.NEGATIVE)
        self.assertIn("printing", _MODULE.REPEAT)
        self.assertIn("display grading", _MODULE.REPEAT)

    def test_exposure_after_negative_fails_the_graph_contract(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["graph-contract"])
        self.assertIn("control:exposure", result["preservedResults"])
        self.assertIn("declared:incident-exposure", result["preservedResults"])
        self.assertIn("applied:post-negative", result["preservedResults"])
        self.assertTrue(any("shadow, highlight, and texture behavior differ" in item for item in result["reasons"]))

    def test_printing_control_repeat_keeps_the_axes(self):
        result = evaluate(payload(control="printing", stageDeclared="printing", stageApplied="display-grade"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("control:printing", result["preservedResults"])
        self.assertIn("graph-contract", result["rejectedClaims"])

    def test_post_lut_contrast_cannot_stand_in_for_every_stage(self):
        result = evaluate(
            payload(
                control="development",
                stageDeclared="development",
                stageApplied="development",
                presentsAsIncident=False,
                postLutContrastOnly=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["post-lut-contrast"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("control:development", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "stage_aligned"})

    def test_display_grade_repeat_with_false_incident_and_post_lut(self):
        result = evaluate(
            payload(
                control="display-grade",
                stageDeclared="incident-exposure",
                stageApplied="display-grade",
                presentsAsIncident=True,
                postLutContrastOnly=True,
            )
        )
        self.assertEqual(result["rejectedClaims"], ["graph-contract", "post-lut-contrast"])
        self.assertIn("control:display-grade", result["preservedResults"])
        self.assertIn("shadow", result["preservedResults"])

    def test_aligned_stage_is_not_qualified(self):
        result = evaluate(
            payload(
                control="exposure",
                stageDeclared="incident-exposure",
                stageApplied="incident-exposure",
                presentsAsIncident=True,
                postLutContrastOnly=False,
            )
        )
        self.assertEqual(result["decision"], "stage_aligned")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("control:exposure", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "control"},
            {**valid, "extra": True},
            {**valid, "control": "contrast"},
            {**valid, "stageApplied": "lut"},
            {**valid, "presentsAsIncident": "true"},
            {**valid, "postLutContrastOnly": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
