"""TC-P016-07 codec interface asymmetry."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p016_tc07", Path(__file__).resolve().parents[1] / "gates" / "p016_tc07.py"
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
_SIZE = "1920x1080"
_PATHS = ("surface", "byte_buffer", "image", "encoder", "decoder")


def interface(name, usable, ten_bit):
    return {"name": name, "usable": usable, "tenBit": ten_bit}


def payload(interfaces, **overrides):
    base = {
        "interfaces": interfaces,
        "main10Advertised": False,
        "surfaceConversionClaimed": False,
        "advertisedSize": _SIZE,
    }
    base.update(overrides)
    return base


class TcP01607(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P016-07")
        self.assertIn(result["decision"], {"partial", "interfaces_usable", "unavailable"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["openQuestions"], ["not-endurance-certified"])
        self.assertIn(_SIZE, result["preservedResults"])
        for token in _ORACLE:
            self.assertIn(token, result["preservedResults"])

    def test_contract_text_is_encoded(self):
        self.assertIn("ten-bit", _MODULE.INTERVENTION)
        self.assertIn("independently", _MODULE.EXPECTED)
        self.assertIn("Main10", _MODULE.NEGATIVE)
        self.assertIn("surface conversion", _MODULE.NEGATIVE)

    def test_surface_ten_bit_kept_when_image_unavailable(self):
        result = evaluate(
            payload(
                [
                    interface("surface", True, True),
                    interface("image", False, False),
                ],
                main10Advertised=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interfaces_usable"})
        self.assertIn("surface", result["preservedResults"])
        self.assertNotIn("image", result["preservedResults"])
        self.assertIn("image", result["rejectedClaims"])
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertTrue(any("usable ten-bit surface is preserved" in reason for reason in result["reasons"]))

    def test_byte_buffer_path_is_independent(self):
        result = evaluate(
            payload(
                [
                    interface("byte_buffer", True, True),
                    interface("surface", False, False),
                ]
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertIn("byte_buffer", result["preservedResults"])
        self.assertIn("surface", result["rejectedClaims"])
        self.assertNotIn("byte_buffer", result["rejectedClaims"])

    def test_image_path_unavailable_under_main10(self):
        result = evaluate(
            payload([interface("image", False, True)], main10Advertised=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "unavailable")
        self.assertIn("image", result["rejectedClaims"])
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interfaces_usable"})
        self.assertEqual(result["preservedResults"], [_SIZE, *_ORACLE])

    def test_encoder_and_decoder_are_independent(self):
        for name in ("encoder", "decoder"):
            other = "decoder" if name == "encoder" else "encoder"
            result = evaluate(
                payload(
                    [
                        interface(name, True, True),
                        interface(other, False, False),
                    ]
                )
            )
            with self.subTest(name=name):
                self.assertContract(result)
                self.assertEqual(result["decision"], "partial")
                self.assertIn(name, result["preservedResults"])
                self.assertIn(other, result["rejectedClaims"])
                self.assertNotIn(name, result["rejectedClaims"])

    def test_each_path_can_be_the_only_usable_interface(self):
        for name in _PATHS:
            others = [interface(other, False, False) for other in _PATHS if other != name]
            result = evaluate(payload([interface(name, True, True), *others]))
            with self.subTest(name=name):
                self.assertEqual(result["decision"], "partial")
                self.assertIn(name, result["preservedResults"])
                self.assertIn(_SIZE, result["preservedResults"])
                for other in _PATHS:
                    if other != name:
                        self.assertIn(other, result["rejectedClaims"])

    def test_main10_does_not_imply_p010_image_or_surface_conversion(self):
        result = evaluate(
            payload(
                [
                    interface("surface", True, True),
                    interface("byte_buffer", True, False),
                    interface("image", False, False),
                    interface("encoder", True, True),
                    interface("decoder", False, False),
                ],
                main10Advertised=True,
                surfaceConversionClaimed=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interfaces_usable"})
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertIn("arbitrary-surface-conversion", result["rejectedClaims"])
        self.assertIn("surface", result["preservedResults"])
        self.assertIn("byte_buffer", result["preservedResults"])
        self.assertIn("encoder", result["preservedResults"])
        self.assertNotIn("image", result["preservedResults"])
        self.assertNotIn("decoder", result["preservedResults"])
        self.assertTrue(any("no hidden precision downgrade" in reason for reason in result["reasons"]))
        self.assertTrue(any("byte_buffer" in reason for reason in result["reasons"]))

    def test_all_usable_without_false_claims_is_interfaces_usable(self):
        result = evaluate(
            payload([interface(name, True, True) for name in _PATHS], main10Advertised=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "interfaces_usable")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        for name in _PATHS:
            self.assertIn(name, result["preservedResults"])

    def test_surface_conversion_demotes_an_otherwise_usable_codec(self):
        result = evaluate(
            payload(
                [interface(name, True, False) for name in _PATHS],
                surfaceConversionClaimed=True,
            )
        )
        self.assertEqual(result["decision"], "partial")
        self.assertIn("arbitrary-surface-conversion", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interfaces_usable"})
        self.assertIn(_SIZE, result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload([interface("surface", True, True)])
        cases = [
            None,
            {},
            {**valid, "interfaces": []},
            {**valid, "interfaces": [interface("surface", True, True), interface("surface", False, False)]},
            {**valid, "main10Advertised": "true"},
            {**valid, "surfaceConversionClaimed": 1},
            {**valid, "advertisedSize": ""},
            {k: v for k, v in valid.items() if k != "advertisedSize"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
