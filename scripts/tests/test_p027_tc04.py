"""TC-P027-04 configure parameters are not the emitted stream."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p027_tc04", Path(__file__).resolve().parents[1] / "gates" / "p027_tc04.py"
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
        "contradiction": "eight-bit-after-ten-bit",
        "trustConfigureOnly": False,
        "usefulMedia": "media-p027",
        "accurateStatus": True,
    }
    base.update(overrides)
    return base


class TcP02704(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P027-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("selected tracks", _MODULE.INTERVENTION)
        self.assertIn("accurate status", _MODULE.EXPECTED)
        self.assertIn("configure parameters", _MODULE.NEGATIVE)
        self.assertIn("eight-bit-after-ten-bit", _MODULE.CONTRADICTIONS)
        self.assertIn("wrong-color-range", _MODULE.CONTRADICTIONS)

    def test_eight_bit_after_ten_bit_fails_the_contract_and_keeps_media(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "contract_failed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["media-p027", "eight-bit-after-ten-bit"])
        self.assertTrue(any("accurate status" in item for item in result["reasons"]))

    def test_wrong_color_range_is_a_separate_repeat(self):
        result = evaluate(payload(contradiction="wrong-color-range", usefulMedia="range-clip"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "contract_failed")
        self.assertEqual(result["preservedResults"], ["range-clip", "wrong-color-range"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_trusting_configure_parameters_is_rejected(self):
        result = evaluate(payload(trustConfigureOnly=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "contract_failed"})
        self.assertEqual(result["rejectedClaims"], ["configure-parameters-trusted"])
        self.assertIn("media-p027", result["preservedResults"])
        self.assertIn("eight-bit-after-ten-bit", result["preservedResults"])

    def test_inaccurate_status_keeps_the_media_identity(self):
        result = evaluate(payload(accurateStatus=False, contradiction="wrong-dimensions"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("inaccurate-status", result["rejectedClaims"])
        self.assertIn("media-p027", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "contradiction": "ten-bit"},
            {**valid, "usefulMedia": ""},
            {**valid, "trustConfigureOnly": 1},
            {**valid, "accurateStatus": "true"},
            {k: v for k, v in valid.items() if k != "usefulMedia"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
