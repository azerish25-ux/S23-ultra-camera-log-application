"""TC-P062-01 wrong LogC domain coefficients."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p062_tc01", Path(__file__).resolve().parents[1] / "gates" / "p062_tc01.py"
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
        "sampleId": "grey-18",
        "retainedLabel": "LogC3",
        "coefficientSet": "sensor-signal",
        "valueDomain": "exposure",
        "locus": "grey",
        "scene": "0.18",
    }
    base.update(overrides)
    return base


class TcP06201(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P062-01")
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

    def test_sensor_signal_on_exposure_is_rejected(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["sensor-signal-on-exposure", "logc3-label-retained"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("scene:0.18", result["preservedResults"])
        self.assertIn("label:LogC3", result["preservedResults"])
        self.assertIn("grey-18", result["preservedResults"])
        self.assertIn("black:fail", result["preservedResults"])
        self.assertIn("grey:fail", result["preservedResults"])
        self.assertIn("branch:fail", result["preservedResults"])
        self.assertIn("inverse:fail", result["preservedResults"])
        self.assertIn("accepted-export:not-produced", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_other_convention_retaining_logc3_fails_before_export(self):
        result = evaluate(payload(coefficientSet="other-convention", sampleId="other"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("logc3-label-retained", result["rejectedClaims"])
        self.assertNotIn("sensor-signal-on-exposure", result["rejectedClaims"])
        self.assertIn("scene:0.18", result["preservedResults"])
        self.assertIn("coefficients:other-convention", result["preservedResults"])

    def test_repeat_near_the_branch_cut(self):
        result = evaluate(
            payload(sampleId="near-cut", locus="branch-cut", scene="0.009", coefficientSet="sensor-signal")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("scene:0.009", result["preservedResults"])
        self.assertIn("locus:branch-cut", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("accepted-export:not-produced", result["preservedResults"])

    def test_repeat_highlight_above_scene_linear_one(self):
        result = evaluate(
            payload(sampleId="hot", locus="highlight-above-one", scene="2", coefficientSet="sensor-signal")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("scene:2", result["preservedResults"])
        self.assertIn("locus:highlight-above-one", result["preservedResults"])
        self.assertIn("label:LogC3", result["preservedResults"])
        self.assertIn("inverse:fail", result["preservedResults"])

    def test_matching_exposure_coefficients_do_not_produce_an_accepted_export(self):
        result = evaluate(payload(coefficientSet="exposure-convention"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("black:pass", result["preservedResults"])
        self.assertIn("grey:pass", result["preservedResults"])
        self.assertIn("branch:pass", result["preservedResults"])
        self.assertIn("inverse:pass", result["preservedResults"])
        self.assertIn("accepted-export:not-produced", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "rejected"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "scene"},
            {**valid, "extra": True},
            {**valid, "retainedLabel": "LogC"},
            {**valid, "coefficientSet": "logc3"},
            {**valid, "scene": "0.180"},
            {**valid, "scene": "-0.1"},
            {**valid, "locus": "highlight-above-one", "scene": "0.5"},
            {**valid, "locus": "branch-cut", "scene": "0.18"},
            {**valid, "locus": "black", "scene": "0.18"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
