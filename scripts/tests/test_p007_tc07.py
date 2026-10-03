"""TC-P007-07 concurrent collaborator change."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from gates.p007_tc07 import evaluate

CASE_ID = "TC-P007-07"
RESULT_KEYS = [
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
]
HASH_A = "a" * 64
HASH_B = "b" * 64


def profiles():
    return [
        {"displayName": "Stock", "sha256": HASH_A},
        {"displayName": "Stock", "sha256": HASH_B},
    ]


def payload(**overrides):
    collaborator = {
        "present": True,
        "preserved": True,
        "overlapping": False,
        "remoteHeadChanged": False,
        "content": "unrelated collaborator modification",
    }
    collaborator.update(overrides.pop("collaborator", {}))
    body = {
        "caseId": CASE_ID,
        "collaborator": collaborator,
        "integratedRevision": "c" * 40,
        "profiles": profiles(),
    }
    body.update(overrides)
    return body


class Tcp007Tc07Tests(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(list(result), RESULT_KEYS)
        self.assertEqual(set(result), set(RESULT_KEYS))
        self.assertEqual(result["caseId"], CASE_ID)
        self.assertIsInstance(result["reasons"], list)
        self.assertIsInstance(result["rejectedClaims"], list)
        self.assertIsInstance(result["preservedResults"], list)
        self.assertIsInstance(result["openQuestions"], list)
        self.assertNotIn(result["decision"], {"allowed", "passed"})
        self.assertTrue(result["reasons"])
        self.assertNotEqual(result["preservedResults"].count(HASH_A), 0)
        self.assertNotEqual(result["preservedResults"].count(HASH_B), 0)

    def test_overlapping_collaborator_is_integrated(self):
        content = "overlapping collaborator bytes"
        revision = "d" * 40
        result = evaluate(
            payload(
                collaborator={
                    "overlapping": True,
                    "content": content,
                },
                integratedRevision=revision,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "integrated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"], [content, revision, HASH_A, HASH_B]
        )
        text = " ".join(result["reasons"]).lower()
        self.assertIn("overlap", text)
        self.assertNotIn("remote head", text)

    def test_non_overlapping_collaborator_is_integrated(self):
        content = "non shared collaborator file"
        revision = "e" * 40
        result = evaluate(
            payload(
                collaborator={
                    "overlapping": False,
                    "remoteHeadChanged": False,
                    "content": content,
                },
                integratedRevision=revision,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "integrated")
        self.assertEqual(
            result["preservedResults"], [content, revision, HASH_A, HASH_B]
        )
        text = " ".join(result["reasons"]).lower()
        self.assertNotIn("overlap", text)
        self.assertNotIn("remote head", text)

    def test_remote_head_change_before_push(self):
        content = "kept collaborator note"
        revision = "f" * 40
        result = evaluate(
            payload(
                collaborator={
                    "overlapping": False,
                    "remoteHeadChanged": True,
                    "preserved": True,
                    "content": content,
                },
                integratedRevision=revision,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "integrated")
        self.assertIn(content, result["preservedResults"])
        self.assertIn(revision, result["preservedResults"])
        text = " ".join(result["reasons"]).lower()
        self.assertIn("remote head", text)
        self.assertNotIn("overlap", text)

    def test_overlapping_and_remote_head_are_both_mentioned(self):
        result = evaluate(
            payload(
                collaborator={
                    "overlapping": True,
                    "remoteHeadChanged": True,
                }
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "integrated")
        text = " ".join(result["reasons"]).lower()
        self.assertIn("overlap", text)
        self.assertIn("remote head", text)

    def test_clean_demonstration_reset_is_blocked_and_never_allowed(self):
        content = "collaborator work that was overwritten"
        for overlapping, remote in ((False, False), (True, False), (False, True), (True, True)):
            result = evaluate(
                payload(
                    collaborator={
                        "present": True,
                        "preserved": False,
                        "overlapping": overlapping,
                        "remoteHeadChanged": remote,
                        "content": content,
                    }
                )
            )
            self.assert_contract(result)
            self.assertEqual(result["decision"], "blocked")
            self.assertNotEqual(result["decision"], "allowed")
            self.assertEqual(result["rejectedClaims"], ["clean-demonstration-reset"])
            self.assertEqual(result["preservedResults"][0], content)
            self.assertIn(HASH_A, result["preservedResults"])
            self.assertIn(HASH_B, result["preservedResults"])

    def test_absent_collaborator_is_unchanged(self):
        result = evaluate(
            payload(
                collaborator={
                    "present": False,
                    "preserved": False,
                    "overlapping": True,
                    "remoteHeadChanged": True,
                    "content": "ignored because absent",
                }
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], [HASH_A, HASH_B])
        self.assertNotIn("ignored because absent", result["preservedResults"])

    def test_identical_display_names_do_not_collapse_hashes(self):
        third = "9" * 64
        body = payload()
        body["profiles"] = [
            {"displayName": "Stock", "sha256": HASH_A},
            {"displayName": "Stock", "sha256": HASH_B},
            {"displayName": "Other", "sha256": third},
        ]
        result = evaluate(body)
        self.assertEqual(
            [item for item in result["preservedResults"] if item in {HASH_A, HASH_B, third}],
            [HASH_A, HASH_B, third],
        )

    def test_wrong_case_id_and_invalid_payload_raise(self):
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate({"caseId": "TC-P007-08"})
        with self.assertRaises(ValueError):
            evaluate({"caseId": CASE_ID})
        broken = payload()
        broken["collaborator"]["present"] = 1
        with self.assertRaises(ValueError):
            evaluate(broken)
        broken = payload()
        broken["profiles"] = [{"displayName": "Stock", "sha256": HASH_A}]
        broken["profiles"].append({"displayName": "Stock"})
        with self.assertRaises(ValueError):
            evaluate(broken)
        broken = payload()
        del broken["integratedRevision"]
        with self.assertRaises(ValueError):
            evaluate(broken)

    def test_result_reasons_stay_non_empty(self):
        variants = [
            payload(),
            payload(collaborator={"present": False}),
            payload(collaborator={"preserved": False}),
        ]
        for body in variants:
            result = evaluate(body)
            self.assertNotEqual(result["decision"], "allowed")
            self.assertTrue(result["reasons"])
            self.assertTrue(all(isinstance(reason, str) and reason for reason in result["reasons"]))


if __name__ == "__main__":
    unittest.main()
