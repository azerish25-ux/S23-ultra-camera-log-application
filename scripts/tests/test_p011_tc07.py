"""TC-P011-07 Main10 does not imply P010 Image support."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p011_tc07", Path(__file__).resolve().parents[1] / "gates" / "p011_tc07.py"
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


def rate(numerator=15, denominator=1):
    return {"numerator": numerator, "denominator": denominator}


def interface(name, usable, ten_bit=False):
    return {"name": name, "usable": usable, "tenBit": ten_bit}


def payload(**overrides):
    base = {
        "interfaces": [
            interface("surface", True, True),
            interface("image", False, False),
        ],
        "main10Advertised": True,
        "advertisedSize": "1920x1080",
        "aeMin": rate(15),
        "aeMax": rate(30),
        "requestedFps": rate(24),
        "containerTimestampsAssigned": False,
    }
    base.update(overrides)
    return base


class TcP01107(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P011-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native_fixed_24"})
        self.assertTrue(result["reasons"])

    def test_encodes_intervention_expected_and_negative(self):
        self.assertIn("ten-bit", _MODULE.INTERVENTION)
        self.assertIn("independently", _MODULE.EXPECTED)
        self.assertIn("P010 Image", _MODULE.NEGATIVE)

    def test_surface_stays_when_image_is_unavailable(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "partial")
        self.assertIn("surface", result["preservedResults"])
        self.assertIn("1920x1080", result["preservedResults"])
        self.assertIn("ae:15/1-30/1", result["preservedResults"])
        self.assertIn("image", result["rejectedClaims"])
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertNotIn("image", result["preservedResults"])
        self.assertTrue(any("does not imply P010 Image" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeats_across_surface_buffer_image_encoder_and_decoder(self):
        names = ("surface", "byte_buffer", "image", "encoder", "decoder")
        for name in names:
            interfaces = [
                interface(other, other != name, ten_bit=other == "surface" and other != name)
                for other in names
            ]
            result = evaluate(payload(interfaces=interfaces, main10Advertised=True))
            with self.subTest(name=name):
                self.assert_contract(result)
                self.assertIn(name, result["rejectedClaims"])
                self.assertNotIn(name, result["preservedResults"])
                self.assertIn("1920x1080", result["preservedResults"])
                self.assertIn("requested:24/1", result["preservedResults"])
                if name == "image":
                    self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
                else:
                    self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])
                self.assertNotEqual(result["decision"], "qualified")

    def test_main10_without_an_image_interface_is_not_image_support(self):
        result = evaluate(
            payload(
                interfaces=[interface("surface", True, True), interface("encoder", True, True)],
                main10Advertised=True,
            )
        )
        self.assertEqual(result["decision"], "partial")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interface_available"})
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertIn("surface", result["preservedResults"])
        self.assertIn("encoder", result["preservedResults"])

    def test_every_listed_interface_usable_is_still_not_ten_bit_fidelity(self):
        result = evaluate(
            payload(
                interfaces=[
                    interface("surface", True, True),
                    interface("byte_buffer", True, True),
                    interface("image", True, True),
                    interface("encoder", True, False),
                    interface("decoder", True, False),
                ],
                main10Advertised=True,
                containerTimestampsAssigned=True,
            )
        )
        self.assertEqual(result["decision"], "interface_available")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("native-fixed-24", result["rejectedClaims"])
        self.assertNotIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertIn("image", result["preservedResults"])
        self.assertTrue(any("not ten-bit fidelity" in item for item in result["reasons"]))

    def test_no_usable_interface_is_unavailable(self):
        result = evaluate(
            payload(
                interfaces=[interface("decoder", False, False)],
                main10Advertised=False,
            )
        )
        self.assertEqual(result["decision"], "unavailable")
        self.assertEqual(result["rejectedClaims"], ["decoder"])
        self.assertIn("1920x1080", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "interfaces": []},
            {**valid, "interfaces": [interface("p010", True)]},
            {**valid, "advertisedSize": "1920X1080"},
            {**valid, "main10Advertised": "true"},
            {**valid, "interfaces": [interface("surface", True), interface("surface", False)]},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
