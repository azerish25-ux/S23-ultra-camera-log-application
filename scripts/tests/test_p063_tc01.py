"""TC-P063-01 wrong LogC domain coefficients."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p063_tc01", Path(__file__).resolve().parents[1] / "gates" / "p063_tc01.py"
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
        "sampleId": "grey-card",
        "label": "LogC3",
        "coefficientSet": "sensor-signal",
        "valueDomain": "exposure",
        "locus": "grey",
        "sceneLinear": "0.18",
        "exportAccepted": True,
    }
    base.update(overrides)
    return base


class TcP06301(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P063-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Use a coefficient set belonging to a different input convention while retaining the LogC3 label.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Fail independent black, grey, branch, and inverse tests before producing an accepted export.",
        )
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Using sensor-signal coefficients on exposure-domain values must fail.",
        )

    def test_sensor_signal_on_exposure_fails(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("sensor-signal-on-exposure", result["rejectedClaims"])
        self.assertIn("failed-black", result["rejectedClaims"])
        self.assertIn("failed-grey", result["rejectedClaims"])
        self.assertIn("failed-branch", result["rejectedClaims"])
        self.assertIn("failed-inverse", result["rejectedClaims"])
        self.assertIn("accepted-export-blocked", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("scene-linear:0.18", result["preservedResults"])
        self.assertIn("label:LogC3", result["preservedResults"])
        self.assertIn("grey-card", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_near_branch_cut(self):
        result = evaluate(payload(sampleId="cut", locus="branch-cut", sceneLinear="0.01"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("locus:branch-cut", result["preservedResults"])
        self.assertIn("scene-linear:0.01", result["preservedResults"])
        self.assertIn("sensor-signal-on-exposure", result["rejectedClaims"])

    def test_repeat_highlight_above_scene_linear_one(self):
        result = evaluate(
            payload(sampleId="hot", locus="highlight", sceneLinear="4", exportAccepted=False)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("scene-linear:4", result["preservedResults"])
        self.assertIn("locus:highlight", result["preservedResults"])
        self.assertNotIn("accepted-export-blocked", result["rejectedClaims"])
        self.assertIn("coefficients:sensor-signal", result["preservedResults"])

    def test_matching_coefficients_are_withheld(self):
        result = evaluate(
            payload(coefficientSet="logc3-exposure", exportAccepted=False, locus="black", sceneLinear="0")
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("domain:exposure", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "label"},
            {**valid, "extra": True},
            {**valid, "label": "LogC4"},
            {**valid, "coefficientSet": "awg4"},
            {**valid, "sceneLinear": "4.0"},
            {**valid, "locus": "highlight", "sceneLinear": "1"},
            {**valid, "locus": "branch-cut", "sceneLinear": "1"},
            {**valid, "exportAccepted": "true"},
            {**valid, "sceneLinear": "-1"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
