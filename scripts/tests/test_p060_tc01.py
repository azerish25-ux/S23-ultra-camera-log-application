"""TC-P060-01 wrong LogC domain coefficients."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p060_tc01", Path(__file__).resolve().parents[1] / "gates" / "p060_tc01.py"
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
        "label": "LogC3",
        "inputDomain": "exposure",
        "coefficientSet": "sensor-ei800",
        "locus": "grey",
        "sceneValue": "0.18",
    }
    base.update(overrides)
    return base


class TcP06001(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P060-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertTrue(result["reasons"])

    def test_packet_strings(self):
        self.assertIn("LogC3", _MODULE.INTERVENTION)
        self.assertIn("sensor-signal", _MODULE.NEGATIVE)
        self.assertIn("branch cut", _MODULE.REPEAT)

    def test_sensor_coefficients_on_exposure_grey_fail(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("sensor-signal-coefficients-on-exposure-domain", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("failed:black,grey,branch,highlight,inverse", result["preservedResults"])
        self.assertIn("scene:0.18", result["preservedResults"])
        self.assertIn("exposure-grey:0.391007", result["preservedResults"])
        self.assertIn("label:LogC3", result["preservedResults"])

    def test_exposure_coefficients_withhold_the_export(self):
        result = evaluate(payload(coefficientSet="exposure-ei800", locus="black", sceneValue="0"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("failed:none", result["preservedResults"])
        self.assertIn("exposure-black:0.092809", result["preservedResults"])
        self.assertIn("applied-black:0.092809", result["preservedResults"])
        self.assertTrue(any("withheld" in item or "not produced" in item or "still withheld" in item
                            for item in result["reasons"]))

    def test_repeat_near_branch_below(self):
        result = evaluate(payload(locus="branch-below", sceneValue="0.010590"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("scene:0.010590", result["preservedResults"])
        self.assertIn("exposure-branch-below:0.149652", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_near_branch_above(self):
        result = evaluate(payload(locus="branch-above", sceneValue="0.010592"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("scene:0.010592", result["preservedResults"])
        self.assertIn("failed:black,grey,branch,highlight,inverse", result["preservedResults"])

    def test_repeat_highlight_above_scene_linear_one(self):
        result = evaluate(payload(locus="highlight", sceneValue="4"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("exposure-highlight:0.718702", result["preservedResults"])
        self.assertIn("applied-highlight:1.103054", result["preservedResults"])
        self.assertIn("scene:4", result["preservedResults"])

    def test_inverse_locus_keeps_both_codes(self):
        result = evaluate(payload(locus="inverse", sceneValue="0.18"))
        self.assertIn("inverse-decoded:0.008907", result["preservedResults"])
        self.assertEqual(result["decision"], "rejected")

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "locus"},
            {**valid, "label": "LogC4"},
            {**valid, "sceneValue": "0.180"},
            {**valid, "inputDomain": "linear"},
            {**valid, "coefficientSet": "ei160"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
