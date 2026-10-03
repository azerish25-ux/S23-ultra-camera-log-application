"""TC-P064-01 wrong LogC domain coefficients."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p064_tc01", Path(__file__).resolve().parents[1] / "gates" / "p064_tc01.py"
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
        "coefficientSet": "logc3-exposure",
        "valueDomain": "exposure",
        "locus": "grey",
        "blackPass": True,
        "greyPass": True,
        "branchPass": True,
        "inversePass": True,
        "sceneLinear": "0.18",
    }
    base.update(overrides)
    return base


class TcP06401(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P064-01")
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
        self.assertIn("scene-linear one", _MODULE.REPEAT)

    def test_matching_coefficients_are_withheld_not_an_accepted_export(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("LogC3", result["preservedResults"])
        self.assertIn("scene-linear:0.18", result["preservedResults"])
        self.assertIn("coefficients:logc3-exposure", result["preservedResults"])

    def test_failed_black_grey_branch_and_inverse_block_export(self):
        result = evaluate(payload(blackPass=False, greyPass=False, branchPass=False, inversePass=False, locus="black", sceneLinear="0"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["black-test", "grey-test", "branch-test", "inverse-test"],
        )
        self.assertIn("LogC3", result["preservedResults"])
        self.assertIn("scene-linear:0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_sensor_signal_on_exposure_domain_fails(self):
        result = evaluate(
            payload(coefficientSet="sensor-signal", valueDomain="exposure", locus="grey", sceneLinear="0.18")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["sensor-signal-on-exposure-domain", "wrong-coefficient-convention"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("LogC3", result["preservedResults"])
        self.assertIn("domain:exposure", result["preservedResults"])
        self.assertIn("coefficients:sensor-signal", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_repeat_near_the_branch_cut(self):
        result = evaluate(payload(locus="branch-cut", sceneLinear="0.19", branchPass=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["branch-test"])
        self.assertIn("locus:branch-cut", result["preservedResults"])
        self.assertIn("scene-linear:0.19", result["preservedResults"])
        self.assertIn("LogC3", result["preservedResults"])

    def test_repeat_highlight_above_scene_linear_one(self):
        result = evaluate(payload(locus="above-one", sceneLinear="2", inversePass=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["inverse-test"])
        self.assertIn("scene-linear:2", result["preservedResults"])
        self.assertIn("locus:above-one", result["preservedResults"])
        clean = evaluate(payload(locus="above-one", sceneLinear="4"))
        self.assertEqual(clean["decision"], "withheld")
        self.assertIn("scene-linear:4", clean["preservedResults"])
        self.assertNotIn(clean["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "sceneLinear"},
            {**valid, "extra": True},
            {**valid, "label": "LogC4"},
            {**valid, "coefficientSet": "LogC3"},
            {**valid, "blackPass": "true"},
            {**valid, "sceneLinear": "0.180"},
            {**valid, "locus": "above-one", "sceneLinear": "1"},
            {**valid, "locus": "branch-cut", "sceneLinear": "2"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
