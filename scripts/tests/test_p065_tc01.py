"""TC-P065-01 unsupported precision format."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p065_tc01", Path(__file__).resolve().parents[1] / "gates" / "p065_tc01.py"
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
        "routeId": "render-rgba16f",
        "apiAvailable": True,
        "requiredFormat": "rgba16f",
        "formatPresent": False,
        "silentRgba8": False,
        "alternative": "none",
        "repeat": "baseline",
    }
    base.update(overrides)
    return base


class TcP06501(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P065-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("graphics API otherwise available", _MODULE.INTERVENTION)
        self.assertIn("RGBA8", _MODULE.NEGATIVE)
        self.assertIn("missing extensions", _MODULE.REPEAT)

    def test_missing_format_reports_the_route(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "route_unavailable")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("render-rgba16f", result["preservedResults"])
        self.assertIn("format:rgba16f", result["preservedResults"])
        self.assertTrue(any("render-rgba16f" in item and "rgba16f" in item for item in result["reasons"]))

    def test_silent_rgba8_is_rejected_and_keeps_the_format(self):
        result = evaluate(payload(silentRgba8=True, alternative="cpu-reference"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["silent-rgba8"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("format:rgba16f", result["preservedResults"])
        self.assertIn("alternative:cpu-reference", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "alternative_selected", "route_unavailable"})

    def test_separately_recorded_alternative_is_not_qualified(self):
        result = evaluate(payload(alternative="cpu-reference", repeat="missing-extension"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "alternative_selected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("format:rgba16f", result["preservedResults"])
        self.assertIn("repeat:missing-extension", result["preservedResults"])
        self.assertIn("alternative:cpu-reference", result["preservedResults"])

    def test_repeat_incompatible_surface(self):
        result = evaluate(payload(repeat="incompatible-surface", requiredFormat="rgba32f"))
        self.assertEqual(result["decision"], "route_unavailable")
        self.assertIn("format:rgba32f", result["preservedResults"])
        self.assertIn("repeat:incompatible-surface", result["preservedResults"])

    def test_repeat_unavailable_import(self):
        result = evaluate(payload(repeat="unavailable-import", requiredFormat="yuv420"))
        self.assertEqual(result["decision"], "route_unavailable")
        self.assertIn("format:yuv420", result["preservedResults"])
        self.assertIn("repeat:unavailable-import", result["preservedResults"])

    def test_present_format_is_retained(self):
        result = evaluate(payload(formatPresent=True))
        self.assertEqual(result["decision"], "format_retained")
        self.assertIn("present:true", result["preservedResults"])
        self.assertIn("format:rgba16f", result["preservedResults"])

    def test_api_unavailable_is_withheld_without_substitution(self):
        result = evaluate(payload(apiAvailable=False, silentRgba8=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("api:false", result["preservedResults"])
        self.assertIn("render-rgba16f", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "routeId"},
            {**valid, "extra": True},
            {**valid, "silentRgba8": "true"},
            {**valid, "requiredFormat": "RGBA8"},
            {**valid, "alternative": "qualified"},
            {**valid, "repeat": "corner"},
            {**valid, "apiAvailable": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
