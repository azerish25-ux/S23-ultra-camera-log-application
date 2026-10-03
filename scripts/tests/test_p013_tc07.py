"""TC-P013-07 Main10 does not imply P010 Image support."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p013_tc07", Path(__file__).resolve().parents[1] / "gates" / "p013_tc07.py"
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


def interface(name, usable, ten_bit):
    return {"name": name, "usable": usable, "tenBit": ten_bit}


def payload(interfaces, main10=True, sole=False, profile="Main10", codec="c2.android.hevc.encoder"):
    return {
        "codecName": codec,
        "profile": profile,
        "interfaces": interfaces,
        "main10Advertised": main10,
        "soleMain10Criterion": sole,
    }


class TcP01307(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P013-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"partial", "interface_specific", "unavailable", "rejected"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        self.assertTrue(result["preservedResults"])
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_surface_usable_image_unavailable_is_partial(self):
        result = evaluate(
            payload(
                [
                    interface("surface", True, True),
                    interface("image", False, True),
                ]
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], ["surface"])
        self.assertIn("image", result["rejectedClaims"])
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertIn("arbitrary-surface-conversion", result["rejectedClaims"])
        self.assertNotIn("image", result["preservedResults"])
        self.assertTrue(any("P010 Image is unavailable" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_byte_buffer_usable_while_surface_is_unavailable(self):
        result = evaluate(
            payload(
                [
                    interface("byte_buffer", True, True),
                    interface("surface", False, True),
                ],
                main10=False,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], ["byte_buffer"])
        self.assertIn("surface", result["rejectedClaims"])
        self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])

    def test_encoder_and_decoder_paths_stay_independent(self):
        result = evaluate(
            payload(
                [
                    interface("encoder", True, True),
                    interface("decoder", False, False),
                ],
                main10=False,
                profile="Main",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], ["encoder"])
        self.assertIn("decoder", result["rejectedClaims"])
        self.assertNotIn("decoder", result["preservedResults"])

    def test_image_path_alone_is_interface_specific_not_qualified(self):
        result = evaluate(payload([interface("image", True, True)], main10=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "interface_specific")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], ["image"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_sole_main10_criterion_does_not_accept_p010_image(self):
        result = evaluate(
            payload(
                [
                    interface("surface", True, True),
                    interface("image", False, True),
                    interface("byte_buffer", False, True),
                ],
                sole=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("main10-as-sole-p010-criterion", result["rejectedClaims"])
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertIn("arbitrary-surface-conversion", result["rejectedClaims"])
        self.assertIn("surface", result["preservedResults"])
        self.assertNotIn("image", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interface_specific", "partial"})

    def test_eight_bit_surface_is_not_silently_upgraded(self):
        result = evaluate(
            payload(
                [
                    interface("surface", True, False),
                    interface("image", False, False),
                ]
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], ["surface"])
        self.assertNotIn("ten-bit:surface", result["preservedResults"])
        self.assertTrue(any("no hidden precision downgrade" in item for item in result["reasons"]))

    def test_no_usable_interface_keeps_codec_identity(self):
        result = evaluate(
            payload([interface(name, False, False) for name in _NAMES], main10=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "unavailable")
        self.assertEqual(result["preservedResults"], ["codec:c2.android.hevc.encoder:Main10"])
        self.assertIn("image", result["rejectedClaims"])
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload([interface("surface", True, True)])
        cases = [
            None,
            {},
            {**valid, "interfaces": []},
            {**valid, "soleMain10Criterion": "yes"},
            {**valid, "interfaces": [interface("hdmi", True, True)]},
            {**valid, "interfaces": [interface("surface", True, True), interface("surface", False, False)]},
            {k: v for k, v in valid.items() if k != "profile"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
