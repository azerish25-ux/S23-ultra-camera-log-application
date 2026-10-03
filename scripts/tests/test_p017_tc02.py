"""TC-P017-02 result differs from request."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p017_tc02", Path(__file__).resolve().parents[1] / "gates" / "p017_tc02.py"
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
        "confirmationPresent": True,
        "showRequestedAsMeasured": False,
    }
    base.update(overrides)
    return base


class TcP01702(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P017-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("requested control target", _MODULE.INTERVENTION)
        self.assertIn("actual observations", _MODULE.EXPECTED)
        self.assertIn("measured values", _MODULE.NEGATIVE)
        self.assertIn("shutter_duration", _MODULE.CONTROLS)
        self.assertIn("active_physical_route", _MODULE.CONTROLS)

    def test_iso_disagreement_withholds_and_keeps_observation(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["200"])
        self.assertNotIn("400", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["confirmed-control readiness withheld"])
        self.assertTrue(any("iso" in item for item in result["reasons"]))

    def test_shutter_duration_omitted_confirmation_is_withheld(self):
        result = evaluate(
            payload(
                control="shutter_duration",
                requested="1/50",
                observed=None,
                confirmationPresent=False,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["confirmation-omitted"])
        self.assertNotIn("1/50", result["preservedResults"])
        self.assertTrue(any("shutter_duration" in item for item in result["reasons"]))

    def test_white_balance_without_confirmation_is_withheld(self):
        result = evaluate(
            payload(
                control="white_balance_lock",
                requested="locked",
                observed="locked",
                confirmationPresent=False,
            )
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["locked"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_lens_focus_match_is_observed_not_qualified(self):
        result = evaluate(
            payload(
                control="lens_focus",
                requested="0.85",
                observed="0.85",
                confirmationPresent=True,
            )
        )
        self.assertEqual(result["decision"], "observed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], ["0.85"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], [])

    def test_active_route_disagreement_preserves_observation(self):
        result = evaluate(
            payload(
                control="active_physical_route",
                requested="physical-2",
                observed="logical-0",
            )
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["logical-0"])
        self.assertNotIn("physical-2", result["preservedResults"])

    def test_showing_requested_as_measured_is_rejected(self):
        result = evaluate(payload(showRequestedAsMeasured=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["requested-as-measured"])
        self.assertEqual(result["preservedResults"], ["200"])
        self.assertNotIn("400", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_requested_as_measured_with_omitted_observation_keeps_omission(self):
        result = evaluate(
            payload(
                control="iso",
                observed=None,
                confirmationPresent=False,
                showRequestedAsMeasured=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["preservedResults"], ["confirmation-omitted"])
        self.assertNotIn("400", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "control": "gain"},
            {**valid, "requested": ""},
            {**valid, "observed": " 200"},
            {**valid, "confirmationPresent": 1},
            {**valid, "observed": None, "confirmationPresent": True},
            {**valid, "showRequestedAsMeasured": "false"},
            {k: v for k, v in valid.items() if k != "control"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
