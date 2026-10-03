"""TC-P011-01 one throwing query does not erase the timing inventory."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p011_tc01", Path(__file__).resolve().parents[1] / "gates" / "p011_tc01.py"
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
_PROPERTIES = ("route_metadata", "timing_arrays", "dynamic_range", "codec")


def rate(numerator=15, denominator=1):
    return {"numerator": numerator, "denominator": denominator}


def payload(**overrides):
    base = {
        "failedProperty": "timing_arrays",
        "candidates": [
            {"id": "raw-4000", "queryError": "timing arrays threw"},
            {"id": "yuv-1080", "queryError": None},
        ],
        "aeMin": rate(15),
        "aeMax": rate(30),
        "requestedFps": rate(24),
        "manualConfirmed": False,
        "containerTimestampsAssigned": True,
    }
    base.update(overrides)
    return base


class TcP01101(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P011-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native_fixed_24"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)

    def test_encodes_intervention_expected_and_negative(self):
        self.assertIn("characteristic query", _MODULE.INTERVENTION)
        self.assertIn("empty device inventory", _MODULE.EXPECTED)
        self.assertIn("erases every candidate", _MODULE.NEGATIVE)

    def test_one_throw_keeps_the_readable_candidate_and_ae_range(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(
            result["preservedResults"],
            ["yuv-1080", "ae:15/1-30/1", "requested:24/1"],
        )
        self.assertEqual(result["rejectedClaims"], ["timing_arrays", "raw-4000", "native-fixed-24"])
        self.assertIn("manual timing has not been confirmed", result["openQuestions"])
        self.assertNotEqual(result["preservedResults"], [])

    def test_repeats_across_route_timing_dynamic_range_and_codec(self):
        for prop in _PROPERTIES:
            throwing = {"id": "failed-route", "queryError": prop + " threw"}
            healthy = {"id": "jpeg-stills", "queryError": None}
            result = evaluate(payload(failedProperty=prop, candidates=[throwing, healthy]))
            with self.subTest(prop=prop):
                self.assert_contract(result)
                self.assertEqual(result["decision"], "partial")
                self.assertIn("jpeg-stills", result["preservedResults"])
                self.assertIn("ae:15/1-30/1", result["preservedResults"])
                self.assertNotIn("failed-route", result["preservedResults"])
                self.assertEqual(result["rejectedClaims"][0], prop)
                self.assertIn("failed-route", result["rejectedClaims"])
                self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_all_throws_still_keep_the_timing_inventory(self):
        result = evaluate(
            payload(
                failedProperty="route_metadata",
                candidates=[
                    {"id": "raw-4000", "queryError": "route metadata query threw"},
                    {"id": "jpeg-8000", "queryError": "route metadata query threw"},
                ],
                containerTimestampsAssigned=False,
            )
        )
        self.assertEqual(result["preservedResults"], ["ae:15/1-30/1", "requested:24/1"])
        self.assertEqual(result["rejectedClaims"], ["route_metadata", "raw-4000", "jpeg-8000"])
        self.assertNotIn("native-fixed-24", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "candidates"},
            {**valid, "extra": True},
            {**valid, "failedProperty": "shutter"},
            {**valid, "candidates": [{"id": "a", "queryError": None}, {"id": "a", "queryError": None}]},
            {**valid, "aeMin": {"numerator": 30, "denominator": 1}, "aeMax": rate(15)},
            {**valid, "requestedFps": {"numerator": 24, "denominator": 2}},
            {**valid, "manualConfirmed": "false"},
            {**valid, "containerTimestampsAssigned": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
