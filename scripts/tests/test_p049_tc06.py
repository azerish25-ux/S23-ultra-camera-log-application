"""TC-P049-06 a real highlight is not removed with every isolated bright pixel."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p049_tc06", Path(__file__).resolve().parents[1] / "gates" / "p049_tc06.py"
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
        "frameCount": 1,
        "defectPersistent": True,
        "realHighlight": True,
        "site": "interior",
        "removeEveryIsolatedBright": False,
    }
    base.update(overrides)
    return base


class TcP04906(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P049-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertIn("sensor defect", _MODULE.INTERVENTION)
        self.assertIn("supported defect", _MODULE.EXPECTED)
        self.assertIn("isolated bright pixel", _MODULE.NEGATIVE)

    def test_several_frames_correct_only_the_defect(self):
        result = evaluate(payload(frameCount=6))
        self.assertContract(result)
        self.assertEqual(result["decision"], "defect_only")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("frames:6", result["preservedResults"])
        self.assertIn("real-highlight:preserved", result["preservedResults"])
        self.assertIn("defect:supported", result["preservedResults"])

    def test_saturated_boundary_keeps_the_real_feature(self):
        result = evaluate(payload(frameCount=4, site="saturated-boundary"))
        self.assertEqual(result["decision"], "defect_only")
        self.assertIn("site:saturated-boundary", result["preservedResults"])
        self.assertIn("real-highlight:preserved", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_removing_every_isolated_bright_pixel_fails(self):
        result = evaluate(payload(frameCount=6, site="saturated-boundary", removeEveryIsolatedBright=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["remove-every-isolated-bright"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("real-highlight:preserved", result["preservedResults"])
        self.assertIn("frames:6", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "defect_only"})

    def test_missing_real_highlight_is_withheld(self):
        result = evaluate(payload(realHighlight=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("real-highlight:absent", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "frameCount": 0},
            {**valid, "frameCount": True},
            {**valid, "site": "edge"},
            {**valid, "defectPersistent": 1},
            {k: v for k, v in valid.items() if k != "site"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
