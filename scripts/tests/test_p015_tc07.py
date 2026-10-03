"""TC-P015-07 Main10 does not imply P010 Image support."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p015_tc07", Path(__file__).resolve().parents[1] / "gates" / "p015_tc07.py"
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
_NAMES = ("surface", "byte_buffer", "image", "encoder", "decoder")


def interfaces(usable):
    rows = []
    for name in _NAMES:
        flag = name in usable
        rows.append({"name": name, "usable": flag, "tenBit": flag})
    return rows


def payload(usable, **overrides):
    base = {
        "interfaces": interfaces(usable),
        "main10Advertised": True,
        "precisionDowngrade": False,
    }
    base.update(overrides)
    return base


class TcP01507(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P015-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["preservedResults"], list(_NAMES))

    def test_contract_text(self):
        self.assertIn("ten-bit input interface", _MODULE.INTERVENTION)
        self.assertIn("hidden precision downgrade", _MODULE.EXPECTED)
        self.assertIn("P010 Image", _MODULE.NEGATIVE)
        self.assertIn("byte-buffer", _MODULE.REPEAT)

    def test_surface_ten_bit_does_not_imply_image(self):
        result = evaluate(payload({"surface"}))
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertIn("surface", result["preservedResults"])
        self.assertIn("image", result["preservedResults"])
        self.assertIn("image", result["rejectedClaims"])
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertIn("arbitrary-surface-conversion", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_byte_buffer_and_encoder_paths_stay_independent(self):
        for name in ("byte_buffer", "encoder"):
            result = evaluate(payload({name}))
            self.assertEqual(result["decision"], "partial")
            self.assertIn(name, result["preservedResults"])
            self.assertIn("image", result["rejectedClaims"])
            self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_decoder_path_is_retained_when_it_is_the_usable_alternative(self):
        result = evaluate(payload({"decoder"}))
        self.assertEqual(result["decision"], "partial")
        self.assertIn("decoder", result["preservedResults"])
        self.assertIn("surface", result["rejectedClaims"])
        self.assertIn("arbitrary-surface-conversion", result["rejectedClaims"])

    def test_precision_downgrade_keeps_the_ten_bit_surface(self):
        result = evaluate(payload({"surface", "encoder"}, precisionDowngrade=True))
        self.assertEqual(result["decision"], "partial")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("hidden-precision-downgrade", result["rejectedClaims"])
        self.assertIn("surface", result["preservedResults"])
        self.assertIn("encoder", result["preservedResults"])

    def test_all_interfaces_usable_is_not_ten_bit_certification(self):
        result = evaluate(payload(set(_NAMES), main10Advertised=False))
        self.assertEqual(result["decision"], "interface_specific")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], list(_NAMES))
        self.assertTrue(any("not ten-bit fidelity certification" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload({"surface"})
        missing = {
            **valid,
            "interfaces": [row for row in valid["interfaces"] if row["name"] != "decoder"],
        }
        cases = [
            None,
            {},
            missing,
            {**valid, "main10Advertised": "yes"},
            {**valid, "precisionDowngrade": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
