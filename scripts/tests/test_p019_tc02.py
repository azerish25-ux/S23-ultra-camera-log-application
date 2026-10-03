"""TC-P019-02 result differs from request."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p019_tc02", Path(__file__).resolve().parents[1] / "gates" / "p019_tc02.py"
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
        "control": "iso",
        "requested": "800",
        "observed": "200",
        "showRequestedAsMeasured": False,
    }
    base.update(overrides)
    return base


class TcP01902(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P019-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_contract(self):
        self.assertIn("disagree with the requested control target", _MODULE.INTERVENTION)
        self.assertIn("withhold confirmed-control readiness", _MODULE.EXPECTED)
        self.assertEqual(_MODULE.NEGATIVE, "Showing requested settings as measured values must fail.")
        self.assertIn("ISO", _MODULE.REPEAT)
        self.assertIn("shutter duration", _MODULE.REPEAT)

    def test_iso_disagreement_is_withheld_and_keeps_the_observation(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("observed:200", result["preservedResults"])
        self.assertIn("requested:800", result["preservedResults"])
        self.assertIn("confirmed-control", result["rejectedClaims"])
        self.assertNotIn("observed:800", result["preservedResults"])
        self.assertTrue(any("actual observations" in item for item in result["reasons"]))

    def test_shutter_omitted_confirmation_is_withheld(self):
        result = evaluate(
            payload(control="shutter_duration", requested="1/48", observed=None)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("observed:omitted", result["preservedResults"])
        self.assertIn("requested:1/48", result["preservedResults"])
        self.assertIn("confirmation metadata omitted", result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_requested_shown_as_measured_is_rejected(self):
        for control, requested in (
            ("white_balance_lock", "locked"),
            ("lens_focus", "0.8m"),
            ("active_physical_route", "ultra-wide"),
        ):
            result = evaluate(
                payload(
                    control=control,
                    requested=requested,
                    observed=None,
                    showRequestedAsMeasured=True,
                )
            )
            with self.subTest(control=control):
                self.assertEqual(result["decision"], "rejected")
                self.assertNotIn(result["decision"], {"qualified", "allowed"})
                self.assertIn("requested-as-measured", result["rejectedClaims"])
                self.assertIn(control, result["rejectedClaims"])
                self.assertIn("observed:omitted", result["preservedResults"])
                self.assertNotIn("observed:" + requested, result["preservedResults"])

    def test_matching_observation_is_recorded_not_qualified(self):
        result = evaluate(payload(observed="800"))
        self.assertEqual(result["decision"], "observation_recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("observed:800", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "control": "gain"},
            {**valid, "requested": ""},
            {**valid, "observed": ""},
            {**valid, "observed": 200},
            {**valid, "showRequestedAsMeasured": "true"},
            {k: v for k, v in valid.items() if k != "control"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
