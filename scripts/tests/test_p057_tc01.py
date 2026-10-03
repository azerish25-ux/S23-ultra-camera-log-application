"""TC-P057-01 sensor-signal coefficients are not exposure-domain LogC3."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p057_tc01", Path(__file__).resolve().parents[1] / "gates" / "p057_tc01.py"
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
        "convention": "sensor-signal",
        "label": "LogC3",
        "probe": "black",
        "exposure": "0",
    }
    base.update(overrides)
    return base


class TcP05701(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P057-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_sensor_signal_fails_black_grey_branch_and_inverse(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["sensor-signal-on-exposure-domain", "black", "grey", "branch", "inverse"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("exposure:0", result["preservedResults"])
        self.assertIn("exposure-domain:0.092809", result["preservedResults"])

    def test_repeat_near_the_branch_cut(self):
        result = evaluate(payload(probe="branch", exposure="0.010591"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("branch", result["rejectedClaims"])
        self.assertIn("probe:branch", result["preservedResults"])
        self.assertIn("exposure:0.010591", result["preservedResults"])
        self.assertTrue(any("probe branch" in item for item in result["reasons"]))

    def test_repeat_highlight_above_scene_linear_one(self):
        result = evaluate(payload(probe="highlight", exposure="16"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("inverse", result["rejectedClaims"])
        self.assertIn("exposure:16", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_exposure_domain_is_withheld_rather_than_exported(self):
        for probe, exposure in (("grey", "0.18"), ("inverse", "-0.01")):
            result = evaluate(payload(convention="exposure-domain", probe=probe, exposure=exposure))
            self.assertEqual(result["decision"], "withheld")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(f"exposure:{exposure}", result["preservedResults"])
            self.assertTrue(any("no accepted export" in item for item in result["reasons"]))

    def test_other_label_is_rejected_and_keeps_the_exposure(self):
        result = evaluate(payload(label="other", convention="exposure-domain", exposure="0.18"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["label-not-logc3"])
        self.assertIn("exposure:0.18", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "probe"},
            {**valid, "extra": True},
            {**valid, "convention": "scene"},
            {**valid, "probe": "white"},
            {**valid, "exposure": "0.180"},
            {**valid, "exposure": 0},
            {**valid, "label": "logc3"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
