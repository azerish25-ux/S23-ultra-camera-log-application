"""TC-P011-03 selecting every supported stream is not coexistence."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p011_tc03", Path(__file__).resolve().parents[1] / "gates" / "p011_tc03.py"
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


def payload(**overrides):
    base = {
        "outputs": [
            {"id": "preview", "supportedAlone": True},
            {"id": "record", "supportedAlone": True},
        ],
        "constraintsViolated": True,
        "selectAll": True,
        "variant": "mixed_preview",
        "aeMin": rate(15),
        "aeMax": rate(30),
        "requestedFps": rate(24),
        "containerTimestampsAssigned": False,
    }
    base.update(overrides)
    return base


class TcP01103(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P011-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native_fixed_24"})
        self.assertTrue(result["reasons"])

    def test_encodes_intervention_expected_and_negative(self):
        self.assertIn("simultaneous combination", _MODULE.INTERVENTION)
        self.assertIn("coexistence", _MODULE.EXPECTED)
        self.assertIn("simultaneously must fail", _MODULE.NEGATIVE)

    def test_selecting_every_stream_fails_and_keeps_individual_support(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["preview", "record"])
        self.assertEqual(
            result["preservedResults"],
            ["alone:preview", "alone:record", "ae:15/1-30/1", "requested:24/1"],
        )
        self.assertTrue(any("not coexistence" in item for item in result["reasons"]))

    def test_repeats_mixed_preview_raw_encoder_and_alternate_lens(self):
        variants = {
            "mixed_preview": ("preview-sdr", "preview-hlg"),
            "raw_plus_encoder": ("raw", "hevc"),
            "alternate_lens": ("wide", "tele"),
        }
        for variant, (left, right) in variants.items():
            result = evaluate(
                payload(
                    variant=variant,
                    selectAll=True,
                    constraintsViolated=False,
                    outputs=[
                        {"id": left, "supportedAlone": True},
                        {"id": right, "supportedAlone": True},
                    ],
                )
            )
            with self.subTest(variant=variant):
                self.assert_contract(result)
                self.assertEqual(result["decision"], "rejected")
                self.assertEqual(result["rejectedClaims"], [left, right])
                self.assertIn(f"alone:{left}", result["preservedResults"])
                self.assertIn("ae:15/1-30/1", result["preservedResults"])
                self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_constraints_reject_even_when_not_selecting_all(self):
        result = evaluate(payload(selectAll=False, constraintsViolated=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["preview", "record"])
        self.assertIn("alone:preview", result["preservedResults"])

    def test_subset_is_withheld_rather_than_certified(self):
        result = evaluate(
            payload(
                selectAll=False,
                constraintsViolated=False,
                outputs=[{"id": "preview", "supportedAlone": True}],
                containerTimestampsAssigned=True,
            )
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["native-fixed-24"])
        self.assertIn("alone:preview", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "variant": "hdr"},
            {**valid, "outputs": []},
            {**valid, "outputs": [{"id": "a", "supportedAlone": True}, {"id": "a", "supportedAlone": True}]},
            {**valid, "selectAll": "yes"},
            {**valid, "requestedFps": {"numerator": 0, "denominator": 1}},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
