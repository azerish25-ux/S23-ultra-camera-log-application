"""Host checks for the P031 interrupted-recording fixture. Not a physical S23 probe.

TC-P031-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p031_recover_interrupted_recordings import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_POLICY,
    ORACLE,
    apply_policy,
    assess,
    request_delete,
    retained_paths,
    validate_document,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
PARTIAL = "takes/take-7/partial.mp4:bytes=4096:nonempty=true:playable=false"
JOURNAL = "journal:takes/take-7/journal.json"
PRESERVED = [
    JOURNAL,
    "take:take-7",
    "track:video",
    "track:audio",
    "status:incomplete",
    "transition:muxer_finalization",
    "completedFlag:false",
    PARTIAL,
    "offer:export",
    "offer:retry",
]


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P031_RECOVER_INTERRUPTED_RECORDINGS.json").read_text(encoding="utf-8")
    )


def artefact(**overrides) -> dict:
    value = {
        "path": "takes/take-7/partial.mp4",
        "kind": "partial_mp4",
        "bytes": 4096,
        "nonempty": True,
        "playable": False,
        "validationComplete": False,
        "soleRetainedCopy": True,
    }
    value.update(overrides)
    return value


def document(**overrides) -> dict:
    value = load_document()
    value.update(overrides)
    return value


class P031RecoveryTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P031")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P031")
        self.assertEqual(MAP_ID, "s23-interrupted-recording-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("path identity", METHOD)
        self.assertIn("selected tracks", METHOD)
        self.assertIn("unfinished MP4", METHOD)
        self.assertIn("explicit export and retry", METHOD)
        self.assertIn("sole retained copy", METHOD)
        self.assertEqual(
            FIXTURE,
            "Process termination during muxer finalization with both a nonempty partial "
            "file and an incomplete journal record.",
        )
        self.assertEqual(
            ORACLE,
            "The recovery library exposes the artefact as unverified and does not discard "
            "it merely because normal validation cannot complete.",
        )
        self.assertEqual(MUTANT, "Delete every file lacking a completed journal flag.")
        self.assertEqual(MUTANT_POLICY, "delete_lacking_completed_journal")

    def test_fixture_exposes_partial_file_as_unverified(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P031")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertFalse(raw["journal"]["completedJournalFlag"])
        self.assertEqual(raw["journal"]["transition"], "muxer_finalization")
        self.assertEqual(raw["journal"]["selectedTracks"], ["video", "audio"])
        self.assertTrue(raw["artefacts"][0]["nonempty"])
        self.assertFalse(raw["artefacts"][0]["playable"])
        self.assertFalse(raw["artefacts"][0]["validationComplete"])
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertEqual(retained_paths(raw), ["takes/take-7/partial.mp4"])
        self.assertIn(PARTIAL, result["preservedResults"])
        self.assertIn(JOURNAL, result["preservedResults"])
        self.assertIn("offer:export", result["preservedResults"])
        self.assertIn("offer:retry", result["preservedResults"])
        self.assertEqual(
            result["openQuestions"],
            ["normal validation cannot complete", "unfinished output is not verified"],
        )
        self.assertIn(ORACLE, result["reasons"])
        self.assertTrue(any("not assumed playable" in item for item in result["reasons"]))
        self.assertTrue(any("not discarded" in item for item in result["reasons"]))
        self.assertNotIn("qualified", " ".join(result["reasons"]))

    def test_mutant_does_not_delete_files_lacking_completed_journal(self) -> None:
        raw = load_document()
        result = apply_policy(raw, MUTANT_POLICY)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unverified"})
        self.assertEqual(
            result["rejectedClaims"],
            ["delete-every-file-lacking-completed-journal"],
        )
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertIn(PARTIAL, result["preservedResults"])
        self.assertIn("takes/take-7/partial.mp4", retained_paths(raw))
        self.assertIn(MUTANT, result["reasons"])
        self.assertIn("files lacking a completed journal flag are retained", result["reasons"])
        self.assertNotIn("deleted", " ".join(result["preservedResults"]))
        # Implementing the mutant would drop this path from the inventory.
        self.assertTrue(any("partial.mp4" in item for item in result["preservedResults"]))

    def test_active_muxing_repeat_keeps_the_remnant(self) -> None:
        raw = load_document()
        raw["journal"]["transition"] = "active_muxing"
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertIn("transition:active_muxing", result["preservedResults"])
        self.assertIn(PARTIAL, result["preservedResults"])
        self.assertIn("track:audio", result["preservedResults"])

    def test_before_first_sample_with_no_media_is_withheld(self) -> None:
        raw = load_document()
        raw["journal"]["transition"] = "before_first_sample"
        raw["artefacts"] = []
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unverified"})
        self.assertIn(JOURNAL, result["preservedResults"])
        self.assertIn("transition:before_first_sample", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["no nonempty remnant"])
        self.assertFalse(any("partial.mp4" in item for item in result["preservedResults"]))
        mutant = apply_policy(raw, MUTANT_POLICY)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn(JOURNAL, mutant["preservedResults"])

    def test_after_publication_is_not_physical_qualification(self) -> None:
        raw = load_document()
        raw["journal"]["transition"] = "after_publication"
        raw["journal"]["terminalStatus"] = "published"
        raw["journal"]["completedJournalFlag"] = True
        raw["artefacts"] = [
            artefact(
                path="takes/take-7/final.mp4",
                bytes=8192,
                nonempty=True,
                playable=True,
                validationComplete=True,
                soleRetainedCopy=False,
            )
        ]
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "journal_complete")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("takes/take-7/final.mp4:bytes=8192:nonempty=true:playable=true",
                      result["preservedResults"])
        self.assertIn("completedFlag:true", result["preservedResults"])
        self.assertTrue(any("not physical S23 qualification" in item for item in result["reasons"]))

    def test_playable_claim_on_unfinished_mp4_is_rejected_and_kept(self) -> None:
        raw = load_document()
        raw["artefacts"][0]["playable"] = True
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["playable-unfinished-mp4"])
        self.assertIn(
            "takes/take-7/partial.mp4:bytes=4096:nonempty=true:playable=true",
            result["preservedResults"],
        )
        self.assertIn(JOURNAL, result["preservedResults"])

    def test_missing_export_or_retry_does_not_drop_the_file(self) -> None:
        raw = load_document()
        raw["offers"] = {"export": True, "retry": False}
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("missing-explicit-export-or-retry", result["rejectedClaims"])
        self.assertIn(PARTIAL, result["preservedResults"])
        self.assertNotIn("offer:retry", result["preservedResults"])
        self.assertIn("offer:export", result["preservedResults"])

    def test_scan_ignores_recorded_confirmation(self) -> None:
        raw = load_document()
        raw["deleteConfirmation"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "unverified")
        self.assertIn(PARTIAL, result["preservedResults"])
        self.assertIn("recorded confirmation does not discard the remnant during scan",
                      result["reasons"])

    def test_unconfirmed_sole_copy_delete_is_rejected(self) -> None:
        raw = load_document()
        result = request_delete(raw, False, ["takes/take-7/partial.mp4"])
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unconfirmed-sole-copy-delete"])
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertIn("the remnant was not discarded", result["reasons"])

    def test_confirmed_delete_keeps_the_inventory_token(self) -> None:
        raw = load_document()
        result = request_delete(raw, True, ["takes/take-7/partial.mp4"])
        self.assert_result(result)
        self.assertEqual(result["decision"], "delete_authorized")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(PARTIAL, result["preservedResults"])
        self.assertIn(JOURNAL, result["preservedResults"])
        self.assertTrue(any("does not verify the MP4" in item for item in result["reasons"]))

    def test_retain_policy_matches_assess(self) -> None:
        raw = load_document()
        self.assertEqual(apply_policy(raw, "retain"), assess(raw))

    def test_invalid_documents_and_requests_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P030"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        playable_type = copy.deepcopy(valid)
        playable_type["artefacts"][0]["playable"] = "false"
        empty_bytes = copy.deepcopy(valid)
        empty_bytes["artefacts"][0]["bytes"] = 0
        published_early = copy.deepcopy(valid)
        published_early["journal"]["terminalStatus"] = "published"
        published_early["journal"]["completedJournalFlag"] = True
        duplicate = copy.deepcopy(valid)
        duplicate["artefacts"].append(copy.deepcopy(duplicate["artefacts"][0]))
        two_soles = copy.deepcopy(valid)
        other = artefact(path="takes/take-7/audio.raw", kind="audio_partial", soleRetainedCopy=True)
        two_soles["artefacts"].append(other)
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            playable_type,
            empty_bytes,
            published_early,
            duplicate,
            two_soles,
            document(schemaVersion=True),
            document(mapId="other"),
            document(method="delete incomplete files"),
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            apply_policy(valid, "delete")
        with self.assertRaises(ValueError):
            request_delete(valid, "yes", ["takes/take-7/partial.mp4"])
        with self.assertRaises(ValueError):
            request_delete(valid, False, ["takes/missing.mp4"])
        kept = assess(valid)
        self.assertIn(PARTIAL, kept["preservedResults"])


if __name__ == "__main__":
    unittest.main()
