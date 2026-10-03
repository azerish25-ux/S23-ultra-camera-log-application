"""TC-P020-07 monitoring toggles do not grade the clean master."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p020_tc07", Path(__file__).resolve().parents[1] / "gates" / "p020_tc07.py"
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
_SOURCE = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_OTHER = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def payload(**overrides):
    base = {
        "aid": "histogram",
        "toggles": 3,
        "sourceHash": _SOURCE,
        "masterHash": _SOURCE,
        "overlayRecordedIntoMaster": False,
    }
    base.update(overrides)
    return base


class TcP02007(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P020-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def assertInventory(self, result):
        for item in _MODULE.WB_INVENTORY:
            self.assertIn(item, result["preservedResults"])
        self.assertIn("source.hash:" + _SOURCE, result["preservedResults"])
        self.assertIn("creative.slider:warm", result["preservedResults"])
        self.assertIn("hardware.kelvin:unavailable", result["preservedResults"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("viewing transforms", _MODULE.INTERVENTION)
        self.assertIn("clean-master", _MODULE.EXPECTED)
        self.assertIn("preview grade", _MODULE.NEGATIVE)
        self.assertIn("histogram", _MODULE.REPEATS)
        self.assertIn("focus_peaking", _MODULE.REPEATS)
        self.assertIn("film_preview", _MODULE.REPEATS)
        self.assertIn("virtual_depth_display", _MODULE.REPEATS)

    def test_histogram_leaves_the_clean_master_unchanged(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertInventory(result)
        self.assertIn("master.hash:" + _SOURCE, result["preservedResults"])
        self.assertTrue(any("histogram" in item for item in result["reasons"]))

    def test_focus_peaking_also_leaves_the_master_unchanged(self):
        result = evaluate(payload(aid="focus_peaking", toggles=5))
        self.assertContract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertInventory(result)
        self.assertTrue(any("focus_peaking" in item for item in result["reasons"]))

    def test_film_preview_overlay_in_the_master_is_rejected(self):
        result = evaluate(payload(aid="film_preview", overlayRecordedIntoMaster=True, masterHash=_OTHER))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unchanged"})
        self.assertEqual(result["rejectedClaims"], ["overlay-in-master:film_preview"])
        self.assertInventory(result)
        self.assertNotIn("master.hash:" + _OTHER, result["preservedResults"])

    def test_virtual_depth_preview_grade_in_the_master_is_rejected(self):
        result = evaluate(payload(aid="virtual_depth_display", overlayRecordedIntoMaster=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("overlay-in-master:virtual_depth_display", result["rejectedClaims"])
        self.assertInventory(result)
        self.assertIn("source.metadata:unchanged", result["preservedResults"])

    def test_clean_master_drift_without_an_overlay_is_rejected(self):
        result = evaluate(payload(masterHash=_OTHER))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["clean-master-changed"])
        self.assertInventory(result)

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "aid": "scopes"},
            {**valid, "toggles": 0},
            {**valid, "sourceHash": ""},
            {**valid, "overlayRecordedIntoMaster": 1},
            {**valid, "extra": True},
            {k: v for k, v in valid.items() if k != "masterHash"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
