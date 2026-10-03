"""Host checks for the P030 publication gate. Not a physical S23 probe.

TC-P030-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p030_publish_media_transactionally import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    assess_publication,
    honest_retains_staging,
    mutant_deletes_before_accept,
    provider_action,
    trace_publication,
    validate_fixture,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
HANDOFF_KEYS = (
    "phase",
    "caseIds",
    "changedFiles",
    "commit",
    "testsRun",
    "failures",
    "unverified",
    "nextPhase",
)
FORBIDDEN = {"qualified", "allowed"}
OWNED = [
    "scripts/gates/p030_publish_media_transactionally.py",
    "scripts/tests/test_p030_publish_media_transactionally.py",
    "docs/P030_PUBLISH_MEDIA_TRANSACTIONALLY.md",
    "docs/P030_PUBLISH_MEDIA_TRANSACTIONALLY.json",
    "docs/evidence/P030-handoff.json",
    "scripts/gates/p030_tc01.py",
    "scripts/gates/p030_tc02.py",
    "scripts/gates/p030_tc03.py",
    "scripts/gates/p030_tc04.py",
    "scripts/gates/p030_tc05.py",
    "scripts/gates/p030_tc06.py",
    "scripts/gates/p030_tc07.py",
    "scripts/gates/p030_tc08.py",
    "scripts/tests/test_p030_tc01.py",
    "scripts/tests/test_p030_tc02.py",
    "scripts/tests/test_p030_tc03.py",
    "scripts/tests/test_p030_tc04.py",
    "scripts/tests/test_p030_tc05.py",
    "scripts/tests/test_p030_tc06.py",
    "scripts/tests/test_p030_tc07.py",
    "scripts/tests/test_p030_tc08.py",
]


def load_fixture() -> dict:
    path = ROOT / "docs" / "P030_PUBLISH_MEDIA_TRANSACTIONALLY.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_handoff() -> dict:
    path = ROOT / "docs" / "evidence" / "P030-handoff.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _step(steps: list[dict], name: str) -> dict:
    return next(item for item in steps if item["name"] == name)


class P030PublishMediaTests(unittest.TestCase):
    def assert_result(self, result: dict) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P030")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_constants_and_fixture_encode_method_oracle_and_mutant(self) -> None:
        raw = load_fixture()
        self.assertIsNone(validate_fixture(raw))
        self.assertEqual(CASE_ID, "P030")
        self.assertEqual(MAP_ID, "s23-publish-media-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P030")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertIn("private staging", METHOD)
        self.assertIn("temporary duplication", METHOD.lower())
        self.assertIn("Failed report export", METHOD)
        self.assertIn("full gallery destination", FIXTURE)
        self.assertIn("report serialization exception", FIXTURE)
        self.assertIn("recovery storage", ORACLE)
        self.assertIn("no empty gallery success", ORACLE)
        self.assertIn("before the public copy is durably accepted", MUTANT)
        self.assertTrue(raw["recording"]["privateRecordingSucceeded"])
        self.assertEqual(raw["recording"]["sourceId"], "take-030")
        self.assertEqual(raw["recording"]["bytes"], 4096)
        self.assertEqual(raw["destination"]["kind"], "gallery")
        self.assertEqual(raw["destination"]["space"], "full")
        self.assertEqual(raw["provider"]["semantics"], "copy")
        self.assertIs(raw["provider"]["publicCopyDurablyAccepted"], False)
        self.assertIs(raw["staging"]["present"], True)
        self.assertEqual(raw["staging"]["location"], "recovery")
        self.assertIs(raw["staging"]["deletedBeforeDurableAccept"], False)
        self.assertIs(raw["gallery"]["emptySuccessShown"], False)
        self.assertEqual(raw["gallery"]["entries"], [])
        self.assertEqual(raw["error"]["step"], "report_export")
        self.assertEqual(raw["error"]["code"], "report-serialization-exception")
        self.assertEqual(
            [item["name"] for item in raw["steps"]],
            [
                "private_staging",
                "inspect",
                "copy_or_move",
                "commit",
                "report_export",
                "redundant_staging_cleanup",
            ],
        )

    def test_full_gallery_report_failure_keeps_recovery_source(self) -> None:
        raw = load_fixture()
        before = copy.deepcopy(raw)
        trace = trace_publication(raw)
        self.assertEqual(trace["semantics"], "copy")
        self.assertIs(trace["temporaryDuplication"], True)
        self.assertIs(trace["cleanupPermitted"], False)
        self.assertIs(trace["stagingRetained"], True)
        self.assertEqual(trace["failedStep"], "report_export")
        self.assertEqual(trace["failedSteps"], ["copy_or_move", "report_export"])
        self.assertEqual(provider_action(raw), "copy")
        self.assertNotEqual(provider_action(raw), "delete")
        result = assess_publication(raw)
        self.assertEqual(raw, before)
        self.assert_result(result)
        self.assertEqual(result["decision"], "recovery_retained")
        self.assertNotIn(result["decision"], FORBIDDEN | {"publication_recorded", "media_retained"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            [
                "source:take-030",
                "recovery:take-030",
                "bytes:4096",
                "staging:present",
                "location:recovery",
                "semantics:copy",
                "durable-accept:false",
                "failed-step:report_export",
                "error:report-serialization-exception",
                "duplication-budget:temporary",
            ],
        )
        self.assertEqual(
            result["reasons"],
            [
                ORACLE,
                "copy_or_move failed: destination-full",
                "report_export failed: report-serialization-exception",
                "the source remains in recovery storage",
                "no empty gallery success is shown",
                "temporary duplication is budgeted",
                "redundant staging was not removed",
                "failed publication step report_export identified as report-serialization-exception",
            ],
        )
        self.assertEqual(
            result["openQuestions"],
            [
                "host fixture does not qualify a physical S23",
                "public copy is not durably accepted",
                "destination space is full",
                "report export failed; media remains discoverable",
            ],
        )

    def test_mutant_would_delete_staging_but_assess_does_not(self) -> None:
        raw = load_fixture()
        self.assertTrue(mutant_deletes_before_accept(raw))
        self.assertTrue(honest_retains_staging(raw))
        self.assertFalse(raw["provider"]["publicCopyDurablyAccepted"])
        result = assess_publication(raw)
        self.assertEqual(result["decision"], "recovery_retained")
        self.assertIn("staging:present", result["preservedResults"])
        self.assertIn("location:recovery", result["preservedResults"])
        self.assertNotIn("staging:absent", result["preservedResults"])
        self.assertNotIn("staging-deleted-before-durable-accept", result["rejectedClaims"])
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertTrue(honest_retains_staging(raw))

    def test_mutant_document_is_rejected_without_wiping_inventory(self) -> None:
        raw = load_fixture()
        raw["staging"]["present"] = False
        raw["staging"]["location"] = "absent"
        raw["staging"]["deletedBeforeDurableAccept"] = True
        self.assertTrue(mutant_deletes_before_accept(raw))
        self.assertFalse(honest_retains_staging(raw))
        result = assess_publication(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], FORBIDDEN | {"recovery_retained", "publication_recorded"})
        self.assertIn("staging-deleted-before-durable-accept", result["rejectedClaims"])
        self.assertIn(MUTANT, result["reasons"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertEqual(result["preservedResults"][:3], raw["inventory"])
        self.assertIn("source:take-030", result["preservedResults"])
        self.assertIn("recovery:take-030", result["preservedResults"])
        self.assertIn("bytes:4096", result["preservedResults"])
        self.assertIn("staging:absent", result["preservedResults"])
        self.assertIn("the inventory is preserved", result["reasons"])

    def test_move_under_storage_pressure_still_retains_recovery(self) -> None:
        raw = load_fixture()
        raw["provider"]["semantics"] = "move"
        self.assertEqual(provider_action(raw), "move")
        self.assertNotEqual(provider_action(raw), "delete")
        self.assertTrue(mutant_deletes_before_accept(raw))
        self.assertTrue(honest_retains_staging(raw))
        trace = trace_publication(raw)
        self.assertIs(trace["cleanupPermitted"], False)
        self.assertIs(trace["temporaryDuplication"], True)
        self.assertEqual(trace["semantics"], "move")
        result = assess_publication(raw)
        self.assertEqual(result["decision"], "recovery_retained")
        self.assertIn("semantics:move", result["preservedResults"])
        self.assertIn("staging:present", result["preservedResults"])
        self.assertIn("source:take-030", result["preservedResults"])
        self.assertNotIn(result["decision"], FORBIDDEN)

    def test_revoked_grant_during_commit_is_recovery_not_empty_success(self) -> None:
        raw = load_fixture()
        raw["destination"]["space"] = "available"
        raw["destination"]["grant"] = "revoked"
        _step(raw["steps"], "copy_or_move")["outcome"] = "succeeded"
        _step(raw["steps"], "copy_or_move")["reason"] = None
        _step(raw["steps"], "commit")["outcome"] = "failed"
        _step(raw["steps"], "commit")["reason"] = "grant-revoked"
        _step(raw["steps"], "report_export")["outcome"] = "not_reached"
        _step(raw["steps"], "report_export")["reason"] = None
        raw["error"] = {"step": "commit", "code": "grant-revoked"}
        result = assess_publication(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "recovery_retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("commit failed: grant-revoked", result["reasons"])
        self.assertIn("source:take-030", result["preservedResults"])
        self.assertIn("staging:present", result["preservedResults"])
        self.assertIn("failed-step:commit", result["preservedResults"])
        self.assertIn("publication grant was revoked", result["openQuestions"])
        self.assertNotIn("destination space is full", result["openQuestions"])
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertIs(trace_publication(raw)["cleanupPermitted"], False)

    def test_empty_gallery_success_is_rejected_and_keeps_the_source(self) -> None:
        raw = load_fixture()
        raw["gallery"]["emptySuccessShown"] = True
        result = assess_publication(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("empty-gallery-success", result["rejectedClaims"])
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertIn("source:take-030", result["preservedResults"])
        self.assertIn("bytes:4096", result["preservedResults"])
        self.assertIn("an empty gallery success was claimed", result["reasons"])

    def test_report_failure_after_durable_accept_leaves_media_discoverable(self) -> None:
        raw = load_fixture()
        raw["destination"]["space"] = "available"
        raw["provider"]["publicCopyDurablyAccepted"] = True
        for name in ("private_staging", "inspect", "copy_or_move", "commit"):
            _step(raw["steps"], name)["outcome"] = "succeeded"
            _step(raw["steps"], name)["reason"] = None
        _step(raw["steps"], "report_export")["outcome"] = "failed"
        _step(raw["steps"], "report_export")["reason"] = "report-serialization-exception"
        _step(raw["steps"], "redundant_staging_cleanup")["outcome"] = "not_reached"
        _step(raw["steps"], "redundant_staging_cleanup")["reason"] = None
        raw["gallery"]["entries"] = ["gallery:take-030"]
        raw["error"] = {"step": "report_export", "code": "report-serialization-exception"}
        self.assertFalse(mutant_deletes_before_accept(raw))
        self.assertTrue(honest_retains_staging(raw))
        result = assess_publication(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "media_retained")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("gallery-entry:gallery:take-030", result["preservedResults"])
        self.assertIn("staging:present", result["preservedResults"])
        self.assertIn("source:take-030", result["preservedResults"])
        self.assertIn("failed report export left media intact and discoverable", result["reasons"])
        self.assertIn("report export failed; media remains discoverable", result["openQuestions"])
        self.assertTrue(trace_publication(raw)["cleanupPermitted"])
        self.assertIs(trace_publication(raw)["stagingRetained"], True)

    def test_cleanup_after_durable_accept_is_not_the_mutant(self) -> None:
        raw = load_fixture()
        raw["destination"]["space"] = "available"
        raw["provider"]["semantics"] = "move"
        raw["provider"]["publicCopyDurablyAccepted"] = True
        for name in ("private_staging", "inspect", "copy_or_move", "commit", "report_export"):
            _step(raw["steps"], name)["outcome"] = "succeeded"
            _step(raw["steps"], name)["reason"] = None
        _step(raw["steps"], "redundant_staging_cleanup")["outcome"] = "succeeded"
        _step(raw["steps"], "redundant_staging_cleanup")["reason"] = None
        raw["staging"]["present"] = False
        raw["staging"]["location"] = "absent"
        raw["staging"]["deletedBeforeDurableAccept"] = False
        raw["gallery"]["entries"] = ["gallery:take-030"]
        raw["gallery"]["emptySuccessShown"] = False
        raw["error"] = None
        raw["inventory"] = ["source:take-030", "bytes:4096", "gallery:take-030"]
        self.assertFalse(mutant_deletes_before_accept(raw))
        result = assess_publication(raw)
        self.assertEqual(result["decision"], "publication_recorded")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("staging:absent", result["preservedResults"])
        self.assertIn("semantics:move", result["preservedResults"])
        self.assertIn("durable-accept:true", result["preservedResults"])
        self.assertIn("gallery-entry:gallery:take-030", result["preservedResults"])
        self.assertIn("source:take-030", result["preservedResults"])
        self.assertIn(
            "publication_recorded is a host-fixture label, not physical S23 qualification",
            result["reasons"],
        )
        self.assertIn("publication_recorded is not physical qualification", result["openQuestions"])
        self.assertTrue(trace_publication(raw)["cleanupPermitted"])

    def test_doc_and_handoff_state_host_limits(self) -> None:
        text = (ROOT / "docs" / "P030_PUBLISH_MEDIA_TRANSACTIONALLY.md").read_text(encoding="utf-8")
        self.assertIn("host fixture", text.lower())
        self.assertIn(
            "python3 -m unittest discover -s scripts/tests -p 'test_p030*.py' -v",
            text,
        )
        self.assertIn("Non-claims", text)
        self.assertIn("physical S23", text)
        self.assertIn("not a physical S23 qualification", text)
        self.assertIn("fixed cadence without measured evidence", text)
        self.assertIn("sensor-derived Log", text)
        self.assertIn("ten-bit fidelity", text)
        self.assertIn("film-stock fidelity", text)
        self.assertIn("cinema-camera equivalence", text)
        handoff = load_handoff()
        self.assertEqual(tuple(handoff), HANDOFF_KEYS)
        self.assertEqual(handoff["phase"], "P030")
        self.assertEqual(handoff["nextPhase"], "P031")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], [])
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p030*.py' -v",
        )
        self.assertEqual(
            handoff["caseIds"],
            [f"TC-P030-0{index}" for index in range(1, 9)],
        )
        self.assertEqual(handoff["changedFiles"], OWNED)
        for claim in (
            "physical S23 capture",
            "fixed cadence without measured evidence",
            "sensor-derived Log",
            "ten-bit fidelity",
            "film-stock fidelity",
            "cinema-camera equivalence",
        ):
            self.assertIn(claim, handoff["unverified"])

    def test_invalid_documents_raise(self) -> None:
        valid = load_fixture()
        early_cleanup = copy.deepcopy(valid)
        _step(early_cleanup["steps"], "copy_or_move")["outcome"] = "succeeded"
        _step(early_cleanup["steps"], "copy_or_move")["reason"] = None
        _step(early_cleanup["steps"], "commit")["outcome"] = "succeeded"
        _step(early_cleanup["steps"], "redundant_staging_cleanup")["outcome"] = "succeeded"
        early_cleanup["destination"]["space"] = "available"
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["oracle"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P029"
        durable_full = copy.deepcopy(valid)
        durable_full["provider"]["publicCopyDurablyAccepted"] = True
        chain = copy.deepcopy(valid)
        _step(chain["steps"], "commit")["outcome"] = "succeeded"
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            durable_full,
            chain,
            early_cleanup,
            {**valid, "schemaVersion": True},
            {**valid, "implementationBaseRevision": "abc"},
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_fixture(sample)


if __name__ == "__main__":
    unittest.main()
