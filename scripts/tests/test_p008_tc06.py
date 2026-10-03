"""Tests for TC-P008-06 uncontrolled threshold revision gate."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_GATE = Path(__file__).resolve().parents[1] / "gates" / "p008_tc06.py"
_SPEC = importlib.util.spec_from_file_location("p008_tc06", _GATE)
assert _SPEC is not None and _SPEC.loader is not None
gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gate)

KEYS = {"caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"}
REMOTE = "fedcba9876543210fedcba9876543210fedcba98"
GATES = ("cadence", "color error", "render latency", "temporal artifact severity")


def payload(name, loosened, reviewed, version_recorded, original_failed, remote=REMOTE, local_build=True):
    return {
        "threshold": {
            "name": name,
            "loosened": loosened,
            "reviewed": reviewed,
            "versionRecorded": version_recorded,
            "originalFailed": original_failed,
        },
        "remoteCommit": remote,
        "localBuildSucceeded": local_build,
    }


class P008Tc06Test(unittest.TestCase):
    def assert_contract(self, result, decision):
        self.assertEqual(KEYS, set(result))
        self.assertEqual(
            ["caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"],
            list(result),
        )
        self.assertEqual("TC-P008-06", result["caseId"])
        self.assertEqual(decision, result["decision"])
        self.assertNotIn(result["decision"], {"allowed", "complete"})
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertIn(REMOTE, result["preservedResults"])
        self.assertIn("physical-device gate pending", result["openQuestions"])

    def test_unreviewed_loosening_is_blocked_and_keeps_original_failure(self):
        partial = (
            (False, False),
            (True, False),
            (False, True),
        )
        for name in GATES:
            for reviewed, version_recorded in partial:
                for local_build in (True, False):
                    with self.subTest(name=name, reviewed=reviewed, version_recorded=version_recorded, local_build=local_build):
                        result = gate.evaluate(payload(
                            name, True, reviewed, version_recorded, True, local_build=local_build,
                        ))
                        self.assert_contract(result, "blocked")
                        self.assertEqual(
                            [f"original-failure:{name}", REMOTE],
                            result["preservedResults"],
                        )
                        self.assertIn(name, result["rejectedClaims"])
                        self.assertIn("original-pass", result["rejectedClaims"])
                        self.assertNotIn(result["decision"], {"allowed", "complete", "reviewed_revision"})
                        if local_build:
                            self.assertTrue(any("does not erase the original failure" in reason for reason in result["reasons"]))

    def test_reviewed_versioned_loosening_is_revision_not_completion(self):
        for name in GATES:
            for original_failed in (True, False):
                with self.subTest(name=name, original_failed=original_failed):
                    result = gate.evaluate(payload(name, True, True, True, original_failed, local_build=True))
                    self.assert_contract(result, "reviewed_revision")
                    self.assertNotEqual("complete", result["decision"])
                    self.assertIn("original-pass", result["rejectedClaims"])
                    self.assertIn("phase-complete", result["rejectedClaims"])
                    if original_failed:
                        self.assertEqual([f"original-failure:{name}", REMOTE], result["preservedResults"])
                    else:
                        self.assertEqual([REMOTE], result["preservedResults"])

    def test_unloosened_original_failure_stays_failed(self):
        for name in GATES:
            with self.subTest(name=name):
                result = gate.evaluate(payload(name, False, False, False, True, local_build=True))
                self.assert_contract(result, "failed")
                self.assertEqual([f"original-failure:{name}", REMOTE], result["preservedResults"])
                self.assertIn(name, result["rejectedClaims"])
                self.assertNotEqual("complete", result["decision"])

    def test_unloosened_passing_threshold_is_unchanged_not_complete(self):
        for name in GATES:
            with self.subTest(name=name):
                result = gate.evaluate(payload(name, False, True, True, False, local_build=True))
                self.assert_contract(result, "unchanged")
                self.assertEqual([REMOTE], result["preservedResults"])
                self.assertEqual([], result["rejectedClaims"])
                self.assertNotIn(result["decision"], {"allowed", "complete", "reviewed_revision"})

    def test_local_build_cannot_turn_blocked_cadence_into_a_pass(self):
        result = gate.evaluate(payload("cadence", True, False, False, True, local_build=True))
        self.assert_contract(result, "blocked")
        self.assertIn("original-failure:cadence", result["preservedResults"])
        self.assertNotIn("allowed", result["decision"])

    def test_bad_input_raises_value_error(self):
        valid = payload("cadence", True, False, False, True)
        with self.assertRaises(ValueError):
            gate.evaluate(None)
        with self.assertRaises(ValueError):
            gate.evaluate({"remoteCommit": REMOTE, "localBuildSucceeded": True})
        with self.assertRaises(ValueError):
            gate.evaluate({**valid, "threshold": []})
        incomplete = payload("cadence", True, False, False, True)
        del incomplete["threshold"]["originalFailed"]
        with self.assertRaises(ValueError):
            gate.evaluate(incomplete)
        with self.assertRaises(ValueError):
            gate.evaluate(payload("  ", True, False, False, True))
        with self.assertRaises(ValueError):
            gate.evaluate(payload("color error", "yes", False, False, True))
        with self.assertRaises(ValueError):
            gate.evaluate(payload("render latency", True, 1, False, True))
        with self.assertRaises(ValueError):
            gate.evaluate(payload("temporal artifact severity", True, False, False, True, remote=""))
        with self.assertRaises(ValueError):
            gate.evaluate({
                "threshold": valid["threshold"],
                "remoteCommit": REMOTE,
                "localBuildSucceeded": "true",
            })


if __name__ == "__main__":
    unittest.main()
