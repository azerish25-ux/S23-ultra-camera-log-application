"""TC-P026-04 configure success does not excuse a contradictory stream."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p026_tc04", Path(__file__).resolve().parents[1] / "gates" / "p026_tc04.py"
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
        "contradiction": "eight_bit_after_ten_bit",
        "configureOnly": False,
        "mediaId": "hevc-access-unit",
        "requested": "Main10/10",
        "emitted": "SPS/8",
        "status": "eight-bit-output",
    }
    base.update(overrides)
    return base


class TcP02604(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P026-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("actual stream", _MODULE.INTERVENTION)
        self.assertIn("useful media", _MODULE.EXPECTED)
        self.assertIn("configure parameters", _MODULE.NEGATIVE)
        self.assertIn("eight_bit_after_ten_bit", _MODULE.CONTRADICTIONS)
        self.assertIn("wrong_color_range", _MODULE.CONTRADICTIONS)

    def test_eight_bit_output_after_a_ten_bit_request_fails(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "output_contract_failed")
        self.assertEqual(result["rejectedClaims"], ["eight_bit_after_ten_bit"])
        self.assertIn("hevc-access-unit", result["preservedResults"])
        self.assertIn("SPS/8", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_wrong_color_range_fails_while_media_is_kept(self):
        result = evaluate(
            payload(
                contradiction="wrong_color_range",
                requested="limited",
                emitted="full",
                status="wrong-range",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "output_contract_failed")
        self.assertEqual(result["rejectedClaims"], ["wrong_color_range"])
        self.assertIn("hevc-access-unit", result["preservedResults"])
        self.assertIn("full", result["preservedResults"])

    def test_trusting_only_configure_parameters_fails(self):
        result = evaluate(payload(configureOnly=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("configure-parameters-only", result["rejectedClaims"])
        self.assertIn("eight_bit_after_ten_bit", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "output_contract_failed"})
        self.assertIn("hevc-access-unit", result["preservedResults"])

    def test_silent_log_relabel_is_rejected(self):
        result = evaluate(payload(status="acceptable-log"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("inaccurate-status", result["rejectedClaims"])
        self.assertIn("hevc-access-unit", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "contradiction": "bit-depth"},
            {**valid, "status": "  "},
            {**valid, "configureOnly": "true"},
            {k: v for k, v in valid.items() if k != "mediaId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
