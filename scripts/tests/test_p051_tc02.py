"""TC-P051-02 crop parity stays on the absolute mosaic origin."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p051_tc02", Path(__file__).resolve().parents[1] / "gates" / "p051_tc02.py"
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
        "cfa": "RGGB",
        "width": 4,
        "height": 4,
        "rowStride": 4,
        "cropLeft": 0,
        "cropTop": 0,
        "cropWidth": 2,
        "cropHeight": 2,
        "red": 10,
        "green": 20,
        "blue": 30,
        "paddingValue": 0,
        "rotation": 0,
        "resetParity": False,
    }
    base.update(overrides)
    return base


class TcP05102(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P051-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants(self):
        self.assertIn("odd and even crop", _MODULE.INTERVENTION)
        self.assertIn("channel identity", _MODULE.EXPECTED)
        self.assertIn("Resetting mosaic parity", _MODULE.NEGATIVE)

    def test_every_cfa_keeps_absolute_phase_for_odd_and_even_origins(self):
        expected = {
            ("RGGB", 0, 0): "R",
            ("RGGB", 1, 1): "B",
            ("GRBG", 0, 0): "G",
            ("GRBG", 1, 1): "G",
            ("GBRG", 1, 0): "B",
            ("GBRG", 0, 1): "R",
            ("BGGR", 1, 1): "R",
            ("BGGR", 0, 0): "B",
        }
        for (cfa, left, top), channel in expected.items():
            result = evaluate(payload(cfa=cfa, cropLeft=left, cropTop=top))
            self.assertContract(result)
            self.assertEqual(result["decision"], "identity_held")
            self.assertIn(f"absolute:{channel}", result["preservedResults"])
            self.assertIn(f"cfa:{cfa}", result["preservedResults"])
            self.assertIn("distinct:10,20,30", result["preservedResults"])
            self.assertEqual(result["rejectedClaims"], [])

    def test_repeat_border_pixel(self):
        result = evaluate(payload(cropLeft=0, cropTop=0, cropWidth=4, cropHeight=1))
        self.assertEqual(result["decision"], "identity_held")
        self.assertIn("absolute:R", result["preservedResults"])
        self.assertIn("crop:4x1+0+0", result["preservedResults"])
        self.assertIn("developed:0,0:10,20,30", result["preservedResults"])

    def test_repeat_padded_rows(self):
        result = evaluate(payload(rowStride=6, paddingValue=999))
        self.assertContract(result)
        self.assertEqual(result["decision"], "identity_held")
        self.assertIn("stride:6", result["preservedResults"])
        self.assertIn("padding:999:ignored", result["preservedResults"])
        self.assertIn("developed:0,0:10,20,30", result["preservedResults"])
        self.assertNotIn("developed:0,0:999,20,30", result["preservedResults"])

    def test_repeat_rotated_developed_output(self):
        turned = evaluate(payload(rotation=90, cropWidth=2, cropHeight=2))
        self.assertEqual(turned["decision"], "identity_held")
        self.assertIn("developed:1,0:10,20,30", turned["preservedResults"])
        half = evaluate(payload(rotation=180, cropWidth=2, cropHeight=2))
        self.assertIn("developed:1,1:10,20,30", half["preservedResults"])
        self.assertNotIn(turned["decision"], {"qualified", "allowed"})

    def test_resetting_parity_fails_even_when_labels_coincide(self):
        odd = evaluate(payload(cropLeft=1, cropTop=1, resetParity=True))
        self.assertContract(odd)
        self.assertEqual(odd["decision"], "rejected")
        self.assertEqual(odd["rejectedClaims"], ["reset-mosaic-parity"])
        self.assertIn(_MODULE.NEGATIVE, odd["reasons"])
        self.assertIn("absolute:B", odd["preservedResults"])
        self.assertIn("reset:R", odd["preservedResults"])
        self.assertIn("distinct:10,20,30", odd["preservedResults"])
        even = evaluate(payload(cropLeft=2, cropTop=2, resetParity=True))
        self.assertEqual(even["decision"], "rejected")
        self.assertNotIn(even["decision"], {"qualified", "allowed", "identity_held"})
        self.assertIn("absolute:R", even["preservedResults"])
        self.assertIn("reset:R", even["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "cfa": "RGBG"},
            {**valid, "red": 10, "green": 10, "blue": 30},
            {**valid, "rotation": 45},
            {**valid, "resetParity": 1},
            {**valid, "cropLeft": 3, "cropWidth": 2},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
