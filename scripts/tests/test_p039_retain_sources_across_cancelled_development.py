"""Host checks for the P039 cancelled-development fixture. Not a physical S23 probe.

TC-P039-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p039_retain_sources_across_cancelled_development import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_POLICY,
    ORACLE,
    assess,
    content_hash,
    mutant_destination,
    profile_hash,
    simulate,
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
FRAMES = ["frame-0", "frame-1", "frame-2", "frame-3"]


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P039_RETAIN_SOURCES_ACROSS_CANCELLED_DEVELOPMENT.json").read_text(
            encoding="utf-8"
        )
    )


def document(**overrides) -> dict:
    source_hash = content_hash(FRAMES)
    value = {
        "schemaVersion": 1,
        "phase": "P039",
        "mapId": MAP_ID,
        "implementationBaseRevision": BASE_REVISION,
        "method": METHOD,
        "fixture": FIXTURE,
        "oracle": ORACLE,
        "mutant": MUTANT,
        "policy": "separate_destination",
        "source": {
            "id": "raw-take-1",
            "filename": "take.rawseq",
            "handle": "ro-take-1",
            "readOnly": True,
            "hashBefore": source_hash,
            "hashAfter": source_hash,
            "frames": list(FRAMES),
        },
        "profile": {
            "id": "profile-capture",
            "recipe": "recipe-a",
            "hash": profile_hash("recipe-a"),
        },
        "job": {
            "developedFrames": 2,
            "destination": "dev-cancel.mov",
            "temporary": "tmp-dev-cancel.part",
            "partialLabel": "incomplete",
            "leasesClosed": True,
            "progressRecorded": True,
        },
        "retry": {
            "restarted": True,
            "recipe": "recipe-b",
            "destination": "dev-retry-recipe-b.mov",
            "readsOriginalFrames": True,
            "frameIds": list(FRAMES),
        },
    }
    value.update(overrides)
    return value


def mutant_document() -> dict:
    sample = document()
    sample["policy"] = MUTANT_POLICY
    sample["job"]["destination"] = mutant_destination(sample["source"]["filename"])
    return sample


class P039RetainSourcesTests(unittest.TestCase):
    def assert_result(self, result: dict) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], CASE_ID)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertTrue(result["preservedResults"])

    def assert_inventory(self, result: dict, sample: dict) -> None:
        source = sample["source"]
        profile = sample["profile"]
        joined = result["preservedResults"]
        self.assertIn(
            f"source:{source['id']}:{source['filename']}:{source['hashBefore']}",
            joined,
        )
        self.assertIn(
            f"profile:{profile['id']}:{profile['recipe']}:{profile['hash']}",
            joined,
        )
        for frame in source["frames"]:
            self.assertIn(f"frame:{frame}", joined)
        self.assertIn(f"hashAfter:{source['hashAfter']}", joined)

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P039")
        self.assertIn("read-only source handles", METHOD)
        self.assertIn("content hashes", METHOD)
        self.assertIn("Cancellation halfway", FIXTURE)
        self.assertIn("another film recipe", FIXTURE)
        self.assertIn("source hash is unchanged", ORACLE)
        self.assertIn("labelled incomplete", ORACLE)
        self.assertIn("original frames", ORACLE)
        self.assertEqual(MUTANT, "Reuse the source filename as the destination of a developed movie.")
        self.assertEqual(mutant_destination("take.rawseq"), "take.rawseq")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")

    def test_fixture_retains_source_across_cancel_restart_and_retry(self) -> None:
        raw = load_document()
        frames = list(raw["source"]["frames"])
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P039")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["source"]["hashBefore"], content_hash(frames))
        self.assertEqual(raw["source"]["hashAfter"], raw["source"]["hashBefore"])
        self.assertEqual(raw["job"]["developedFrames"] * 2, len(frames))
        self.assertEqual(raw["job"]["partialLabel"], "incomplete")
        self.assertNotEqual(raw["job"]["destination"], raw["source"]["filename"])
        self.assertNotEqual(raw["job"]["temporary"], raw["source"]["filename"])
        self.assertNotEqual(raw["retry"]["recipe"], raw["profile"]["recipe"])
        self.assertEqual(raw["retry"]["frameIds"], frames)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "sources_retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assert_inventory(result, raw)
        self.assertEqual(raw["source"]["frames"], frames)
        self.assertTrue(any("unchanged" in item for item in result["reasons"]))
        self.assertTrue(any("incomplete" in item for item in result["reasons"]))
        self.assertTrue(any("original frames" in item for item in result["reasons"]))
        self.assertTrue(any("host fixture only" in item for item in result["openQuestions"]))

    def test_simulate_keeps_temporary_output_off_the_source(self) -> None:
        raw = load_document()
        before = copy.deepcopy(raw)
        observed = simulate(raw)
        self.assertEqual(raw, before)
        self.assertEqual(observed["frames"], FRAMES)
        self.assertEqual(observed["developed"], ["frame-0", "frame-1"])
        self.assertEqual(observed["retryFrames"], FRAMES)
        self.assertEqual(observed["partialLabel"], "incomplete")
        self.assertNotEqual(observed["destination"], observed["sourceFilename"])
        self.assertTrue(observed["temporary"])
        self.assertTrue(all(row["path"] != observed["sourceFilename"] for row in observed["temporary"]))
        self.assertEqual(observed["hashBefore"], observed["hashAfter"])

    def test_mutant_source_filename_destination_is_rejected(self) -> None:
        sample = mutant_document()
        frames = list(sample["source"]["frames"])
        result = assess(sample)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotEqual(result["decision"], "sources_retained")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("reuse-source-filename", result["rejectedClaims"])
        self.assertIn("source-overwrite", result["rejectedClaims"])
        self.assert_inventory(result, sample)
        self.assertEqual(sample["source"]["frames"], frames)
        self.assertTrue(any(item == MUTANT for item in result["reasons"]))
        self.assertIn(ORACLE, result["reasons"])

    def test_mutant_still_rejects_when_the_source_hash_changes(self) -> None:
        sample = mutant_document()
        sample["source"]["hashAfter"] = "f" * 64
        result = assess(sample)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotEqual(result["decision"], "sources_retained")
        self.assert_inventory(result, sample)
        self.assertIn(f"hashAfter:{'f' * 64}", result["preservedResults"])
        self.assertIn(
            f"source:raw-take-1:take.rawseq:{content_hash(FRAMES)}",
            result["preservedResults"],
        )

    def test_temporary_reuse_of_the_source_filename_is_rejected(self) -> None:
        sample = document()
        sample["job"]["temporary"] = sample["source"]["filename"]
        result = assess(sample)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("reuse-source-filename", result["rejectedClaims"])
        self.assert_inventory(result, sample)
        self.assertIn("frame:frame-0", result["preservedResults"])

    def test_changed_source_hash_is_rejected_without_wiping_frames(self) -> None:
        sample = document()
        sample["source"]["hashAfter"] = "ab" * 32
        result = assess(sample)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("source-hash-changed", result["rejectedClaims"])
        self.assert_inventory(result, sample)
        self.assertNotIn(result["decision"], {"qualified", "allowed", "sources_retained"})

    def test_not_halfway_is_withheld_and_keeps_the_inventory(self) -> None:
        sample = document()
        sample["job"]["developedFrames"] = 1
        result = assess(sample)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("not-halfway-cancellation", result["openQuestions"])
        self.assert_inventory(result, sample)
        self.assertEqual(result["rejectedClaims"], [])

    def test_retry_without_another_recipe_is_withheld(self) -> None:
        sample = document()
        sample["retry"]["recipe"] = "recipe-a"
        result = assess(sample)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("retry-recipe-unchanged", result["openQuestions"])
        self.assertIn("profile:profile-capture:recipe-a:" + profile_hash("recipe-a"), result["preservedResults"])

    def test_missing_restart_is_withheld(self) -> None:
        sample = document()
        sample["retry"]["restarted"] = False
        result = assess(sample)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("restart-not-recorded", result["openQuestions"])
        self.assert_inventory(result, sample)

    def test_unlabelled_partial_and_missed_retry_frames_are_rejected(self) -> None:
        partial = document()
        partial["job"]["partialLabel"] = "complete"
        partial_result = assess(partial)
        self.assertEqual(partial_result["decision"], "rejected")
        self.assertIn("partial-not-incomplete", partial_result["rejectedClaims"])
        self.assert_inventory(partial_result, partial)

        missed = document()
        missed["retry"]["readsOriginalFrames"] = False
        missed_result = assess(missed)
        self.assertEqual(missed_result["decision"], "rejected")
        self.assertIn("retry-missed-original-frames", missed_result["rejectedClaims"])
        for frame in FRAMES:
            self.assertIn(f"frame:{frame}", missed_result["preservedResults"])

    def test_open_lease_and_writable_handle_are_rejected(self) -> None:
        leased = document()
        leased["job"]["leasesClosed"] = False
        leased_result = assess(leased)
        self.assertEqual(leased_result["decision"], "rejected")
        self.assertIn("leases-left-open", leased_result["rejectedClaims"])
        self.assert_inventory(leased_result, leased)

        writable = document()
        writable["source"]["readOnly"] = False
        writable_result = assess(writable)
        self.assertEqual(writable_result["decision"], "rejected")
        self.assertIn("writable-source-handle", writable_result["rejectedClaims"])
        self.assertIn("frame:frame-3", writable_result["preservedResults"])

    def test_invalid_documents_raise(self) -> None:
        valid = document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["oracle"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P038"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        bad_hash = copy.deepcopy(valid)
        bad_hash["source"]["hashBefore"] = "ab" * 32
        bad_hash["source"]["hashAfter"] = "ab" * 32
        duplicate = copy.deepcopy(valid)
        duplicate["source"]["frames"] = ["frame-0", "frame-0", "frame-1", "frame-2"]
        schema = copy.deepcopy(valid)
        schema["schemaVersion"] = True
        overflow = copy.deepcopy(valid)
        overflow["job"]["developedFrames"] = 5
        mutant = mutant_document()
        mutant["job"]["destination"] = "dev-cancel.mov"
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            bad_hash,
            duplicate,
            schema,
            overflow,
            document(policy="overwrite"),
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(mutant)
        with self.assertRaises(ValueError):
            assess([])
        kept = assess(valid)
        self.assertEqual(kept["decision"], "sources_retained")


if __name__ == "__main__":
    unittest.main()
