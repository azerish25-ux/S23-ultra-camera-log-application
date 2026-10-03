"""TC-P021-02 result differs from request."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p021_tc02", Path(__file__).resolve().parents[1] / "gates" / "p021_tc02.py"
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
        "requested": "400",
        "observed": "200",
        "presentRequestedAsMeasured": False,
    }
    base.update(overrides)
    return base


class TcP02102(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P021-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        for token in _MODULE.FOCUS_INVENTORY:
            self.assertIn(token, result["preservedResults"])

    def test_module_encodes_intervention_expected_and_negative(self):
        self.assertIn("disagree with the requested control", _MODULE.INTERVENTION)
        self.assertIn("withhold confirmed-control readiness", _MODULE.EXPECTED)
        self.assertIn("requested settings as measured", _MODULE.NEGATIVE)
        for name in ("iso", "shutter_duration", "white_balance_lock", "lens_focus", "active_physical_route"):
            self.assertIn(name, _MODULE.REPEATS)

    def test_repeat_iso_disagreement_is_withheld(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("observed:iso:200", result["preservedResults"])
        self.assertIn("requested:iso:400", result["preservedResults"])
        self.assertNotIn("measured:iso:400", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["confirmed-control readiness withheld"])
        self.assertTrue(any("repeat control iso" in item for item in result["reasons"]))

    def test_repeat_lens_focus_omits_confirmation(self):
        result = evaluate(payload(control="lens_focus", requested="0.62", observed=None))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("observed:lens_focus:omitted", result["preservedResults"])
        self.assertNotIn("measured:lens_focus:0.62", result["preservedResults"])
        self.assertIn("physical.distance:unknown", result["preservedResults"])
        self.assertTrue(any("lens_focus" in item for item in result["reasons"]))

    def test_repeat_shutter_and_route_match_can_confirm(self):
        shutter = evaluate(
            payload(control="shutter_duration", requested="1/48", observed="1/48")
        )
        route = evaluate(
            payload(control="active_physical_route", requested="0", observed="0")
        )
        lock = evaluate(
            payload(control="white_balance_lock", requested="locked", observed="locked")
        )
        for result, token in (
            (shutter, "measured:shutter_duration:1/48"),
            (route, "measured:active_physical_route:0"),
            (lock, "measured:white_balance_lock:locked"),
        ):
            self.assertContract(result)
            self.assertEqual(result["decision"], "control_confirmed")
            self.assertNotIn(result["decision"], {"qualified", "allowed"})
            self.assertIn(token, result["preservedResults"])
            self.assertEqual(result["openQuestions"], [])

    def test_negative_does_not_present_request_as_measured(self):
        result = evaluate(payload(presentRequestedAsMeasured=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "control_confirmed"})
        self.assertIn("requested-as-measured", result["rejectedClaims"])
        self.assertIn("observed:iso:200", result["preservedResults"])
        self.assertNotIn("measured:iso:400", result["preservedResults"])
        self.assertFalse(any(item.startswith("measured:") for item in result["preservedResults"]))
        self.assertIn("virtual.relativeDepth:0.62", result["preservedResults"])

    def test_negative_lens_focus_request_is_not_a_measurement(self):
        result = evaluate(
            payload(
                control="lens_focus",
                requested="0.62",
                observed=None,
                presentRequestedAsMeasured=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn("measured:lens_focus:0.62", result["preservedResults"])
        self.assertIn("physical.distance:unknown", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "control": "focus"},
            {**valid, "observed": 200},
            {**valid, "presentRequestedAsMeasured": 1},
            {**valid, "requested": " 400"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
