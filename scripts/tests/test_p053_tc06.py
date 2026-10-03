"""TC-P053-06 defect versus real highlight."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p053_tc06", Path(__file__).resolve().parents[1] / "gates" / "p053_tc06.py"
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


def frame(ident, defect, hx, hy, value):
    return {
        "id": ident,
        "defectValue": defect,
        "highlightX": hx,
        "highlightY": hy,
        "highlightValue": value,
    }


def payload(**overrides):
    base = {
        "policy": "measured-map",
        "frames": [
            frame("f0", 900, 3, 2, 880),
            frame("f1", 910, 4, 4, 860),
            frame("f2", 895, 7, 1, 1023),
        ],
        "defectX": 2,
        "defectY": 2,
        "supported": True,
        "persistent": True,
        "nearSaturated": False,
    }
    base.update(overrides)
    return base


class TcP05306(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P053-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn("defect:2,2", result["preservedResults"])

    def test_several_frames_correct_only_the_supported_defect(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "defect_corrected")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("frame:f0:highlight=3,2:880", result["preservedResults"])
        self.assertIn("frame:f1:highlight=4,4:860", result["preservedResults"])
        self.assertIn("frame:f2:highlight=7,1:1023", result["preservedResults"])
        self.assertIn("frame:f0:defect=900", result["preservedResults"])
        self.assertIn("policy:measured-map", result["preservedResults"])

    def test_near_saturated_boundary_still_preserves_the_highlight(self):
        result = evaluate(payload(nearSaturated=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "defect_corrected")
        self.assertIn("saturated-boundary", result["preservedResults"])
        self.assertIn("frame:f2:highlight=7,1:1023", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "rejected"})

    def test_removing_every_isolated_bright_pixel_fails(self):
        result = evaluate(payload(policy="intensity-threshold", nearSaturated=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            [
                "remove-every-isolated-bright-pixel",
                "highlight:f0:3,2",
                "highlight:f1:4,4",
                "highlight:f2:7,1",
            ],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("frame:f0:highlight=3,2:880", result["preservedResults"])
        self.assertIn("frame:f2:defect=895", result["preservedResults"])
        self.assertIn("saturated-boundary", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "defect_corrected"})

    def test_unsupported_or_stationary_highlight_is_withheld(self):
        unsupported = evaluate(payload(supported=False, persistent=False))
        self.assertEqual(unsupported["decision"], "withheld")
        self.assertEqual(unsupported["rejectedClaims"], ["unsupported-defect", "not-persistent"])
        self.assertIn("frame:f1:highlight=4,4:860", unsupported["preservedResults"])
        still = evaluate(
            payload(
                frames=[
                    frame("f0", 900, 3, 2, 880),
                    frame("f1", 910, 3, 2, 870),
                ]
            )
        )
        self.assertEqual(still["decision"], "withheld")
        self.assertIn("highlight-not-moving", still["rejectedClaims"])
        self.assertIn("frame:f0:highlight=3,2:880", still["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        one = payload(frames=[frame("f0", 900, 3, 2, 880)])
        cases = [
            None,
            {**valid, "policy": "median"},
            one,
            {**valid, "supported": "yes"},
            {**valid, "defectX": -1},
            {key: value for key, value in valid.items() if key != "frames"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
