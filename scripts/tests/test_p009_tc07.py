"""TC-P009-07 codec interface asymmetry."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p009_tc07", Path(__file__).resolve().parents[1] / "gates" / "p009_tc07.py"
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


def interface(name, usable=True, ten_bit=False):
    return {"name": name, "usable": usable, "tenBit": ten_bit}


def payload(interfaces, main10=False):
    return {"interfaces": interfaces, "main10Advertised": main10}


class TcP00907(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P009-07")
        self.assertIn(result["decision"], {"partial", "qualified", "unavailable"})
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_each_interface_qualifies_alone(self):
        for name in _NAMES:
            result = evaluate(payload([interface(name, True, name in {"surface", "byte_buffer", "image"})]))
            self.assertContract(result)
            self.assertEqual(result["decision"], "qualified")
            self.assertEqual(result["preservedResults"], [name])
            self.assertEqual(result["rejectedClaims"], [])
            self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])

    def test_each_interface_unavailable_alone(self):
        for name in _NAMES:
            result = evaluate(
                payload([interface(name, False, True)], main10=name == "image")
            )
            self.assertContract(result)
            self.assertEqual(result["decision"], "unavailable")
            self.assertEqual(result["preservedResults"], [])
            if name == "image":
                self.assertEqual(
                    result["rejectedClaims"],
                    ["image", "main10-implies-p010-image"],
                )
                self.assertNotEqual(result["decision"], "qualified")
            else:
                self.assertEqual(result["rejectedClaims"], [name])
                self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])

    def test_one_unusable_path_does_not_erase_the_others(self):
        for bad in _NAMES:
            interfaces = [
                interface(name, name != bad, name in {"surface", "byte_buffer"})
                for name in _NAMES
            ]
            result = evaluate(payload(interfaces, main10=True))
            self.assertContract(result)
            self.assertEqual(result["decision"], "partial")
            self.assertEqual(
                result["preservedResults"],
                [name for name in _NAMES if name != bad],
            )
            rejected = [bad]
            if bad == "image":
                rejected.append("main10-implies-p010-image")
                self.assertNotEqual(result["decision"], "qualified")
                self.assertTrue(
                    any("p010 image" in item for item in result["reasons"])
                )
            self.assertEqual(result["rejectedClaims"], rejected)
            if bad != "surface":
                self.assertIn("surface", result["preservedResults"])
            if bad != "byte_buffer":
                self.assertIn("byte_buffer", result["preservedResults"])

    def test_main10_does_not_imply_p010_image_or_downgrade_tenbit_inputs(self):
        result = evaluate(
            payload(
                [
                    interface("surface", True, True),
                    interface("byte_buffer", True, True),
                    interface("image", False, False),
                    interface("encoder", True, False),
                    interface("decoder", False, True),
                ],
                main10=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(
            result["preservedResults"],
            ["surface", "byte_buffer", "encoder"],
        )
        self.assertEqual(
            result["rejectedClaims"],
            ["image", "decoder", "main10-implies-p010-image"],
        )
        self.assertNotIn("image", result["preservedResults"])
        self.assertTrue(any("without precision downgrade" in item for item in result["reasons"]))
        self.assertTrue(any("surface" in item and "byte_buffer" in item for item in result["reasons"]))

    def test_unusable_image_without_main10_is_only_that_interface(self):
        result = evaluate(
            payload(
                [
                    interface("surface", True, True),
                    interface("byte_buffer", True, True),
                    interface("image", False, True),
                    interface("encoder", True, False),
                    interface("decoder", True, False),
                ],
                main10=False,
            )
        )
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["rejectedClaims"], ["image"])
        self.assertEqual(
            result["preservedResults"],
            ["surface", "byte_buffer", "encoder", "decoder"],
        )
        self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])

    def test_all_unusable_with_main10_is_unavailable_not_qualified(self):
        result = evaluate(
            payload(
                [interface(name, False, True) for name in _NAMES],
                main10=True,
            )
        )
        self.assertEqual(result["decision"], "unavailable")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(result["preservedResults"], [])
        self.assertEqual(
            result["rejectedClaims"],
            ["surface", "byte_buffer", "image", "encoder", "decoder", "main10-implies-p010-image"],
        )

    def test_all_usable_with_main10_qualifies_image_only_because_it_is_usable(self):
        result = evaluate(
            payload(
                [interface(name, True, True) for name in _NAMES],
                main10=True,
            )
        )
        self.assertEqual(result["decision"], "qualified")
        self.assertEqual(result["preservedResults"], list(_NAMES))
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])

    def test_main10_does_not_invent_a_missing_image_interface(self):
        result = evaluate(
            payload(
                [
                    interface("surface", True, True),
                    interface("byte_buffer", True, True),
                    interface("encoder", True, False),
                    interface("decoder", True, False),
                ],
                main10=True,
            )
        )
        self.assertEqual(result["decision"], "qualified")
        self.assertNotIn("image", result["preservedResults"])
        self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertEqual(
            result["preservedResults"],
            ["surface", "byte_buffer", "encoder", "decoder"],
        )

    def test_usable_eight_bit_surface_is_preserved_without_being_renamed(self):
        result = evaluate(
            payload(
                [
                    interface("surface", True, False),
                    interface("image", False, False),
                ],
                main10=True,
            )
        )
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], ["surface"])
        self.assertEqual(
            result["rejectedClaims"],
            ["image", "main10-implies-p010-image"],
        )

    def test_input_order_is_preserved_for_split_results(self):
        result = evaluate(
            payload(
                [
                    interface("decoder", False, False),
                    interface("encoder", True, True),
                    interface("byte_buffer", True, True),
                    interface("surface", False, True),
                    interface("image", False, True),
                ],
                main10=True,
            )
        )
        self.assertEqual(result["decision"], "partial")
        self.assertEqual(result["preservedResults"], ["encoder", "byte_buffer"])
        self.assertEqual(
            result["rejectedClaims"],
            ["decoder", "surface", "image", "main10-implies-p010-image"],
        )

    def test_invalid_payload_raises(self):
        valid = interface("surface", True, True)
        cases = [
            None,
            [],
            {},
            {"interfaces": [valid]},
            {"main10Advertised": False},
            {"interfaces": [valid], "main10Advertised": False, "extra": 1},
            {"interfaces": [], "main10Advertised": False},
            {"interfaces": valid, "main10Advertised": False},
            {"interfaces": [valid], "main10Advertised": 1},
            {"interfaces": [valid], "main10Advertised": "true"},
            {"interfaces": [None], "main10Advertised": False},
            {"interfaces": ["surface"], "main10Advertised": False},
            {"interfaces": [{**valid, "path": "surface"}], "main10Advertised": False},
            {"interfaces": [{k: v for k, v in valid.items() if k != "tenBit"}], "main10Advertised": False},
            {"interfaces": [{**valid, "name": "byte-buffer"}], "main10Advertised": False},
            {"interfaces": [{**valid, "name": "Image"}], "main10Advertised": False},
            {"interfaces": [{**valid, "name": ""}], "main10Advertised": False},
            {"interfaces": [{**valid, "usable": 1}], "main10Advertised": False},
            {"interfaces": [{**valid, "usable": "true"}], "main10Advertised": False},
            {"interfaces": [{**valid, "tenBit": 0}], "main10Advertised": True},
            {"interfaces": [valid, valid], "main10Advertised": False},
            {
                "interfaces": [interface("surface"), interface("surface", False)],
                "main10Advertised": False,
            },
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
