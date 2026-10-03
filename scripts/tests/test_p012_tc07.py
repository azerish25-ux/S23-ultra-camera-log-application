"""TC-P012-07 codec interface asymmetry."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p012_tc07", Path(__file__).resolve().parents[1] / "gates" / "p012_tc07.py"
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


def payload(interfaces, main10=False, size="1920x1080"):
    return {
        "interfaces": interfaces,
        "main10Advertised": main10,
        "advertisedSize": size,
    }


def all_five(**overrides):
    """Build the five codec interfaces. overrides map name to (usable, tenBit)."""
    rows = []
    for name in _NAMES:
        usable, ten_bit = overrides.get(name, (True, True))
        rows.append(interface(name, usable, ten_bit))
    return rows


class TcP01207(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P012-07")
        self.assertIn(result["decision"], {"partial", "qualified", "unavailable"})
        self.assertNotIn(result["decision"], {"unlimited", "allowed"})
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))
        self.assertEqual(result["openQuestions"], [])

    def test_all_five_usable_is_qualified_and_keeps_advertised_size(self):
        size = "4080x3072"
        result = evaluate(payload(all_five(), main10=True, size=size))
        self.assertContract(result)
        self.assertEqual(result["decision"], "qualified")
        self.assertEqual(result["preservedResults"], [*_NAMES, size])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])

    def test_each_interface_name_qualified_alone(self):
        for name in _NAMES:
            result = evaluate(
                payload([interface(name, True, True)], main10=False, size="1280x720")
            )
            self.assertContract(result)
            self.assertEqual(result["decision"], "qualified")
            self.assertEqual(result["preservedResults"], [name, "1280x720"])
            self.assertEqual(result["rejectedClaims"], [])
            self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])

    def test_each_interface_name_is_independently_unusable(self):
        for name in _NAMES:
            overrides = {name: (False, False)}
            rows = all_five(**overrides)
            main10 = name == "image"
            result = evaluate(payload(rows, main10=main10, size="1920x1080"))
            self.assertContract(result)
            self.assertEqual(result["decision"], "partial")
            self.assertNotEqual(result["decision"], "qualified")
            usable = [item for item in _NAMES if item != name]
            self.assertEqual(result["preservedResults"], [*usable, "1920x1080"])
            if name == "image":
                self.assertEqual(
                    result["rejectedClaims"],
                    ["image", "main10-implies-p010-image"],
                )
                self.assertTrue(
                    any("Main10 advertising does not imply P010 Image support" in item
                        for item in result["reasons"])
                )
            else:
                self.assertEqual(result["rejectedClaims"], [name])
                self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])
            self.assertIn("1920x1080", result["preservedResults"])
            self.assertNotIn(name, result["preservedResults"])

    def test_mixed_usability_is_partial_across_all_five_names(self):
        rows = [
            interface("surface", True, True),
            interface("byte_buffer", False, True),
            interface("image", False, False),
            interface("encoder", True, False),
            interface("decoder", False, True),
        ]
        result = evaluate(payload(rows, main10=False, size="4000x3000"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], ["surface", "encoder", "4000x3000"])
        self.assertEqual(result["rejectedClaims"], ["byte_buffer", "image", "decoder"])
        self.assertTrue(any("independently" in item for item in result["reasons"]))
        self.assertTrue(any("encoder" in item for item in result["reasons"]))

    def test_none_usable_is_unavailable_and_preserves_only_advertised_size(self):
        rows = [interface(name, False, False) for name in _NAMES]
        result = evaluate(payload(rows, main10=True, size="4080x3072"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "unavailable")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(result["preservedResults"], ["4080x3072"])
        self.assertEqual(
            result["rejectedClaims"],
            [*_NAMES, "main10-implies-p010-image"],
        )

    def test_main10_with_unusable_image_is_not_qualified(self):
        rows = all_five(**{"image": (False, True)})
        result = evaluate(payload(rows, main10=True, size="1920x1080"))
        self.assertContract(result)
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(result["decision"], "partial")
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertIn("image", result["rejectedClaims"])
        self.assertNotIn("image", result["preservedResults"])
        self.assertIn("1920x1080", result["preservedResults"])

    def test_main10_false_with_unusable_image_does_not_add_false_claim(self):
        rows = all_five(**{"image": (False, False)})
        result = evaluate(payload(rows, main10=False, size="1920x1080"))
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["rejectedClaims"], ["image"])
        self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])

    def test_main10_with_usable_image_does_not_reject_implication(self):
        rows = all_five(**{"decoder": (False, True)})
        result = evaluate(payload(rows, main10=True, size="2048x1080"))
        self.assertEqual(result["decision"], "partial")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(result["rejectedClaims"], ["decoder"])
        self.assertIn("image", result["preservedResults"])
        self.assertIn("2048x1080", result["preservedResults"])
        self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])

    def test_ten_bit_surface_preserved_when_image_unusable(self):
        rows = [
            interface("surface", True, True),
            interface("byte_buffer", False, False),
            interface("image", False, False),
            interface("encoder", False, True),
            interface("decoder", True, True),
        ]
        result = evaluate(payload(rows, main10=True, size="3840x2160"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(result["preservedResults"], ["surface", "decoder", "3840x2160"])
        self.assertEqual(
            result["rejectedClaims"],
            ["byte_buffer", "image", "encoder", "main10-implies-p010-image"],
        )
        self.assertIn("surface", result["preservedResults"])
        self.assertNotIn("image", result["preservedResults"])
        self.assertTrue(
            any("usable ten-bit surface is preserved" in item for item in result["reasons"])
        )

    def test_usable_surface_stays_preserved_without_ten_bit_upgrade(self):
        rows = all_five(**{"surface": (True, False), "image": (False, False)})
        result = evaluate(payload(rows, main10=True, size="1920x1080"))
        self.assertEqual(result["decision"], "partial")
        self.assertIn("surface", result["preservedResults"])
        self.assertNotIn("image", result["preservedResults"])
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertTrue(any("surface" in item and "ten-bit" in item for item in result["reasons"]))

    def test_input_order_is_preserved_for_every_interface_name(self):
        order = ("decoder", "encoder", "image", "byte_buffer", "surface")
        rows = [
            interface("decoder", True, True),
            interface("encoder", False, True),
            interface("image", True, True),
            interface("byte_buffer", False, False),
            interface("surface", True, True),
        ]
        self.assertEqual(tuple(item["name"] for item in rows), order)
        result = evaluate(payload(rows, main10=False, size="640x480"))
        self.assertEqual(
            result["preservedResults"],
            ["decoder", "image", "surface", "640x480"],
        )
        self.assertEqual(result["rejectedClaims"], ["encoder", "byte_buffer"])
        self.assertEqual(result["decision"], "partial")

    def test_image_only_unusable_under_main10_is_unavailable(self):
        result = evaluate(
            payload([interface("image", False, True)], main10=True, size="1920x1080")
        )
        self.assertEqual(result["decision"], "unavailable")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(
            result["rejectedClaims"],
            ["image", "main10-implies-p010-image"],
        )
        self.assertEqual(result["preservedResults"], ["1920x1080"])

    def test_invalid_payload_raises(self):
        valid_row = interface("surface", True, True)
        valid = payload([valid_row], main10=False, size="1920x1080")
        cases = [
            None,
            [],
            {},
            {"interfaces": [valid_row], "main10Advertised": False},
            {"interfaces": [valid_row], "advertisedSize": "1920x1080"},
            {"main10Advertised": False, "advertisedSize": "1920x1080"},
            {**valid, "extra": True},
            payload([], main10=False),
            payload(valid_row, main10=False),
            payload([None], main10=False),
            payload(["surface"], main10=False),
            payload([{**valid_row, "extra": 1}], main10=False),
            payload([{k: v for k, v in valid_row.items() if k != "tenBit"}], main10=False),
            payload([interface("Image", True, True)], main10=False),
            payload([interface("p010", True, True)], main10=False),
            payload([interface("", True, True)], main10=False),
            payload([interface("surface", 1, True)], main10=False),
            payload([interface("surface", "true", True)], main10=False),
            payload([interface("surface", True, 1)], main10=False),
            payload([interface("surface", True, None)], main10=False),
            payload(
                [interface("surface", True, True), interface("surface", False, False)],
                main10=False,
            ),
            payload([valid_row], main10=0, size="1920x1080"),
            payload([valid_row], main10="true", size="1920x1080"),
            payload([valid_row], main10=False, size=""),
            payload([valid_row], main10=False, size=None),
            payload([valid_row], main10=False, size=1920),
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
