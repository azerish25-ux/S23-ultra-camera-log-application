"""TC-P023-02 requested controls are not measured values."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p023_tc02", Path(__file__).resolve().parents[1] / "gates" / "p023_tc02.py"
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
        "observed": "800",
        "presentedAs": "observed",
    }
    base.update(overrides)
    return base


class TcP02302(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P023-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("disagree with the requested control", _MODULE.INTERVENTION)
        self.assertIn("withhold confirmed-control readiness", _MODULE.EXPECTED)
        self.assertIn("Showing requested settings as measured values", _MODULE.NEGATIVE)
        self.assertIn("iso", _MODULE.CONTROLS)
        self.assertIn("active_physical_route", _MODULE.CONTROLS)

    def test_iso_disagreement_is_withheld_and_observation_kept(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            ["control:iso", "requested:400", "800"],
        )
        self.assertIn("confirmed-control readiness withheld", result["openQuestions"])
        self.assertTrue(any(_MODULE.EXPECTED in item for item in result["reasons"]))

    def test_shutter_duration_omitted_confirmation_is_withheld(self):
        result = evaluate(
            payload(control="shutter_duration", requested="1/48", observed=None, presentedAs="observed")
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("confirmation-omitted", result["preservedResults"])
        self.assertIn("requested:1/48", result["preservedResults"])
        self.assertNotIn("1/48", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_white_balance_shown_as_requested_is_rejected(self):
        result = evaluate(
            payload(
                control="white_balance_lock",
                requested="locked",
                observed="unlocked",
                presentedAs="requested",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})
        self.assertEqual(result["rejectedClaims"], ["requested-shown-as-measured"])
        self.assertIn("unlocked", result["preservedResults"])
        self.assertIn("requested:locked", result["preservedResults"])
        self.assertTrue(any(_MODULE.NEGATIVE in item for item in result["reasons"]))

    def test_lens_focus_and_route_keep_observations(self):
        focus = evaluate(
            payload(control="lens_focus", requested="1.2m", observed="0.8m", presentedAs="observed")
        )
        route = evaluate(
            payload(
                control="active_physical_route",
                requested="physical-2",
                observed="logical-0",
                presentedAs="observed",
            )
        )
        self.assertEqual(focus["decision"], "withheld")
        self.assertEqual(route["decision"], "withheld")
        self.assertIn("0.8m", focus["preservedResults"])
        self.assertIn("logical-0", route["preservedResults"])
        self.assertNotIn(focus["decision"], {"qualified", "allowed"})
        self.assertNotIn(route["decision"], {"qualified", "allowed"})

    def test_route_request_presented_as_measured_fails(self):
        result = evaluate(
            payload(
                control="active_physical_route",
                requested="physical-2",
                observed=None,
                presentedAs="requested",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("confirmation-omitted", result["preservedResults"])
        self.assertIn("requested:physical-2", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {**valid, "control": "gain"},
            {**valid, "observed": "400"},
            {**valid, "presentedAs": "measured"},
            {**valid, "requested": ""},
            {**valid, "observed": 800},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
