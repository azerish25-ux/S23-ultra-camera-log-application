"""TC-P061-01 wrong LogC domain coefficients."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p061_tc01", Path(__file__).resolve().parents[1] / "gates" / "p061_tc01.py"
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
        "coefficientSet": "logc3-sensor",
        "valueDomain": "exposure",
        "locus": "grey",
        "sceneLinear": "0.18",
        "acceptedExportRequested": True,
    }
    base.update(overrides)
    return base


class TcP06101(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P061-01")
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
            _MODULE.NEGATIVE,
            "Using sensor-signal coefficients on exposure-domain values must fail.",
        )
        self.assertIn("branch cut", _MODULE.REPEAT)
        self.assertIn("highlights above scene-linear one", _MODULE.REPEAT)

    def test_sensor_coefficients_on_exposure_fail_all_four_checks(self):
        self.assertEqual(
            _MODULE.failed_checks("logc3-sensor", "exposure"),
            ["black", "grey", "branch", "inverse"],
        )
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            [
                "sensor-signal-on-exposure",
                "black",
                "grey",
                "branch",
                "inverse",
                "accepted-export-blocked",
            ],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("label:LogC3", result["preservedResults"])
        self.assertIn("domain:exposure", result["preservedResults"])
        self.assertIn("scene:0.18", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_matching_exposure_coefficients_are_not_an_accepted_export(self):
        self.assertEqual(_MODULE.failed_checks("logc3-exposure", "exposure"), [])
        result = evaluate(
            payload(
                coefficientSet="logc3-exposure",
                valueDomain="exposure",
                acceptedExportRequested=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("label:LogC3", result["preservedResults"])
        self.assertTrue(any("does not accept an export" in item for item in result["reasons"]))

    def test_repeat_near_branch_cut(self):
        result = evaluate(
            payload(locus="branch-cut", sceneLinear="0.010591", acceptedExportRequested=False)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("locus:branch-cut", result["preservedResults"])
        self.assertIn("scene:0.010591", result["preservedResults"])
        self.assertIn("black", result["rejectedClaims"])
        self.assertIn("inverse", result["rejectedClaims"])
        self.assertIn("label:LogC3", result["preservedResults"])

    def test_repeat_highlight_above_scene_linear_one(self):
        result = evaluate(payload(locus="highlight-above-one", sceneLinear="2"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("scene:2", result["preservedResults"])
        self.assertIn("locus:highlight-above-one", result["preservedResults"])
        self.assertIn("sensor-signal-on-exposure", result["rejectedClaims"])
        self.assertIn("accepted-export-blocked", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_other_convention_fails_while_keeping_the_label(self):
        result = evaluate(
            payload(coefficientSet="other-convention", locus="black", sceneLinear="0")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("other-convention", result["rejectedClaims"])
        self.assertEqual(
            _MODULE.failed_checks("other-convention", "exposure"),
            ["black", "grey", "branch", "inverse"],
        )
        self.assertIn("label:LogC3", result["preservedResults"])

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
            {**valid, "sceneLinear": "2", "locus": "grey"},
            {**valid, "acceptedExportRequested": "true"},
            {**valid, "sceneLinear": "-1", "locus": "black"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
