"""TC-P050-01 signed and over-range values are not clamped to zero-to-one."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p050_tc01", Path(__file__).resolve().parents[1] / "gates" / "p050_tc01.py"
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
        "anchor": "zero",
        "samples": [-4, 0, 16, 1400],
        "black": 16,
        "sourceWhite": 1023,
        "storageLimit": 65535,
        "displayLimit": 4095,
        "implicitClamp": False,
    }
    base.update(overrides)
    return base


class TcP05001(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P050-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(any(item.startswith("sample:") for item in result["preservedResults"]))

    def test_constants(self):
        self.assertIn("below black", _MODULE.INTERVENTION)
        self.assertIn("storage or display limit", _MODULE.EXPECTED)
        self.assertIn("zero-to-one clamp", _MODULE.NEGATIVE)

    def test_repeat_around_zero(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sample:-4", result["preservedResults"])
        self.assertIn("signed:-4:-20", result["preservedResults"])
        self.assertIn("signed:0:-16", result["preservedResults"])
        self.assertIn("ratio:1400:1384/1007", result["preservedResults"])
        self.assertTrue(any("around zero" in item for item in result["reasons"]))

    def test_repeat_source_white_reference(self):
        result = evaluate(
            payload(
                anchor="source_white",
                samples=[-2, 1023, 1100],
                black=64,
                sourceWhite=1023,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained")
        self.assertIn("sample:1023", result["preservedResults"])
        self.assertIn("signed:1100:1036", result["preservedResults"])
        self.assertTrue(any("not a hard ceiling" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_encoding_boundary(self):
        result = evaluate(
            payload(
                anchor="encoding_boundary",
                samples=[-1, 2000, 4095, 5000],
                black=0,
                sourceWhite=1000,
                storageLimit=65535,
                displayLimit=4095,
            )
        )
        self.assertEqual(result["decision"], "retained")
        self.assertIn("sample:4095", result["preservedResults"])
        self.assertIn("declared-limit:5000", result["openQuestions"])
        self.assertTrue(any("not forced into zero-to-one" in item for item in result["reasons"]))
        self.assertIn("anchor:encoding_boundary", result["preservedResults"])

    def test_implicit_clamp_is_rejected(self):
        result = evaluate(payload(implicitClamp=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retained"})
        self.assertEqual(result["rejectedClaims"], ["implicit-zero-to-one-clamp"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("sample:1400", result["preservedResults"])
        self.assertIn("signed:-4:-20", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "anchor": "mid"},
            {**valid, "samples": [0, 1]},
            {**valid, "implicitClamp": 1},
            {**valid, "sourceWhite": 16},
            {k: v for k, v in valid.items() if k != "black"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
