"""TC-P022-02 observations are not replaced by the request."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p022_tc02", Path(__file__).resolve().parents[1] / "gates" / "p022_tc02.py"
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
_HASH = "cm-result-differs"


def payload(**overrides):
    base = {
        "control": "iso",
        "requested": "400",
        "observed": "320",
        "confirmationPresent": True,
        "displayRequestedAsMeasured": False,
        "cleanMasterHash": _HASH,
    }
    base.update(overrides)
    return base


class TcP02202(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P022-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("requested control target", _MODULE.INTERVENTION)
        self.assertIn("actual observations", _MODULE.EXPECTED)
        self.assertIn("measured values", _MODULE.NEGATIVE)

    def test_iso_disagreement_is_withheld_and_shows_the_observation(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["320", "iso", _HASH])
        self.assertNotIn("400", result["preservedResults"])
        self.assertIn("confirmed-control readiness withheld", result["openQuestions"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_shutter_duration_without_confirmation_is_withheld(self):
        result = evaluate(
            payload(
                control="shutter_duration",
                requested="1/48",
                observed="1/48",
                confirmationPresent=False,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["1/48", "shutter_duration", _HASH])
        self.assertIn("confirmation metadata omitted", result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_showing_requested_iso_as_measured_is_rejected(self):
        result = evaluate(payload(displayRequestedAsMeasured=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld", "observed"})
        self.assertEqual(result["rejectedClaims"], ["requested-shown-as-measured"])
        self.assertEqual(result["preservedResults"], ["320", "iso", _HASH])
        self.assertNotIn("400", result["preservedResults"])

    def test_lens_focus_omitted_observation_keeps_the_clean_master(self):
        result = evaluate(
            payload(control="lens_focus", requested="0.4m", observed=None, confirmationPresent=False)
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"][0], "observation-omitted")
        self.assertIn(_HASH, result["preservedResults"])
        self.assertNotIn("0.4m", result["preservedResults"])

    def test_matching_white_balance_with_confirmation_is_observed(self):
        result = evaluate(
            payload(
                control="white_balance_lock",
                requested="locked",
                observed="locked",
                confirmationPresent=True,
            )
        )
        self.assertEqual(result["decision"], "observed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["openQuestions"], [])
        self.assertEqual(result["preservedResults"], ["locked", "white_balance_lock", _HASH])

    def test_active_physical_route_request_is_not_the_measurement(self):
        result = evaluate(
            payload(
                control="active_physical_route",
                requested="physical-2",
                observed="logical-0",
                displayRequestedAsMeasured=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("logical-0", result["preservedResults"])
        self.assertNotIn("physical-2", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "control": "gain"},
            {**valid, "observed": ""},
            {**valid, "confirmationPresent": "true"},
            {**valid, "requested": 400},
            {k: v for k, v in valid.items() if k != "control"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
