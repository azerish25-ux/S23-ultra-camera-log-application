"""TC-P013-01 one throwing characteristic query does not empty the inventory."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p013_tc01", Path(__file__).resolve().parents[1] / "gates" / "p013_tc01.py"
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
_PROPERTIES = (
    "route_metadata",
    "timing_arrays",
    "dynamic_range_profiles",
    "optional_codec",
)


def candidate(**overrides):
    base = {
        "candidateId": "hevc-main10-surface",
        "codecName": "c2.android.hevc.encoder",
        "interface": "surface",
        "format": "COLOR_FormatSurface",
        "queryError": None,
    }
    base.update(overrides)
    return base


def _identity(item):
    return f"{item['candidateId']}:{item['interface']}:{item['format']}"


class TcP01301(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P013-01")
        self.assertIn(result["decision"], {"partial", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))
        self.assertTrue(result["preservedResults"])

    def test_route_metadata_throw_keeps_surface_and_image(self):
        throwing = candidate(queryError="route metadata query threw")
        healthy = candidate(
            candidateId="hevc-main10-p010-image",
            interface="image",
            format="P010",
        )
        result = evaluate(
            {"candidates": [throwing, healthy], "failedProperty": "route_metadata", "eraseAll": False}
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], [_identity(healthy), "unreadable:" + _identity(throwing)])
        self.assertIn("route_metadata", result["rejectedClaims"])
        self.assertNotIn(_identity(healthy), result["rejectedClaims"])
        self.assertTrue(any("route_metadata" in item for item in result["reasons"]))

    def test_timing_arrays_throw_keeps_readable_byte_buffer(self):
        throwing = candidate(queryError="timing arrays threw", interface="encoder", format="HEVC")
        healthy = candidate(
            candidateId="hevc-byte-buffer",
            interface="byte_buffer",
            format="P010",
        )
        result = evaluate(
            {"candidates": [throwing, healthy], "failedProperty": "timing_arrays", "eraseAll": False}
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertIn(_identity(healthy), result["preservedResults"])
        self.assertNotEqual(result["preservedResults"], [])
        self.assertEqual(result["rejectedClaims"][0], "timing_arrays")

    def test_dynamic_range_profile_query_does_not_empty_inventory(self):
        streams = [
            candidate(queryError="dynamic-range profile query threw"),
            candidate(candidateId="jpeg-route", interface="image", format="JPEG", queryError=None),
            candidate(candidateId="front-yuv", interface="surface", format="YUV_420_888", queryError=None),
        ]
        result = evaluate(
            {
                "candidates": streams,
                "failedProperty": "dynamic_range_profiles",
                "eraseAll": False,
            }
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(
            result["preservedResults"][:2],
            [_identity(streams[1]), _identity(streams[2])],
        )
        self.assertIn("dynamic_range_profiles", result["rejectedClaims"])

    def test_optional_codec_query_retains_unrelated_format(self):
        healthy = candidate(candidateId="decoder", interface="decoder", format="HEVC")
        result = evaluate(
            {
                "candidates": [
                    candidate(queryError="optional codec query threw"),
                    healthy,
                ],
                "failedProperty": "optional_codec",
                "eraseAll": False,
            }
        )
        self.assertContract(result)
        self.assertIn(_identity(healthy), result["preservedResults"])
        self.assertEqual(result["decision"], "partial")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_erase_all_negative_is_rejected_and_inventory_remains(self):
        healthy = candidate(candidateId="hevc-main10-surface", interface="surface", format="COLOR_FormatSurface")
        other = candidate(candidateId="hevc-main10-p010-image", interface="image", format="P010")
        result = evaluate(
            {
                "candidates": [healthy, other],
                "failedProperty": "optional_codec",
                "eraseAll": True,
            }
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "partial"})
        self.assertIn("erased-inventory", result["rejectedClaims"])
        self.assertIn(_identity(healthy), result["preservedResults"])
        self.assertIn(_identity(other), result["preservedResults"])
        self.assertTrue(any("erases every candidate" in item for item in result["reasons"]))

    def test_each_failed_property_is_reported(self):
        for prop in _PROPERTIES:
            result = evaluate(
                {
                    "candidates": [candidate(queryError=prop + " threw"), candidate(candidateId="kept")],
                    "failedProperty": prop,
                    "eraseAll": False,
                }
            )
            with self.subTest(prop=prop):
                self.assertEqual(result["decision"], "partial")
                self.assertEqual(result["rejectedClaims"][0], prop)
                self.assertTrue(result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = {
            "candidates": [candidate()],
            "failedProperty": "route_metadata",
            "eraseAll": False,
        }
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "eraseAll"},
            {**valid, "extra": True},
            {**valid, "failedProperty": "focal"},
            {**valid, "eraseAll": "true"},
            {**valid, "candidates": []},
            {**valid, "candidates": [candidate(interface="hdmi")]},
            {**valid, "candidates": [candidate(queryError="")]},
            {**valid, "candidates": [candidate(), candidate()]},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
