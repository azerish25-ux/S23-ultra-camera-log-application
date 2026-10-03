"""TC-P024-01 late callbacks must not resurrect the current owner."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p024_tc01", Path(__file__).resolve().parents[1] / "gates" / "p024_tc01.py"
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
        "moment": "before_first_sample",
        "ownerGeneration": 2,
        "callbackGeneration": 1,
        "resurrectsRecording": False,
        "attachesObsoleteSurface": False,
        "releasesOnlyStaleResources": True,
        "currentTakeId": "take-current",
        "staleResourceId": "surface-stale",
    }
    base.update(overrides)
    return base


class TcP02401(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P024-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)

    def test_module_encodes_case_text(self):
        self.assertIn("previous camera or recording generation", _MODULE.INTERVENTION)
        self.assertIn("Ignore stale state mutation", _MODULE.EXPECTED)
        self.assertIn("resurrects recording", _MODULE.NEGATIVE)
        self.assertEqual(
            _MODULE.MOMENTS,
            (
                "before_first_sample",
                "during_stopping",
                "after_activity_recreation",
                "after_camera_reopen",
            ),
        )

    def test_before_first_sample_ignores_stale_callback(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "ignored")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["take-current", "surface-stale"])
        self.assertTrue(any("before_first_sample" in item for item in result["reasons"]))
        self.assertTrue(any(_MODULE.EXPECTED in item for item in result["reasons"]))

    def test_during_stopping_ignores_stale_callback(self):
        result = evaluate(
            payload(
                moment="during_stopping",
                ownerGeneration=4,
                callbackGeneration=2,
                currentTakeId="take-stopping",
                staleResourceId="session-old",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "ignored")
        self.assertEqual(result["preservedResults"], ["take-stopping", "session-old"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(any("during_stopping" in item for item in result["reasons"]))

    def test_resurrection_after_activity_recreation_is_rejected(self):
        result = evaluate(
            payload(moment="after_activity_recreation", resurrectsRecording=True)
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("resurrected-recording", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["take-current", "surface-stale"])
        self.assertIn("recreation does not transfer ownership to a stale callback", result["openQuestions"])
        self.assertTrue(any(_MODULE.NEGATIVE in item for item in result["reasons"]))

    def test_obsolete_surface_after_camera_reopen_is_rejected(self):
        result = evaluate(
            payload(
                moment="after_camera_reopen",
                attachesObsoleteSurface=True,
                currentTakeId="take-reopen",
                staleResourceId="surface-obsolete",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("obsolete-surface", result["rejectedClaims"])
        self.assertIn("take-reopen", result["preservedResults"])
        self.assertIn("surface-obsolete", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "ignored"})

    def test_releasing_current_owner_resources_is_rejected(self):
        result = evaluate(payload(moment="during_stopping", releasesOnlyStaleResources=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("released-current-owner-resources", result["rejectedClaims"])
        self.assertIn("take-current", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "moment": "after_stop"},
            {**valid, "ownerGeneration": 0},
            {**valid, "callbackGeneration": 2},
            {**valid, "callbackGeneration": True},
            {**valid, "resurrectsRecording": 1},
            {**valid, "currentTakeId": "two words"},
            {key: value for key, value in valid.items() if key != "moment"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
