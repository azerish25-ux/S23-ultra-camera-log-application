"""TC-P016-01 partial characteristic failure."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p016_tc01", Path(__file__).resolve().parents[1] / "gates" / "p016_tc01.py"
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
_ORACLE = ["file-retained", "playback:separate", "cadence:separate"]
_PROPERTIES = ("route_metadata", "timing", "dynamic_range", "codec")
_QUERY_ERRORS = {
    "route_metadata": "route metadata query threw",
    "timing": "timing arrays threw",
    "dynamic_range": "dynamic-range profile query threw",
    "codec": "optional codec query threw",
}


def stream(**overrides):
    base = {
        "logicalId": "rear",
        "format": "RAW_SENSOR",
        "width": 4000,
        "height": 3000,
        "advertised": True,
        "configured": False,
        "samples": 0,
        "queryError": None,
    }
    base.update(overrides)
    return base


def _identity(item):
    return f"{item['width']}x{item['height']}:{item['format']}@{item['logicalId']}"


class TcP01601(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P016-01")
        self.assertEqual(result["decision"], "partial")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
        self.assertEqual(result["openQuestions"], ["not-endurance-certified"])
        for token in _ORACLE:
            self.assertIn(token, result["preservedResults"])
        self.assertNotEqual(result["preservedResults"], [])

    def test_contract_text_is_encoded(self):
        self.assertIn("characteristic query throw", _MODULE.INTERVENTION)
        self.assertIn("empty device inventory", _MODULE.EXPECTED)
        self.assertIn("must fail", _MODULE.NEGATIVE)

    def test_route_metadata_throw_keeps_other_routes(self):
        throwing = stream(queryError=_QUERY_ERRORS["route_metadata"])
        healthy = stream(logicalId="front", format="YUV_420_888", width=1920, height=1080)
        result = evaluate({"streams": [throwing, healthy], "failedProperty": "route_metadata"})
        self.assertContract(result)
        self.assertEqual(
            result["preservedResults"],
            ["1920x1080:YUV_420_888@front", *_ORACLE],
        )
        self.assertEqual(
            result["rejectedClaims"],
            ["route_metadata", "4000x3000:RAW_SENSOR@rear"],
        )
        self.assertNotIn("1920x1080:YUV_420_888@front", result["rejectedClaims"])

    def test_timing_arrays_throw_keeps_readable_formats(self):
        streams = [
            stream(queryError=_QUERY_ERRORS["timing"]),
            stream(format="JPEG", width=8000, height=6000),
            stream(logicalId="front", format="YUV_420_888", width=1920, height=1080),
        ]
        result = evaluate({"streams": streams, "failedProperty": "timing"})
        self.assertContract(result)
        self.assertEqual(
            result["preservedResults"],
            ["8000x6000:JPEG@rear", "1920x1080:YUV_420_888@front", *_ORACLE],
        )
        self.assertIn("timing", result["rejectedClaims"])
        self.assertTrue(any("timing" in item for item in result["reasons"]))

    def test_dynamic_range_profile_throw_keeps_neighbors(self):
        streams = [
            stream(logicalId="wide", format="RAW_SENSOR", width=4000, height=3000),
            stream(format="JPEG", width=8000, height=6000, queryError=_QUERY_ERRORS["dynamic_range"]),
            stream(logicalId="front", format="YUV_420_888", width=1920, height=1080),
        ]
        result = evaluate({"streams": streams, "failedProperty": "dynamic_range"})
        self.assertContract(result)
        self.assertEqual(
            result["preservedResults"],
            ["4000x3000:RAW_SENSOR@wide", "1920x1080:YUV_420_888@front", *_ORACLE],
        )
        self.assertEqual(
            result["rejectedClaims"],
            ["dynamic_range", "8000x6000:JPEG@rear"],
        )

    def test_optional_codec_query_throw_keeps_one_healthy_stream(self):
        result = evaluate(
            {
                "streams": [
                    stream(logicalId="front", queryError=_QUERY_ERRORS["codec"]),
                    stream(format="YUV_420_888", width=1920, height=1080),
                    stream(logicalId="wide", queryError=_QUERY_ERRORS["codec"]),
                ],
                "failedProperty": "codec",
            }
        )
        self.assertContract(result)
        self.assertEqual(result["preservedResults"], ["1920x1080:YUV_420_888@rear", *_ORACLE])
        self.assertIn("codec", result["rejectedClaims"])

    def test_failed_property_is_repeated_across_the_four_queries(self):
        healthy = stream(format="YUV_420_888", width=1920, height=1080)
        for prop in _PROPERTIES:
            throwing = stream(queryError=_QUERY_ERRORS[prop])
            result = evaluate({"streams": [throwing, healthy], "failedProperty": prop})
            with self.subTest(prop=prop):
                self.assertContract(result)
                self.assertIn("1920x1080:YUV_420_888@rear", result["preservedResults"])
                self.assertIn(prop, result["rejectedClaims"])
                self.assertNotIn(_identity(healthy), result["rejectedClaims"])

    def test_all_throws_still_keep_the_baseline_take(self):
        raw = stream(queryError="route metadata query threw")
        jpeg = stream(format="JPEG", width=8000, height=6000, queryError="route metadata query threw")
        result = evaluate({"streams": [raw, jpeg], "failedProperty": "route_metadata"})
        self.assertContract(result)
        self.assertEqual(result["preservedResults"], _ORACLE)
        self.assertEqual(
            result["rejectedClaims"],
            ["route_metadata", "4000x3000:RAW_SENSOR@rear", "8000x6000:JPEG@rear"],
        )

    def test_empty_stream_list_is_not_an_empty_inventory(self):
        result = evaluate({"streams": [], "failedProperty": "codec"})
        self.assertContract(result)
        self.assertEqual(result["preservedResults"], _ORACLE)
        self.assertEqual(result["rejectedClaims"], ["codec"])

    def test_invalid_payload_raises(self):
        valid = stream()
        cases = [
            None,
            [],
            {},
            {"streams": [valid]},
            {"failedProperty": "timing"},
            {"streams": [valid], "failedProperty": "timing", "extra": 1},
            {"streams": [valid], "failedProperty": "metadata"},
            {"streams": [valid], "failedProperty": None},
            {"streams": [None], "failedProperty": "codec"},
            {"streams": [{**valid, "width": True}], "failedProperty": "timing"},
            {"streams": [{**valid, "queryError": ""}], "failedProperty": "timing"},
            {"streams": [{**valid, "samples": -1}], "failedProperty": "codec"},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
