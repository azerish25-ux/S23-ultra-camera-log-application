"""TC-P009-01 partial camera-route characteristic failure."""

from __future__ import annotations

import importlib.util
import json
import math
import re
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p009_tc01", Path(__file__).resolve().parents[1] / "gates" / "p009_tc01.py"
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
_PROPERTIES = ("metadata", "timing", "dynamic_range", "codec")


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


class TcP00901(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P009-01")
        self.assertIn(result["decision"], {"partial", "inventoried"})
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
        self.assertNotIn("lens", json.dumps({k: v for k, v in result.items() if k != "caseId"}).lower())

    def test_baseline_addresses_hidden_physical_and_unknown_focal(self):
        result = evaluate({"routes": [route()], "failedProperty": "metadata"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "inventoried")
        self.assertEqual(result["preservedResults"], ["rear:tele-sensor"])
        self.assertEqual(result["rejectedClaims"], ["metadata"])
        self.assertEqual(result["openQuestions"], ["focal unknown"])
        self.assertTrue(any("tele-sensor addressed via rear" == item for item in result["reasons"]))
        self.assertNoFabricatedFocal(result)

    def test_single_query_error_preserves_the_other_route(self):
        good = route()
        bad = route(logicalId="front", physicalId=None, focalMm=24, queryError="characteristic throw")
        result = evaluate({"routes": [good, bad], "failedProperty": "metadata"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertIn("rear:tele-sensor", result["preservedResults"])
        self.assertNotIn("front:logical", result["preservedResults"])
        self.assertEqual(result["preservedResults"], ["rear:tele-sensor"])
        self.assertIn("metadata", result["rejectedClaims"])
        self.assertIn("front:logical", result["rejectedClaims"])
        self.assertNotIn("rear:tele-sensor", result["rejectedClaims"])
        self.assertEqual(result["openQuestions"], ["focal unknown"])
        self.assertNotIn("24", json.dumps(result))

    def test_repeat_failed_property_keeps_readable_route(self):
        for prop in _PROPERTIES:
            good = route(queryError=None)
            bad = route(
                logicalId="front",
                physicalId=None,
                focalMm=24,
                queryError=f"{prop} unavailable",
            )
            result = evaluate({"routes": [bad, good], "failedProperty": prop})
            self.assertContract(result)
            self.assertEqual(result["decision"], "partial")
            self.assertEqual(result["preservedResults"], ["rear:tele-sensor"])
            self.assertEqual(result["rejectedClaims"], [prop, "front:logical"])
            self.assertIn("focal unknown", result["openQuestions"])
            self.assertTrue(any("addressed via rear" in item for item in result["reasons"]))
            self.assertNotIn("24", json.dumps(result))

    def test_three_routes_middle_error_does_not_erase_candidates(self):
        routes = [
            route(
                logicalId="wide",
                physicalId="wide-sensor",
                publicCameraIds=["wide", "wide-sensor"],
                focalMm=18,
            ),
            route(queryError="timing arrays threw"),
            route(logicalId="front", physicalId="front-sensor", publicCameraIds=["front", "front-sensor"], focalMm=26),
        ]
        result = evaluate({"routes": routes, "failedProperty": "timing"})
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(
            result["preservedResults"],
            ["wide:wide-sensor", "front:front-sensor"],
        )
        self.assertEqual(result["rejectedClaims"], ["timing", "rear:tele-sensor"])
        self.assertTrue(any("tele-sensor addressed via rear" == item for item in result["reasons"]))
        self.assertFalse(any("addressed via front" in item for item in result["reasons"]))
        self.assertFalse(any("addressed via wide" in item for item in result["reasons"]))

    def test_all_routes_throwing_is_partial_not_silent_empty_inventory(self):
        result = evaluate(
            {
                "routes": [
                    route(queryError="metadata threw"),
                    route(logicalId="front", physicalId=None, queryError="metadata threw"),
                ],
                "failedProperty": "metadata",
            }
        )
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], [])
        self.assertEqual(
            result["rejectedClaims"],
            ["metadata", "rear:tele-sensor", "front:logical"],
        )
        self.assertTrue(result["reasons"])

    def test_open_physical_independently_is_rejected_and_not_allowed(self):
        mutant = route(openPhysicalIndependently=True)
        other = route(logicalId="front", physicalId=None, focalMm=24)
        result = evaluate({"routes": [mutant, other], "failedProperty": "codec"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "inventoried")
        self.assertNotEqual(result["decision"], "allowed")
        self.assertIn("rear:tele-sensor", result["rejectedClaims"])
        self.assertIn("rear:tele-sensor", result["preservedResults"])
        self.assertIn("front:logical", result["preservedResults"])
        self.assertTrue(any("openPhysicalIndependently" in item for item in result["reasons"]))

    def test_mutant_and_query_error_on_same_route_listed_once(self):
        bad = route(queryError="codec query threw", openPhysicalIndependently=True)
        good = route(logicalId="wide", physicalId="wide-sensor", focalMm=18, queryError=None)
        result = evaluate({"routes": [bad, good], "failedProperty": "dynamic_range"})
        self.assertEqual(result["decision"], "partial")
        self.assertNotEqual(result["decision"], "allowed")
        self.assertEqual(result["preservedResults"], ["wide:wide-sensor"])
        self.assertEqual(result["rejectedClaims"], ["dynamic_range", "rear:tele-sensor"])

    def test_known_focal_is_not_reported_unknown_and_public_member_needs_no_owner_bridge(self):
        result = evaluate(
            {
                "routes": [
                    route(
                        physicalId="rear",
                        publicCameraIds=["rear"],
                        focalMm=24,
                    )
                ],
                "failedProperty": "codec",
            }
        )
        self.assertEqual(result["decision"], "inventoried")
        self.assertEqual(result["openQuestions"], [])
        self.assertEqual(result["preservedResults"], ["rear:rear"])
        self.assertFalse(any("addressed via" in item for item in result["reasons"]))
        self.assertNotIn("24", json.dumps(result))

    def test_logical_only_route_uses_logical_token(self):
        result = evaluate(
            {
                "routes": [route(physicalId=None, focalMm=None)],
                "failedProperty": "timing",
            }
        )
        self.assertEqual(result["preservedResults"], ["rear:logical"])
        self.assertEqual(result["openQuestions"], ["focal unknown"])
        self.assertFalse(any("addressed via" in item for item in result["reasons"]))
        self.assertNoFabricatedFocal(result)

    def test_invalid_payload_raises(self):
        valid = route()
        cases = [
            None,
            [],
            {},
            {"routes": [valid]},
            {"failedProperty": "metadata"},
            {"routes": [valid], "failedProperty": "metadata", "extra": 1},
            {"routes": [valid], "failedProperty": "Metadata"},
            {"routes": [valid], "failedProperty": "focus"},
            {"routes": valid, "failedProperty": "metadata"},
            {"routes": [None], "failedProperty": "metadata"},
            {"routes": ["rear"], "failedProperty": "codec"},
            {"routes": [{**valid, "lens": "invented"}], "failedProperty": "metadata"},
            {"routes": [{k: v for k, v in valid.items() if k != "focalMm"}], "failedProperty": "metadata"},
            {"routes": [{**valid, "logicalId": ""}], "failedProperty": "metadata"},
            {"routes": [{**valid, "logicalId": 0}], "failedProperty": "metadata"},
            {"routes": [{**valid, "physicalId": ""}], "failedProperty": "metadata"},
            {"routes": [{**valid, "physicalId": 2}], "failedProperty": "metadata"},
            {"routes": [{**valid, "publicCameraIds": "rear"}], "failedProperty": "metadata"},
            {"routes": [{**valid, "publicCameraIds": [0]}], "failedProperty": "metadata"},
            {"routes": [{**valid, "focalMm": True}], "failedProperty": "metadata"},
            {"routes": [{**valid, "focalMm": "24"}], "failedProperty": "metadata"},
            {"routes": [{**valid, "focalMm": math.nan}], "failedProperty": "metadata"},
            {"routes": [{**valid, "focalMm": math.inf}], "failedProperty": "metadata"},
            {"routes": [{**valid, "queryError": ""}], "failedProperty": "metadata"},
            {"routes": [{**valid, "queryError": 1}], "failedProperty": "metadata"},
            {"routes": [{**valid, "advertised": 1}], "failedProperty": "metadata"},
            {"routes": [{**valid, "configured": "false"}], "failedProperty": "metadata"},
            {"routes": [{**valid, "samples": True}], "failedProperty": "metadata"},
            {"routes": [{**valid, "samples": -1}], "failedProperty": "metadata"},
            {"routes": [{**valid, "samples": 1.0}], "failedProperty": "metadata"},
            {"routes": [{**valid, "openPhysicalIndependently": "false"}], "failedProperty": "metadata"},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
