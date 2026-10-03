"""TC-P048-01 whole-frame mean is not a known neutral target."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p048_tc01", Path(__file__).resolve().parents[1] / "gates" / "p048_tc01.py"
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
        "patchId": "grey-18",
        "defect": "none",
        "wholeFrameMean": "180",
        "knownNeutral": True,
        "substituteMean": False,
    }
    base.update(overrides)
    return base


class TcP04801(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P048-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("patch:grey-18", result["preservedResults"])
        self.assertIn("whole-frame-mean:180", result["preservedResults"])

    def test_constants(self):
        self.assertIn("clipped, textured, specular", _MODULE.INTERVENTION)
        self.assertIn("explicitly provisional", _MODULE.EXPECTED)
        self.assertIn("Whole-image average brightness", _MODULE.NEGATIVE)

    def test_known_neutral_stays_provisional(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("known-neutral:true", result["preservedResults"])

    def test_negative_whole_frame_mean_is_rejected(self):
        result = evaluate(payload(substituteMean=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("whole-frame-mean-substitution", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("whole-frame-mean:180", result["preservedResults"])

    def test_repeat_dark_patch_rejects_scale(self):
        result = evaluate(payload(defect="dark"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("invalid-neutral:dark", result["rejectedClaims"])
        self.assertIn("defect:dark", result["preservedResults"])

    def test_repeat_colored_illumination_rejects_scale(self):
        result = evaluate(payload(defect="colored", patchId="patch-color"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("invalid-neutral:colored", result["rejectedClaims"])
        self.assertIn("patch:patch-color", result["preservedResults"])
        self.assertIn("whole-frame-mean:180", result["preservedResults"])

    def test_repeat_mixed_pixels_and_partial_clip_are_rejected(self):
        for defect in ("mixed", "partial_clip"):
            result = evaluate(payload(defect=defect))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn(f"invalid-neutral:{defect}", result["rejectedClaims"])
            self.assertIn(f"defect:{defect}", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        for item in (None, {}, {**valid, "extra": True}, {**valid, "defect": "soft"}):
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
