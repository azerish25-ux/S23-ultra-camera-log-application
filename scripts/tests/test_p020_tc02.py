"""TC-P020-02 host checks. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p020_tc02", Path(__file__).resolve().parents[1] / "gates" / "p020_tc02.py"
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
_INVENTORY = _MODULE.WB_INVENTORY


def _contract(test, result):
    test.assertEqual(tuple(result), _KEYS)
    test.assertEqual(result["caseId"], "TC-P020-02")
    test.assertNotIn(result["decision"], {"qualified", "allowed"})
    test.assertIsInstance(result["reasons"], list)
    test.assertTrue(result["reasons"])
    test.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
    for key in ("rejectedClaims", "preservedResults", "openQuestions"):
        test.assertIsInstance(result[key], list)
        test.assertTrue(all(isinstance(item, str) for item in result[key]))


def _inventory(test, result):
    for item in _INVENTORY:
        test.assertIn(item, result["preservedResults"])


def payload(**overrides):
    base = {
        "control": "iso",
        "requested": "400",
        "observed": "200",
        "presentRequestedAsMeasured": False,
    }
    base.update(overrides)
    return base


class TcP02002(unittest.TestCase):
    def test_module_encodes_the_case_text(self):
        self.assertIn("requested control", _MODULE.INTERVENTION)
        self.assertIn("actual observations", _MODULE.EXPECTED)
        self.assertIn("measured values", _MODULE.NEGATIVE)
        for name in ("iso", "shutter_duration", "white_balance_lock", "lens_focus", "active_physical_route"):
            self.assertIn(name, _MODULE.REPEATS)

    def test_iso_disagreement_is_withheld_and_inventory_stays(self):
        result = evaluate(payload())
        _contract(self, result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("confirmed-control readiness withheld", result["openQuestions"])
        self.assertIn("observed:iso:200", result["preservedResults"])
        self.assertIn("requested:iso:400", result["preservedResults"])
        self.assertNotIn("measured:iso:400", result["preservedResults"])
        _inventory(self, result)
        self.assertTrue(any("iso" in item for item in result["reasons"]))

    def test_white_balance_lock_without_confirmation_is_withheld(self):
        result = evaluate(payload(control="white_balance_lock", requested="locked", observed=None))
        _contract(self, result)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("observed:white_balance_lock:omitted", result["preservedResults"])
        _inventory(self, result)
        self.assertIn("hardware.kelvin:unavailable", result["preservedResults"])

    def test_requested_shutter_shown_as_measured_is_rejected(self):
        result = evaluate(
            payload(control="shutter_duration", requested="1/50", observed="1/120", presentRequestedAsMeasured=True)
        )
        _contract(self, result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "control_confirmed", "withheld"})
        self.assertEqual(result["rejectedClaims"], ["requested-as-measured"])
        self.assertNotIn("measured:shutter_duration:1/50", result["preservedResults"])
        _inventory(self, result)

    def test_lens_focus_match_is_confirmed_without_qualification(self):
        result = evaluate(payload(control="lens_focus", requested="0.35", observed="0.35"))
        self.assertEqual(result["decision"], "control_confirmed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("measured:lens_focus:0.35", result["preservedResults"])
        self.assertEqual(result["openQuestions"], [])
        _inventory(self, result)

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [None, [], {}, {**valid, "control": "kelvin"}, {**valid, "observed": ""}, {**valid, "extra": 1}]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
