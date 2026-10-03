"""TC-P008-07 concurrent collaborator change."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


def _load():
    path = Path(__file__).resolve().parents[1] / "gates" / "p008_tc07.py"
    spec = importlib.util.spec_from_file_location("p008_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load()

RESULT_KEYS = [
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
]


def payload(**overrides):
    collaborator = {
        "present": True,
        "preserved": True,
        "overlapping": False,
        "remoteHeadChanged": False,
        "content": "docs/note.txt",
    }
    collaborator.update(overrides.pop("collaborator", {}))
    base = {
        "collaborator": collaborator,
        "integratedRevision": "int-rev-1",
        "remoteCommit": "abc123def456",
        "localBuildSucceeded": False,
    }
    base.update(overrides)
    return base


class TcP00807Tests(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(list(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "TC-P008-07")
        self.assertIsInstance(result["reasons"], list)
        self.assertIsInstance(result["rejectedClaims"], list)
        self.assertIsInstance(result["preservedResults"], dict)
        self.assertIsInstance(result["openQuestions"], list)
        self.assertNotIn(result["decision"], ("complete", "allowed"))
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_reset_is_blocked_even_when_local_build_succeeded(self):
        content = {"path": "app/src/main/AndroidManifest.xml", "text": "collaborator edit"}
        body = payload(
            collaborator={
                "present": True,
                "preserved": False,
                "overlapping": True,
                "remoteHeadChanged": True,
                "content": content,
            },
            localBuildSucceeded=True,
            remoteCommit="remote-before-push",
            integratedRevision="should-not-authorize-completion",
        )
        original = copy.deepcopy(body)
        result = gate.evaluate(body)
        self.assertEqual(body, original)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "blocked")
        self.assertEqual(result["rejectedClaims"], ["clean-demonstration-reset"])
        self.assertEqual(result["preservedResults"]["content"], content)
        self.assertEqual(result["preservedResults"]["remoteCommit"], "remote-before-push")
        self.assertNotIn("integratedRevision", result["preservedResults"])
        text = " ".join(result["reasons"]).lower()
        self.assertIn("overlapping", text)
        self.assertIn("remote head", text)

    def test_reset_stays_blocked_when_local_build_failed(self):
        body = payload(
            collaborator={"present": True, "preserved": False, "content": "kept.txt"},
            localBuildSucceeded=False,
        )
        result = gate.evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "blocked")
        self.assertIn("clean-demonstration-reset", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"]["content"], "kept.txt")
        self.assertEqual(
            result["preservedResults"]["remoteCommit"], body["remoteCommit"]
        )

    def test_overlapping_files_are_integrated_not_complete(self):
        content = [
            "scripts/gates/p008_tc07.py",
            "app/src/main/java/com/s23log/probe/MainActivity.kt",
        ]
        body = payload(
            collaborator={
                "present": True,
                "preserved": True,
                "overlapping": True,
                "remoteHeadChanged": False,
                "content": content,
            },
            integratedRevision="rev-overlap",
            remoteCommit="commit-overlap",
            localBuildSucceeded=True,
        )
        result = gate.evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "integrated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], [])
        self.assertEqual(result["preservedResults"]["content"], content)
        self.assertEqual(result["preservedResults"]["integratedRevision"], "rev-overlap")
        self.assertEqual(result["preservedResults"]["remoteCommit"], "commit-overlap")
        text = " ".join(result["reasons"]).lower()
        self.assertIn("overlapping", text)
        self.assertNotIn("remote head", text)

    def test_non_overlapping_files_are_integrated(self):
        content = ["docs/PORTFOLIO.md"]
        body = payload(
            collaborator={
                "present": True,
                "preserved": True,
                "overlapping": False,
                "remoteHeadChanged": False,
                "content": content,
            },
            integratedRevision="rev-disjoint",
            remoteCommit="commit-disjoint",
            localBuildSucceeded=False,
        )
        result = gate.evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "integrated")
        self.assertEqual(result["preservedResults"]["content"], content)
        self.assertEqual(result["preservedResults"]["integratedRevision"], "rev-disjoint")
        self.assertEqual(result["preservedResults"]["remoteCommit"], "commit-disjoint")
        text = " ".join(result["reasons"]).lower()
        self.assertNotIn("overlapping", text)
        self.assertNotIn("remote head", text)

    def test_remote_head_change_before_push_is_reported(self):
        content = "unrelated-collaborator.patch"
        body = payload(
            collaborator={
                "present": True,
                "preserved": True,
                "overlapping": False,
                "remoteHeadChanged": True,
                "content": content,
            },
            integratedRevision="rev-after-fetch",
            remoteCommit="new-remote-head",
            localBuildSucceeded=True,
        )
        result = gate.evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "integrated")
        self.assertNotEqual(result["decision"], "complete")
        text = " ".join(result["reasons"]).lower()
        self.assertIn("remote head", text)
        self.assertNotIn("overlapping", text)
        self.assertEqual(result["preservedResults"]["content"], content)
        self.assertEqual(result["preservedResults"]["integratedRevision"], "rev-after-fetch")
        self.assertEqual(result["preservedResults"]["remoteCommit"], "new-remote-head")

    def test_overlapping_and_remote_head_are_both_mentioned(self):
        body = payload(
            collaborator={
                "overlapping": True,
                "remoteHeadChanged": True,
                "preserved": True,
                "present": True,
                "content": "shared.kt",
            }
        )
        result = gate.evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "integrated")
        text = " ".join(result["reasons"]).lower()
        self.assertIn("overlapping", text)
        self.assertIn("remote head", text)

    def test_absent_collaborator_is_unchanged_and_preserves_remote_commit(self):
        for local_build in (False, True):
            with self.subTest(local_build=local_build):
                body = payload(
                    collaborator={
                        "present": False,
                        "preserved": False,
                        "overlapping": False,
                        "remoteHeadChanged": False,
                        "content": "",
                    },
                    remoteCommit="stable-remote",
                    localBuildSucceeded=local_build,
                )
                result = gate.evaluate(body)
                self.assert_contract(result)
                self.assertEqual(result["decision"], "unchanged")
                self.assertEqual(result["rejectedClaims"], [])
                self.assertEqual(result["preservedResults"], {"remoteCommit": "stable-remote"})
                self.assertNotIn("content", result["preservedResults"])

    def test_absent_collaborator_still_preserves_a_moved_remote_head(self):
        body = payload(
            collaborator={
                "present": False,
                "preserved": True,
                "overlapping": True,
                "remoteHeadChanged": True,
                "content": "ignored-because-absent",
            },
            remoteCommit="moved-head",
            localBuildSucceeded=True,
        )
        result = gate.evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertEqual(result["preservedResults"]["remoteCommit"], "moved-head")
        self.assertIn("remote head", " ".join(result["reasons"]).lower())
        self.assertNotIn("overlapping", " ".join(result["reasons"]).lower())

    def test_local_build_never_yields_complete_or_allowed(self):
        variants = [
            {"present": True, "preserved": False},
            {"present": True, "preserved": True, "overlapping": True},
            {"present": True, "preserved": True, "remoteHeadChanged": True},
            {"present": False, "preserved": False},
        ]
        for flags in variants:
            for local_build in (False, True):
                with self.subTest(flags=flags, local_build=local_build):
                    collaborator = {
                        "present": False,
                        "preserved": False,
                        "overlapping": False,
                        "remoteHeadChanged": False,
                        "content": "x",
                    }
                    collaborator.update(flags)
                    result = gate.evaluate(
                        payload(collaborator=collaborator, localBuildSucceeded=local_build)
                    )
                    self.assert_contract(result)
                    self.assertNotIn(result["decision"], ("complete", "allowed"))

    def test_invalid_payload_raises_value_error(self):
        valid = payload()
        invalid = [
            None,
            [],
            "payload",
            {},
            {**valid, "extra": True},
            {key: valid[key] for key in valid if key != "remoteCommit"},
            {**valid, "localBuildSucceeded": 1},
            {**valid, "integratedRevision": ""},
            {**valid, "integratedRevision": "   "},
            {**valid, "remoteCommit": ""},
            {**valid, "remoteCommit": None},
            {**valid, "collaborator": []},
            {**valid, "collaborator": {**valid["collaborator"], "present": "true"}},
            {**valid, "collaborator": {**valid["collaborator"], "preserved": 0}},
            {**valid, "collaborator": {**valid["collaborator"], "overlapping": 1}},
            {
                **valid,
                "collaborator": {
                    key: valid["collaborator"][key]
                    for key in valid["collaborator"]
                    if key != "content"
                },
            },
            {
                **valid,
                "collaborator": {**valid["collaborator"], "extraFlag": False},
            },
        ]
        for body in invalid:
            with self.subTest(body=body):
                with self.assertRaises(ValueError):
                    gate.evaluate(body)


if __name__ == "__main__":
    unittest.main()
