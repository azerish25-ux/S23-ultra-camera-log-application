"""TC-P059-01 wrong LogC domain coefficients."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p059_tc01", Path(__file__).resolve().parents[1] / "gates" / "p059_tc01.py"
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
        "coefficientSet": "exposure-logc3",
        "valueDomain": "exposure",
        "repeat": "none",
        "sceneLinear": "0.18",
        "blackResidual": "0",
        "greyResidual": "0",
        "branchResidual": "0",
        "inverseResidual": "0",
    }
    base.update(overrides)
    return base


class TcP05901(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P059-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("label:LogC3", result["preservedResults"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("LogC3", _MODULE.INTERVENTION)
        self.assertIn("black, grey, branch, and inverse", _MODULE.EXPECTED)
        self.assertIn("sensor-signal", _MODULE.NEGATIVE)

    def test_matching_exposure_coefficients_stay_withheld(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("coefficients:exposure-logc3", result["preservedResults"])
        self.assertIn("scene-linear:0.18", result["preservedResults"])
        self.assertIn("black:0", result["preservedResults"])
        self.assertTrue(any("accepted export" in item for item in result["reasons"]))

    def test_negative_sensor_signal_on_exposure_fails_all_four_tests(self):
        result = evaluate(payload(coefficientSet="sensor-signal"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})
        self.assertEqual(
            result["rejectedClaims"],
            ["sensor-signal-on-exposure", "wrong-convention", "black", "grey", "branch", "inverse"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("coefficients:sensor-signal", result["preservedResults"])
        self.assertIn("domain:exposure", result["preservedResults"])
        self.assertIn("grey:0", result["preservedResults"])

    def test_repeat_branch_cut_keeps_the_scene_linear_value(self):
        result = evaluate(
            payload(
                coefficientSet="sensor-signal",
                repeat="branch-cut",
                sceneLinear="0.0106",
                branchResidual="0.02",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("repeat:branch-cut", result["preservedResults"])
        self.assertIn("scene-linear:0.0106", result["preservedResults"])
        self.assertIn("branch:0.02", result["preservedResults"])
        self.assertIn("sensor-signal-on-exposure", result["rejectedClaims"])
        self.assertIn("branch", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_highlights_above_scene_linear_one(self):
        result = evaluate(
            payload(
                coefficientSet="foreign-convention",
                repeat="highlights-above-one",
                sceneLinear="1.5",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("repeat:highlights-above-one", result["preservedResults"])
        self.assertIn("scene-linear:1.5", result["preservedResults"])
        self.assertIn("wrong-convention", result["rejectedClaims"])
        self.assertNotIn("sensor-signal-on-exposure", result["rejectedClaims"])
        self.assertIn("inverse", result["rejectedClaims"])
        self.assertIn("label:LogC3", result["preservedResults"])

    def test_nonzero_grey_residual_fails_without_erasing_black(self):
        result = evaluate(payload(greyResidual="0.04"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["grey"])
        self.assertIn("black:0", result["preservedResults"])
        self.assertIn("grey:0.04", result["preservedResults"])

    def test_sensor_signal_domain_with_matching_coefficients_is_withheld(self):
        result = evaluate(payload(coefficientSet="sensor-signal", valueDomain="sensor-signal"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("domain:sensor-signal", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "label"},
            {**valid, "extra": True},
            {**valid, "label": "LogC4"},
            {**valid, "coefficientSet": "logc3"},
            {**valid, "repeat": "daylight"},
            {**valid, "sceneLinear": "0.180"},
            {**valid, "blackResidual": "-1"},
            {**valid, "greyResidual": 0},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
