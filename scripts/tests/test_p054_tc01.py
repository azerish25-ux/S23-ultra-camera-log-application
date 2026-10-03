"""TC-P054-01 negative and bright intermediate values."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p054_tc01", Path(__file__).resolve().parents[1] / "gates" / "p054_tc01.py"
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
        "sampleId": "hair-px",
        "locus": "around-zero",
        "codeValue": "-0.02",
        "sourceWhite": "1",
        "storageLimit": "none",
        "implicitClamp": False,
    }
    base.update(overrides)
    return base


class TcP05401(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P054-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_repeat_around_zero_retains_signed_values(self):
        below = evaluate(payload(codeValue="-0.02"))
        above = evaluate(payload(codeValue="0.02", sampleId="zero-plus"))
        for result, code in ((below, "-0.02"), (above, "0.02")):
            self.assertContract(result)
            self.assertEqual(result["decision"], "retained")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(f"code:{code}", result["preservedResults"])
            self.assertIn("locus:around-zero", result["preservedResults"])

    def test_repeat_source_white_keeps_over_range(self):
        at_white = evaluate(payload(locus="source-white", codeValue="1", sampleId="white"))
        over = evaluate(payload(locus="above-white", codeValue="2.4", sampleId="highlight"))
        self.assertContract(at_white)
        self.assertEqual(at_white["decision"], "retained")
        self.assertIn("code:1", at_white["preservedResults"])
        self.assertIn("source-white:1", at_white["preservedResults"])
        self.assertContract(over)
        self.assertEqual(over["decision"], "retained")
        self.assertIn("code:2.4", over["preservedResults"])
        self.assertIn("highlight", over["preservedResults"])

    def test_repeat_encoding_boundary_limits_only_at_declared_storage(self):
        at_limit = evaluate(
            payload(locus="encoding-boundary", codeValue="1", storageLimit="1", sampleId="edge")
        )
        beyond = evaluate(
            payload(locus="encoding-boundary", codeValue="1.05", storageLimit="1", sampleId="over-edge")
        )
        self.assertEqual(at_limit["decision"], "retained")
        self.assertIn("code:1", at_limit["preservedResults"])
        self.assertEqual(beyond["decision"], "storage-limited")
        self.assertIn("beyond-declared-limit", beyond["rejectedClaims"])
        self.assertIn("code:1.05", beyond["preservedResults"])
        self.assertIn("stored:1", beyond["preservedResults"])
        self.assertNotIn(beyond["decision"], {"qualified", "allowed"})

    def test_negative_implicit_clamp_is_rejected_and_keeps_the_code(self):
        result = evaluate(payload(locus="below-black", codeValue="-0.4", implicitClamp=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["implicit-zero-to-one-clamp"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("code:-0.4", result["preservedResults"])
        self.assertNotIn("code:0", result["preservedResults"])
        highlight = evaluate(
            payload(locus="above-white", codeValue="4", implicitClamp=True, sampleId="clip")
        )
        self.assertEqual(highlight["decision"], "rejected")
        self.assertIn("code:4", highlight["preservedResults"])
        self.assertNotIn(highlight["decision"], {"qualified", "allowed", "retained"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "codeValue"},
            {**valid, "extra": True},
            {**valid, "locus": "black"},
            {**valid, "codeValue": "-0"},
            {**valid, "codeValue": "0.020"},
            {**valid, "sourceWhite": "0"},
            {**valid, "storageLimit": "none "},
            {**valid, "implicitClamp": 1},
            {**valid, "sampleId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
