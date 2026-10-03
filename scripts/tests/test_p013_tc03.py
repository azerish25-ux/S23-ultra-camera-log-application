"""TC-P013-03 individually supported outputs are not coexistence."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p013_tc03", Path(__file__).resolve().parents[1] / "gates" / "p013_tc03.py"
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


def output(id_, format_, width, height, supported=True):
    return {
        "id": id_,
        "format": format_,
        "width": width,
        "height": height,
        "supportedAlone": supported,
    }


def payload(outputs, violated, variant):
    return {"outputs": outputs, "constraintsViolated": violated, "variant": variant}


class TcP01303(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P013-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"rejected", "compatible"})
        self.assertTrue(result["reasons"])
        self.assertTrue(result["preservedResults"])

    def _pair(self):
        return [
            output("preview", "YUV_420_888", 1920, 1080),
            output("record", "HEVC", 3840, 2160),
        ]

    def test_mixed_preview_selection_of_every_stream_fails(self):
        outputs = self._pair()
        result = evaluate(payload(outputs, True, "mixed_preview"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["preview", "record"])
        self.assertEqual(
            result["preservedResults"],
            ["1920x1080:YUV_420_888", "3840x2160:HEVC"],
        )
        self.assertTrue(any("not coexistence" in item for item in result["reasons"]))
        self.assertTrue(any("simultaneously must fail" in item for item in result["reasons"]))

    def test_raw_plus_encoder_violation_preserves_both_sizes(self):
        outputs = [
            output("raw", "RAW_SENSOR", 4000, 3000),
            output("encoder", "HEVC", 1920, 1080),
        ]
        result = evaluate(payload(outputs, True, "raw_plus_encoder"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["preservedResults"], ["4000x3000:RAW_SENSOR", "1920x1080:HEVC"])
        self.assertEqual(result["rejectedClaims"], ["raw", "encoder"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "compatible"})

    def test_alternate_lens_routes_do_not_prove_coexistence(self):
        outputs = [
            output("rear", "YUV_420_888", 1920, 1080),
            output("tele", "YUV_420_888", 1920, 1080),
        ]
        result = evaluate(payload(outputs, True, "alternate_lens"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("1920x1080:YUV_420_888", result["preservedResults"])
        self.assertEqual(len(result["preservedResults"]), 2)

    def test_constraints_intact_are_compatible_not_qualified(self):
        result = evaluate(payload(self._pair(), False, "mixed_preview"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "compatible")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("3840x2160:HEVC", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_individually_unsupported_output_is_rejected_and_inventory_kept(self):
        outputs = [
            output("preview", "YUV_420_888", 1280, 720, True),
            output("raw", "RAW_SENSOR", 4000, 3000, False),
        ]
        result = evaluate(payload(outputs, False, "raw_plus_encoder"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["raw"])
        self.assertEqual(result["preservedResults"], ["1280x720:YUV_420_888", "4000x3000:RAW_SENSOR"])

    def test_invalid_payload_raises(self):
        valid = payload(self._pair(), False, "mixed_preview")
        cases = [
            None,
            {},
            {**valid, "variant": "tele"},
            {**valid, "constraintsViolated": "true"},
            {**valid, "outputs": []},
            payload([output("a", "YUV_420_888", 0, 10)], False, "mixed_preview"),
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
