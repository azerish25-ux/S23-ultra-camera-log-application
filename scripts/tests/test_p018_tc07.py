"""TC-P018-07 independent monitoring toggle."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p018_tc07", Path(__file__).resolve().parents[1] / "gates" / "p018_tc07.py"
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
_CLEAN = "master-aa11"


def payload(**overrides):
    base = {
        "aid": "histogram",
        "enabled": True,
        "cleanMasterHash": _CLEAN,
        "recordedHash": _CLEAN,
        "overlayRecordedIntoMaster": False,
    }
    base.update(overrides)
    return base


class TcP01807(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P018-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_contract(self):
        self.assertIn("same controlled source sequence", _MODULE.INTERVENTION)
        self.assertIn("clean-master content unchanged", _MODULE.EXPECTED)
        self.assertIn("false-color overlay", _MODULE.NEGATIVE)
        self.assertIn("histogram", _MODULE.REPEAT)
        self.assertIn("focus peaking", _MODULE.REPEAT)

    def test_histogram_toggle_leaves_the_clean_master(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "clean_unchanged")
        self.assertEqual(result["preservedResults"], ["clean:" + _CLEAN])
        self.assertEqual(result["rejectedClaims"], [])

    def test_focus_peaking_disabled_also_leaves_the_clean_master(self):
        result = evaluate(payload(aid="focus_peaking", enabled=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "clean_unchanged")
        self.assertIn("clean:" + _CLEAN, result["preservedResults"])

    def test_overlay_recorded_into_the_master_is_rejected(self):
        for aid in ("film_preview", "virtual_depth_display"):
            result = evaluate(payload(aid=aid, overlayRecordedIntoMaster=True))
            with self.subTest(aid=aid):
                self.assertEqual(result["decision"], "rejected")
                self.assertNotIn(result["decision"], {"qualified", "allowed"})
                self.assertEqual(result["rejectedClaims"], ["overlay-in-clean-master", aid])
                self.assertEqual(result["preservedResults"], ["clean:" + _CLEAN])

    def test_hash_mismatch_is_rejected_even_without_the_overlay_flag(self):
        result = evaluate(payload(recordedHash="graded-bb22", overlayRecordedIntoMaster=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("clean:" + _CLEAN, result["preservedResults"])
        self.assertNotIn("clean:graded-bb22", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "aid": "zebra"},
            {**valid, "cleanMasterHash": ""},
            {**valid, "enabled": 1},
            {**valid, "overlayRecordedIntoMaster": "false"},
            {k: v for k, v in valid.items() if k != "recordedHash"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
