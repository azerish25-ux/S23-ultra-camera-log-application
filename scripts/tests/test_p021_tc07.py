"""TC-P021-07 independent monitoring toggle."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p021_tc07", Path(__file__).resolve().parents[1] / "gates" / "p021_tc07.py"
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
_SOURCE = "abc123"


def payload(**overrides):
    base = {
        "aid": "histogram",
        "toggles": 4,
        "sourceHash": _SOURCE,
        "masterHash": _SOURCE,
        "overlayRecordedIntoMaster": False,
    }
    base.update(overrides)
    return base


class TcP02107(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P021-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        for token in _MODULE.FOCUS_INVENTORY:
            self.assertIn(token, result["preservedResults"])
        self.assertIn("source.hash:" + _SOURCE, result["preservedResults"])

    def test_module_encodes_intervention_expected_and_negative(self):
        self.assertIn("Toggle overlays and viewing transforms", _MODULE.INTERVENTION)
        self.assertIn("clean-source or clean-master", _MODULE.EXPECTED)
        self.assertIn("false-color overlay or preview grade", _MODULE.NEGATIVE)
        for name in ("histogram", "focus_peaking", "film_preview", "virtual_depth_display"):
            self.assertIn(name, _MODULE.REPEATS)

    def test_repeat_histogram_leaves_master_unchanged(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertIn("master.hash:" + _SOURCE, result["preservedResults"])
        self.assertTrue(any("histogram" in item for item in result["reasons"]))
        self.assertIn("physical.distance:unknown", result["preservedResults"])

    def test_repeat_focus_peaking_leaves_master_unchanged(self):
        result = evaluate(payload(aid="focus_peaking", toggles=2))
        self.assertContract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertTrue(any("focus_peaking" in item for item in result["reasons"]))
        self.assertIn("virtual.relativeDepth:0.62", result["preservedResults"])

    def test_repeat_film_preview_and_virtual_depth_display(self):
        for aid in ("film_preview", "virtual_depth_display"):
            result = evaluate(payload(aid=aid, toggles=6))
            self.assertContract(result)
            self.assertEqual(result["decision"], "unchanged")
            self.assertIn("master.hash:" + _SOURCE, result["preservedResults"])
            self.assertTrue(any(aid in item for item in result["reasons"]))

    def test_negative_overlay_in_master_is_rejected(self):
        result = evaluate(
            payload(aid="film_preview", overlayRecordedIntoMaster=True, masterHash="graded")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unchanged"})
        self.assertIn("overlay-in-master:film_preview", result["rejectedClaims"])
        self.assertNotIn("master.hash:graded", result["preservedResults"])
        self.assertIn("source.hash:" + _SOURCE, result["preservedResults"])

    def test_negative_virtual_depth_overlay_does_not_qualify_master(self):
        result = evaluate(payload(aid="virtual_depth_display", overlayRecordedIntoMaster=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("overlay-in-master:virtual_depth_display", result["rejectedClaims"])
        self.assertIn("source.hash:" + _SOURCE, result["preservedResults"])
        self.assertNotIn("master.hash:" + _SOURCE, result["preservedResults"])

    def test_changed_master_without_overlay_is_rejected(self):
        result = evaluate(payload(masterHash="other"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("clean-master-changed", result["rejectedClaims"])
        self.assertIn("source.hash:" + _SOURCE, result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "aid": "zebra"},
            {**valid, "toggles": 0},
            {**valid, "sourceHash": ""},
            {**valid, "overlayRecordedIntoMaster": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
