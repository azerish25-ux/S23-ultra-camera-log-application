"""TC-P009-02 advertised but unusable camera route."""

from __future__ import annotations

import importlib.util
import json
import math
import re
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p009_tc02", Path(__file__).resolve().parents[1] / "gates" / "p009_tc02.py"
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
_FAILURES = ("session_rejected", "startup_timeout", "stream_mismatch")


def route(**overrides):
    base = {
        "logicalId": "rear",
        "physicalId": "tele-sensor",
        "publicCameraIds": ["rear", "front"],
        "focalMm": None,
        "queryError": None,
        "advertised": True,
        "configured": False,
        "samples": 0,
        "openPhysicalIndependently": False,
    }
    base.update(overrides)
    return base


def _texts(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _texts(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _texts(item)


class TcP00902(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P009-02")
        self.assertIn(result["decision"], {"advertised_only", "qualified", "rejected"})
        self.assertNotEqual(result["decision"], "allowed")
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def assertNoFabricatedFocal(self, result):
        for text in _texts(result):
            if text == result["caseId"]:
                continue
            self.assertIsNone(re.search(r"\d", text), f"fabricated number in {text!r}")
        self.assertNotIn("mm", json.dumps(result).lower())

    def test_baseline_advertised_unconfigured_uses_logical_owner_and_unknown_focal(self):
        result = evaluate(
            {"route": route(advertised=True, configured=False, samples=0), "failureMode": "none"}
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["rear/tele-sensor/none"])
        self.assertEqual(result["preservedResults"], ["advertised:rear"])
        self.assertEqual(result["openQuestions"], ["focal unknown"])
        self.assertTrue(any(item == "tele-sensor addressed via rear" for item in result["reasons"]))
        self.assertNoFabricatedFocal(result)

    def test_configure_request_alone_is_not_qualified(self):
        result = evaluate(
            {
                "route": route(advertised=True, configured=True, samples=0, focalMm=None),
                "failureMode": "none",
            }
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["rear/tele-sensor/none"])
        self.assertEqual(result["preservedResults"], ["advertised:rear"])
        self.assertIn("focal unknown", result["openQuestions"])
        self.assertNoFabricatedFocal(result)

    def test_measured_route_is_qualified_without_inventing_focal(self):
        result = evaluate(
            {
                "route": route(advertised=True, configured=True, samples=4, focalMm=None),
                "failureMode": "none",
            }
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "qualified")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["rear:tele-sensor"])
        self.assertNotIn("advertised:rear", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["focal unknown"])
        self.assertTrue(any("addressed via rear" in item for item in result["reasons"]))
        self.assertNoFabricatedFocal(result)

    def test_failure_modes_repeat_as_advertised_only(self):
        for mode in _FAILURES:
            result = evaluate(
                {
                    "route": route(advertised=True, configured=True, samples=8, focalMm=None),
                    "failureMode": mode,
                }
            )
            self.assertContract(result)
            self.assertEqual(result["decision"], "advertised_only")
            self.assertNotIn(result["decision"], {"qualified", "allowed"})
            self.assertEqual(result["rejectedClaims"], [f"rear/tele-sensor/{mode}"])
            self.assertEqual(result["preservedResults"], ["advertised:rear"])
            self.assertEqual(result["openQuestions"], ["focal unknown"])
            self.assertTrue(any("addressed via rear" in item for item in result["reasons"]))
            self.assertNoFabricatedFocal(result)

    def test_advertised_but_not_configured_with_samples_is_not_qualified(self):
        result = evaluate(
            {
                "route": route(advertised=True, configured=False, samples=5),
                "failureMode": "none",
            }
        )
        self.assertEqual(result["decision"], "advertised_only")
        self.assertEqual(result["rejectedClaims"], ["rear/tele-sensor/none"])
        self.assertEqual(result["preservedResults"], ["advertised:rear"])

    def test_samples_zero_without_advertisement_is_rejected(self):
        result = evaluate(
            {
                "route": route(advertised=False, configured=True, samples=0, physicalId=None),
                "failureMode": "none",
            }
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "advertised_only"})
        self.assertEqual(result["rejectedClaims"], ["rear:logical"])
        self.assertEqual(result["preservedResults"], [])
        self.assertNotIn("None", result["rejectedClaims"])

    def test_open_physical_independently_is_rejected_not_qualified(self):
        result = evaluate(
            {
                "route": route(
                    advertised=True,
                    configured=True,
                    samples=4,
                    openPhysicalIndependently=True,
                    focalMm=None,
                ),
                "failureMode": "none",
            }
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertNotEqual(result["decision"], "allowed")
        self.assertEqual(result["rejectedClaims"], ["rear:tele-sensor"])
        self.assertEqual(result["preservedResults"], ["advertised:rear"])
        self.assertEqual(result["openQuestions"], ["focal unknown"])
        self.assertTrue(any("addressed via rear" in item for item in result["reasons"]))
        self.assertNoFabricatedFocal(result)

    def test_independent_open_wins_over_failure_mode(self):
        result = evaluate(
            {
                "route": route(
                    advertised=True,
                    configured=True,
                    samples=4,
                    openPhysicalIndependently=True,
                ),
                "failureMode": "startup_timeout",
            }
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(
            result["rejectedClaims"],
            ["rear:tele-sensor", "rear/tele-sensor/startup_timeout"],
        )
        self.assertIn("advertised:rear", result["preservedResults"])

    def test_public_member_with_known_focal_qualifies_without_owner_bridge(self):
        result = evaluate(
            {
                "route": route(
                    physicalId="rear",
                    publicCameraIds=["rear"],
                    focalMm=24,
                    advertised=True,
                    configured=True,
                    samples=2,
                ),
                "failureMode": "none",
            }
        )
        self.assertEqual(result["decision"], "qualified")
        self.assertEqual(result["openQuestions"], [])
        self.assertEqual(result["preservedResults"], ["rear:rear"])
        self.assertFalse(any("addressed via" in item for item in result["reasons"]))
        self.assertNotIn("24", json.dumps(result))

    def test_unadvertised_configured_stream_is_rejected(self):
        result = evaluate(
            {
                "route": route(
                    advertised=False,
                    configured=True,
                    samples=3,
                    physicalId="tele-sensor",
                    focalMm=35,
                ),
                "failureMode": "none",
            }
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "advertised_only"})
        self.assertEqual(result["rejectedClaims"], ["rear:tele-sensor"])
        self.assertEqual(result["preservedResults"], [])
        self.assertEqual(result["openQuestions"], [])
        self.assertNotIn("35", json.dumps(result))

    def test_invalid_payload_raises(self):
        valid = route(advertised=True, configured=True, samples=1)
        cases = [
            None,
            [],
            {},
            {"route": valid},
            {"failureMode": "none"},
            {"route": valid, "failureMode": "none", "extra": True},
            {"route": valid, "failureMode": "timeout"},
            {"route": valid, "failureMode": "NONE"},
            {"route": valid, "failureMode": None},
            {"route": [valid], "failureMode": "none"},
            {"route": {**valid, "lens": 50}, "failureMode": "none"},
            {"route": {k: v for k, v in valid.items() if k != "samples"}, "failureMode": "none"},
            {"route": {**valid, "logicalId": ""}, "failureMode": "none"},
            {"route": {**valid, "physicalId": ""}, "failureMode": "session_rejected"},
            {"route": {**valid, "publicCameraIds": ("rear",)}, "failureMode": "none"},
            {"route": {**valid, "focalMm": True}, "failureMode": "none"},
            {"route": {**valid, "focalMm": math.nan}, "failureMode": "none"},
            {"route": {**valid, "queryError": ""}, "failureMode": "none"},
            {"route": {**valid, "advertised": "true"}, "failureMode": "none"},
            {"route": {**valid, "configured": 0}, "failureMode": "none"},
            {"route": {**valid, "samples": True}, "failureMode": "none"},
            {"route": {**valid, "samples": -1}, "failureMode": "stream_mismatch"},
            {"route": {**valid, "samples": 1.5}, "failureMode": "none"},
            {"route": {**valid, "openPhysicalIndependently": 1}, "failureMode": "none"},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
