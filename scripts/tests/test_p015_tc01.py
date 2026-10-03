"""TC-P015-01 partial characteristic failure does not empty the inventory."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p015_tc01", Path(__file__).resolve().parents[1] / "gates" / "p015_tc01.py"
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


def capability(identity, *, readable=True, kind="format", query_error=None):
    return {"id": identity, "kind": kind, "readable": readable, "queryError": query_error}


def payload(failed, **overrides):
    base = {
        "capabilities": [
            capability("fmt-yuv-1080"),
            capability("fmt-jpeg-4000", kind="format"),
            capability(
                "failed-query",
                readable=False,
                kind="query",
                query_error=failed + " query threw",
            ),
        ],
        "failedProperty": failed,
        "eraseAllCandidates": False,
    }
    base.update(overrides)
    return base


class TcP01501(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P015-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)

    def test_contract_text(self):
        self.assertIn("unrelated formats and routes remain readable", _MODULE.INTERVENTION)
        self.assertIn("empty device inventory", _MODULE.EXPECTED)
        self.assertIn("erases every candidate", _MODULE.NEGATIVE)
        self.assertIn("route metadata", _MODULE.REPEAT)

    def test_route_metadata_keeps_unrelated_formats(self):
        result = evaluate(payload("route_metadata"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], ["fmt-yuv-1080", "fmt-jpeg-4000"])
        self.assertIn("route_metadata", result["rejectedClaims"])
        self.assertIn("failed-query", result["rejectedClaims"])
        self.assertNotEqual(result["preservedResults"], [])
        self.assertTrue(any("route_metadata" in item for item in result["reasons"]))

    def test_timing_arrays_do_not_drop_routes(self):
        result = evaluate(payload("timing_arrays"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], ["fmt-yuv-1080", "fmt-jpeg-4000"])
        self.assertEqual(result["openQuestions"], ["timing_arrays"])

    def test_dynamic_range_and_codec_queries_stay_partial(self):
        for failed in ("dynamic_range_profiles", "optional_codec"):
            result = evaluate(payload(failed))
            self.assertEqual(result["decision"], "partial")
            self.assertNotIn(result["decision"], {"qualified", "allowed"})
            self.assertIn("fmt-yuv-1080", result["preservedResults"])
            self.assertIn(failed, result["rejectedClaims"])
            self.assertIn(failed, result["reasons"][0])

    def test_erase_all_negative_fails_and_keeps_inventory(self):
        result = evaluate(payload("optional_codec", eraseAllCandidates=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], ["fmt-yuv-1080", "fmt-jpeg-4000"])
        self.assertIn("erase-all-candidates", result["rejectedClaims"])
        self.assertTrue(any("must not erase every candidate" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload("route_metadata")
        empty_readable = {
            "capabilities": [
                capability("only", readable=False, query_error="threw"),
            ],
            "failedProperty": "timing_arrays",
            "eraseAllCandidates": False,
        }
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "failedProperty"},
            {**valid, "extra": True},
            {**valid, "failedProperty": "focus"},
            {**valid, "eraseAllCandidates": "yes"},
            {**valid, "capabilities": []},
            empty_readable,
            {
                **valid,
                "capabilities": [capability("ok", readable=True, query_error="nope")],
            },
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
