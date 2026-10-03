"""TC-P014-01 partial ordinary-stream characteristic failure."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p014_tc01", Path(__file__).resolve().parents[1] / "gates" / "p014_tc01.py"
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


class TcP01401(unittest.TestCase):
    def test_module_encodes_the_case_text(self):
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Make one camera characteristic query throw while unrelated formats and routes remain readable.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Retain unaffected capabilities and report the failed property explicitly "
            "rather than returning an empty device inventory.",
        )
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A single exception that erases every candidate must fail.",
        )

    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P014-01")
        self.assertIn(result["decision"], {"partial", "inventoried"})
        self.assertNotEqual(result["decision"], "allowed")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_failed_property_keeps_raw_and_larger_jpeg(self):
        raw = stream()
        jpeg = stream(format="JPEG", width=8000, height=6000)
        result = evaluate({"streams": [raw, jpeg], "failedProperty": "timing"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(
            result["preservedResults"],
            ["4000x3000:RAW_SENSOR@rear", "8000x6000:JPEG@rear"],
        )
        self.assertNotEqual(result["preservedResults"], [])
        self.assertEqual(result["rejectedClaims"], ["timing"])
        self.assertEqual(result["openQuestions"], [])
        self.assertTrue(
            any("advertisement is not operational qualification" == item for item in result["reasons"])
        )
        self.assertTrue(any("timing" in item for item in result["reasons"]))

    def test_one_throw_retains_healthy_1920x1080_across_queries(self):
        for prop in _PROPERTIES:
            throwing = stream(queryError=_QUERY_ERRORS[prop])
            healthy = stream(
                logicalId="rear",
                format="YUV_420_888",
                width=1920,
                height=1080,
                advertised=True,
                queryError=None,
            )
            result = evaluate({"streams": [throwing, healthy], "failedProperty": prop})
            with self.subTest(prop=prop):
                self.assertContract(result)
                self.assertEqual(result["decision"], "partial")
                self.assertEqual(result["preservedResults"], ["1920x1080:YUV_420_888@rear"])
                self.assertNotEqual(result["preservedResults"], [])
                self.assertIn("1920x1080:YUV_420_888@rear", result["preservedResults"])
                self.assertNotIn(_identity(throwing), result["preservedResults"])
                self.assertEqual(result["rejectedClaims"], [prop, "4000x3000:RAW_SENSOR@rear"])
                self.assertIn(prop, result["rejectedClaims"])
                self.assertNotIn("1920x1080:YUV_420_888@rear", result["rejectedClaims"])
                self.assertTrue(result["reasons"])

    def test_throw_does_not_drop_other_advertised_sizes(self):
        streams = [
            stream(queryError="timing arrays threw"),
            stream(format="JPEG", width=8000, height=6000, queryError=None),
            stream(logicalId="front", format="YUV_420_888", width=1920, height=1080, queryError=None),
        ]
        result = evaluate({"streams": streams, "failedProperty": "timing"})
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(
            result["preservedResults"],
            ["8000x6000:JPEG@rear", "1920x1080:YUV_420_888@front"],
        )
        self.assertNotEqual(result["preservedResults"], [])
        self.assertEqual(
            result["rejectedClaims"],
            ["timing", "4000x3000:RAW_SENSOR@rear"],
        )

    def test_middle_error_preserves_both_neighbors(self):
        streams = [
            stream(logicalId="wide", format="RAW_SENSOR", width=4000, height=3000),
            stream(logicalId="rear", format="JPEG", width=8000, height=6000, queryError="timing arrays threw"),
            stream(logicalId="front", format="YUV_420_888", width=1920, height=1080),
        ]
        result = evaluate({"streams": streams, "failedProperty": "dynamic_range"})
        self.assertEqual(
            result["preservedResults"],
            ["4000x3000:RAW_SENSOR@wide", "1920x1080:YUV_420_888@front"],
        )
        self.assertEqual(
            result["rejectedClaims"],
            ["dynamic_range", "8000x6000:JPEG@rear"],
        )
        self.assertNotEqual(result["preservedResults"], [])

    def test_all_streams_throwing_names_each_identity(self):
        raw = stream(queryError="route metadata query threw")
        jpeg = stream(format="JPEG", width=8000, height=6000, queryError="route metadata query threw")
        result = evaluate({"streams": [raw, jpeg], "failedProperty": "route_metadata"})
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], [])
        self.assertEqual(
            result["rejectedClaims"],
            ["route_metadata", "4000x3000:RAW_SENSOR@rear", "8000x6000:JPEG@rear"],
        )
        self.assertTrue(result["reasons"])

    def test_one_healthy_stream_is_never_dropped(self):
        result = evaluate(
            {
                "streams": [
                    stream(logicalId="front", queryError="optional codec query threw"),
                    stream(format="YUV_420_888", width=1920, height=1080),
                    stream(logicalId="wide", queryError="optional codec query threw"),
                ],
                "failedProperty": "codec",
            }
        )
        self.assertEqual(result["preservedResults"], ["1920x1080:YUV_420_888@rear"])
        self.assertNotEqual(result["preservedResults"], [])
        self.assertEqual(result["decision"], "partial")

    def test_unadvertised_readable_size_is_still_retained(self):
        quiet = stream(advertised=False, format="PRIVATE", width=1920, height=1080)
        result = evaluate({"streams": [quiet], "failedProperty": "codec"})
        self.assertEqual(result["preservedResults"], ["1920x1080:PRIVATE@rear"])
        self.assertEqual(result["rejectedClaims"], ["codec"])

    def test_duplicate_error_identity_listed_once(self):
        bad = stream(queryError="timing arrays threw")
        result = evaluate({"streams": [bad, dict(bad)], "failedProperty": "timing"})
        self.assertEqual(result["rejectedClaims"], ["timing", "4000x3000:RAW_SENSOR@rear"])
        self.assertEqual(result["preservedResults"], [])

    def test_duplicate_healthy_sizes_are_both_retained(self):
        item = stream(format="YUV_420_888", width=1920, height=1080)
        result = evaluate({"streams": [item, dict(item)], "failedProperty": "route_metadata"})
        self.assertEqual(
            result["preservedResults"],
            ["1920x1080:YUV_420_888@rear", "1920x1080:YUV_420_888@rear"],
        )

    def test_empty_stream_list_reports_the_failed_property(self):
        result = evaluate({"streams": [], "failedProperty": "codec"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], [])
        self.assertEqual(result["rejectedClaims"], ["codec"])

    def test_one_throw_keeps_4k_and_declared_8k_candidates(self):
        thrown = stream(queryError="timing arrays threw", width=1280, height=720, format="YUV_420_888")
        uhd = stream(format="YUV_420_888", width=3840, height=2160, logicalId="rear")
        declared_8k = stream(format="YUV_420_888", width=7680, height=4320, logicalId="rear")
        for prop in _PROPERTIES:
            result = evaluate(
                {"streams": [thrown, uhd, declared_8k], "failedProperty": prop}
            )
            with self.subTest(prop=prop):
                self.assertContract(result)
                self.assertEqual(result["decision"], "partial")
                self.assertNotIn(result["decision"], {"qualified", "allowed"})
                self.assertEqual(
                    result["preservedResults"],
                    ["3840x2160:YUV_420_888@rear", "7680x4320:YUV_420_888@rear"],
                )
                self.assertNotEqual(result["preservedResults"], [])
                self.assertEqual(result["rejectedClaims"][0], prop)
                self.assertIn("1280x720:YUV_420_888@rear", result["rejectedClaims"])

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
            {"streams": [valid], "failedProperty": "route-metadata"},
            {"streams": [valid], "failedProperty": "CODEC"},
            {"streams": [valid], "failedProperty": None},
            {"streams": [valid], "failedProperty": ""},
            {"streams": valid, "failedProperty": "codec"},
            {"streams": [None], "failedProperty": "codec"},
            {"streams": ["rear"], "failedProperty": "timing"},
            {"streams": [{**valid, "lens": "invented"}], "failedProperty": "timing"},
            {"streams": [{k: v for k, v in valid.items() if k != "format"}], "failedProperty": "timing"},
            {"streams": [{**valid, "logicalId": ""}], "failedProperty": "timing"},
            {"streams": [{**valid, "logicalId": 0}], "failedProperty": "timing"},
            {"streams": [{**valid, "format": ""}], "failedProperty": "codec"},
            {"streams": [{**valid, "format": 32}], "failedProperty": "codec"},
            {"streams": [{**valid, "width": 0}], "failedProperty": "timing"},
            {"streams": [{**valid, "width": -1}], "failedProperty": "timing"},
            {"streams": [{**valid, "width": True}], "failedProperty": "timing"},
            {"streams": [{**valid, "width": 1920.0}], "failedProperty": "timing"},
            {"streams": [{**valid, "height": False}], "failedProperty": "timing"},
            {"streams": [{**valid, "height": 0}], "failedProperty": "dynamic_range"},
            {"streams": [{**valid, "advertised": 1}], "failedProperty": "codec"},
            {"streams": [{**valid, "configured": "false"}], "failedProperty": "codec"},
            {"streams": [{**valid, "samples": True}], "failedProperty": "route_metadata"},
            {"streams": [{**valid, "samples": -1}], "failedProperty": "route_metadata"},
            {"streams": [{**valid, "samples": 1.0}], "failedProperty": "route_metadata"},
            {"streams": [{**valid, "queryError": ""}], "failedProperty": "timing"},
            {"streams": [{**valid, "queryError": 1}], "failedProperty": "timing"},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
