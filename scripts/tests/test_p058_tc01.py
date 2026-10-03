"""TC-P058-01 wrong LogC domain coefficients."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p058_tc01", Path(__file__).resolve().parents[1] / "gates" / "p058_tc01.py"
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
        "coefficientDomain": "logc3-encoded",
        "valueDomain": "logc3-encoded",
        "region": "grey",
        "sceneLinear": "0.18",
        "branchCut": "0.02",
        "blackCheck": "pass",
        "greyCheck": "pass",
        "branchCheck": "pass",
        "inverseCheck": "pass",
    }
    base.update(overrides)
    return base


class TcP05801(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P058-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "accepted"})
        self.assertTrue(result["reasons"])
        self.assertIn("label:LogC3", result["preservedResults"])

    def test_matching_domain_records_checks_without_an_accepted_export(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "checks_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("scene-linear:0.18", result["preservedResults"])
        self.assertTrue(any("not an accepted export" in item for item in result["reasons"]))

    def test_negative_sensor_signal_coefficients_on_exposure_fail(self):
        result = evaluate(
            payload(
                coefficientDomain="sensor-signal",
                valueDomain="exposure",
                blackCheck="pass",
                greyCheck="pass",
                branchCheck="pass",
                inverseCheck="pass",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("sensor-signal-on-exposure", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("coefficients:sensor-signal", result["preservedResults"])
        self.assertIn("values:exposure", result["preservedResults"])
        self.assertIn("black", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "accepted"})

    def test_repeat_near_the_branch_cut(self):
        result = evaluate(
            payload(
                coefficientDomain="exposure",
                valueDomain="exposure",
                region="branch",
                sceneLinear="0.021",
                branchCut="0.02",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("branch", result["rejectedClaims"])
        self.assertIn("scene-linear:0.021", result["preservedResults"])
        self.assertIn("branch-cut:0.02", result["preservedResults"])
        self.assertTrue(any("near branch cut" in item for item in result["reasons"]))

    def test_repeat_highlight_above_scene_linear_one(self):
        result = evaluate(
            payload(
                coefficientDomain="sensor-signal",
                valueDomain="sensor-signal",
                region="highlight",
                sceneLinear="2",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("highlight-above-one", result["rejectedClaims"])
        self.assertIn("wrong-domain-coefficients", result["rejectedClaims"])
        self.assertIn("scene-linear:2", result["preservedResults"])
        self.assertIn("label:LogC3", result["preservedResults"])
        self.assertTrue(any("highlight above scene-linear one" in item for item in result["reasons"]))

    def test_failed_check_on_the_matching_domain_is_rejected(self):
        result = evaluate(payload(inverseCheck="fail"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["inverse"])
        self.assertIn("input-inverse:fail", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "label"},
            {**valid, "extra": True},
            {**valid, "label": "LogC4"},
            {**valid, "coefficientDomain": "linear"},
            {**valid, "sceneLinear": "0.1800"},
            {**valid, "branchCut": "0"},
            {**valid, "blackCheck": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
