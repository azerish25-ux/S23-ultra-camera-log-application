"""TC-P016-03 incompatible output combination."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p016_tc03", Path(__file__).resolve().parents[1] / "gates" / "p016_tc03.py"
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


def output(id_, format_, width, height, supported=True):
    return {
        "id": id_,
        "format": format_,
        "width": width,
        "height": height,
        "supportedAlone": supported,
    }


def _sizes(items):
    return [f"{item['width']}x{item['height']}:{item['format']}" for item in items]


class TcP01603(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P016-03")
        self.assertIn(result["decision"], {"rejected", "compatible"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["openQuestions"], ["not-endurance-certified"])
        for token in _ORACLE:
            self.assertIn(token, result["preservedResults"])

    def test_contract_text_is_encoded(self):
        self.assertIn("simultaneous combination", _MODULE.INTERVENTION)
        self.assertIn("coexistence", _MODULE.EXPECTED)
        self.assertIn("simultaneously must fail", _MODULE.NEGATIVE)

    def _pair(self):
        return [
            output("preview-a", "YUV_420_888", 1920, 1080),
            output("preview-b", "YUV_420_888", 1280, 720),
            output("raw", "RAW_SENSOR", 4000, 3000),
            output("encoder", "HEVC", 1920, 1080),
        ]

    def test_mixed_preview_violation_rejects_combination(self):
        items = [
            output("preview-1080", "YUV_420_888", 1920, 1080),
            output("preview-720", "YUV_420_888", 1280, 720),
        ]
        result = evaluate({"outputs": items, "constraintsViolated": True, "variant": "mixed_preview"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["preview-1080", "preview-720"])
        self.assertEqual(result["preservedResults"], [*_sizes(items), *_ORACLE])
        self.assertIn("independent support is not coexistence", result["reasons"])
        self.assertTrue(any("mixed_preview" in reason for reason in result["reasons"]))

    def test_raw_plus_encoder_violation_rejects_combination(self):
        items = [
            output("raw", "RAW_SENSOR", 4000, 3000),
            output("encoder", "HEVC", 1920, 1080),
        ]
        result = evaluate(
            {"outputs": items, "constraintsViolated": True, "variant": "raw_plus_encoder"}
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["raw", "encoder"])
        self.assertIn("4000x3000:RAW_SENSOR", result["preservedResults"])
        self.assertIn("1920x1080:HEVC", result["preservedResults"])

    def test_alternate_lens_violation_rejects_combination(self):
        items = [
            output("wide", "YUV_420_888", 1920, 1080),
            output("tele", "YUV_420_888", 1920, 1080),
        ]
        result = evaluate(
            {"outputs": items, "constraintsViolated": True, "variant": "alternate_lens"}
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["wide", "tele"])
        self.assertEqual(result["preservedResults"], [*_sizes(items), *_ORACLE])

    def test_every_individually_supported_stream_fails_when_constraints_are_violated(self):
        items = self._pair()
        result = evaluate(
            {"outputs": items, "constraintsViolated": True, "variant": "raw_plus_encoder"}
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "compatible"})
        self.assertEqual(result["rejectedClaims"], [item["id"] for item in items])
        for size in _sizes(items):
            self.assertIn(size, result["preservedResults"])
        self.assertGreater(len(result["preservedResults"]), len(items))

    def test_inside_constraints_is_compatible_not_qualified(self):
        items = [
            output("preview", "YUV_420_888", 1920, 1080),
            output("encoder", "HEVC", 1920, 1080),
        ]
        result = evaluate(
            {"outputs": items, "constraintsViolated": False, "variant": "mixed_preview"}
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "compatible")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], [*_sizes(items), *_ORACLE])
        self.assertFalse(any("proves coexistence" in reason for reason in result["reasons"]))

    def test_one_unsupported_output_rejects_only_that_id(self):
        items = [
            output("preview", "YUV_420_888", 1920, 1080, True),
            output("raw", "RAW_SENSOR", 4000, 3000, False),
        ]
        result = evaluate(
            {"outputs": items, "constraintsViolated": False, "variant": "alternate_lens"}
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["raw"])
        self.assertIn("1920x1080:YUV_420_888", result["preservedResults"])
        self.assertIn("4000x3000:RAW_SENSOR", result["preservedResults"])

    def test_invalid_payload_raises(self):
        item = output("preview", "YUV_420_888", 1920, 1080)
        cases = [
            None,
            {},
            {"outputs": [], "constraintsViolated": True, "variant": "mixed_preview"},
            {"outputs": [item], "constraintsViolated": True, "variant": "other"},
            {"outputs": [item, item], "constraintsViolated": False, "variant": "mixed_preview"},
            {"outputs": [item], "constraintsViolated": "true", "variant": "mixed_preview"},
            {"outputs": [{**item, "width": True}], "constraintsViolated": False, "variant": "mixed_preview"},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
