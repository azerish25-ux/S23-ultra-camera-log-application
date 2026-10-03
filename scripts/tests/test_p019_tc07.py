"""TC-P019-07 independent monitoring toggle."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p019_tc07", Path(__file__).resolve().parents[1] / "gates" / "p019_tc07.py"
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
_HASH = "clean-master-exposure-a1"


def payload(**overrides):
    base = {
        "aid": "histogram",
        "enabled": True,
        "cleanMasterHash": _HASH,
        "recordedHash": _HASH,
        "overlayRecordedIntoMaster": False,
    }
    base.update(overrides)
    return base


class TcP01907(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P019-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("viewing transforms", _MODULE.INTERVENTION)
        self.assertIn("deterministic contract", _MODULE.EXPECTED)
        self.assertIn("false-color overlay", _MODULE.NEGATIVE)
        self.assertIn("histogram", _MODULE.AIDS)
        self.assertIn("focus_peaking", _MODULE.AIDS)
        self.assertIn("film_preview", _MODULE.AIDS)
        self.assertIn("virtual_depth_display", _MODULE.AIDS)

    def test_histogram_leaves_the_clean_master_unchanged(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "clean_unchanged")
        self.assertEqual(result["preservedResults"], ["clean:" + _HASH])
        self.assertEqual(result["rejectedClaims"], [])

    def test_focus_peaking_disabled_also_leaves_the_master(self):
        result = evaluate(payload(aid="focus_peaking", enabled=False))
        self.assertEqual(result["decision"], "clean_unchanged")
        self.assertIn("clean:" + _HASH, result["preservedResults"])
        self.assertTrue(any("disabled" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_film_preview_overlay_in_the_master_is_rejected(self):
        result = evaluate(payload(aid="film_preview", overlayRecordedIntoMaster=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["overlay-in-clean-master", "film_preview"])
        self.assertEqual(result["preservedResults"], ["clean:" + _HASH])

    def test_virtual_depth_hash_disagreement_is_rejected(self):
        result = evaluate(
            payload(aid="virtual_depth_display", recordedHash="graded-master-b2")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("overlay-in-clean-master", result["rejectedClaims"])
        self.assertIn("clean:" + _HASH, result["preservedResults"])
        self.assertNotIn("clean:graded-master-b2", result["preservedResults"])
        self.assertTrue(any("disagrees" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "aid": "zebra"},
            {**valid, "enabled": 1},
            {**valid, "cleanMasterHash": ""},
            {**valid, "recordedHash": " graded"},
            {k: v for k, v in valid.items() if k != "aid"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
