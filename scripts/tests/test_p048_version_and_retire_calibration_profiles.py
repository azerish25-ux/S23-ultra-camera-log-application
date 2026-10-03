"""Host checks for the P048 profile lifecycle. Not a physical S23 probe.

TC-P048-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p048_version_and_retire_calibration_profiles import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    assess,
    compare,
    compatibility_key,
    content_digest,
    install_revision,
    rollback,
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
HASH_V1 = "ac3165c03a01dfcf1b091bee99e4e6bcc709bda10d6733c5b5daa1eaa7d9372c"
HASH_V2 = "3fd59652c44a1de85fa7a7a4cf97b1f96762dc6653e83e3f2ecc4bb4842d24bf"


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P048_VERSION_AND_RETIRE_CALIBRATION_PROFILES.json").read_text(
            encoding="utf-8"
        )
    )


def _replace_v1(document: dict, label: str) -> dict:
    mutant = copy.deepcopy(document)
    profile = next(item for item in mutant["profiles"] if item["versionId"] == "prof-v1")
    profile["bytesLabel"] = label
    profile["contentHash"] = content_digest(label)
    return mutant


class P048LifecycleTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P048")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P048")
        self.assertEqual(MAP_ID, "s23-profile-lifecycle-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("exact compatibility keys", METHOD)
        self.assertIn("never overwrite the provenance", METHOD)
        self.assertIn("rollback and comparison", METHOD)
        self.assertEqual(
            FIXTURE,
            "A user installs a newly measured profile and reopens a previously rendered take.",
        )
        self.assertEqual(
            ORACLE,
            "The earlier result remains reproducible while a new revision may be rendered and compared.",
        )
        self.assertEqual(
            MUTANT,
            "Replace all profile files in place while keeping the old version identifier.",
        )

    def test_fixture_reopens_archived_take_and_compares_new_revision(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P048")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["migrationPolicy"], "new-development-version")
        self.assertEqual(content_digest("bytes-v1"), HASH_V1)
        self.assertEqual(content_digest("bytes-v2"), HASH_V2)
        self.assertEqual(raw["sources"][0]["profileRef"], "prof-v1")
        self.assertNotEqual(raw["profiles"][0]["firmware"], raw["profiles"][1]["firmware"])
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "reproducible")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("recipe:export-archived:recipe-archived", result["preservedResults"])
        self.assertIn("recipe:export-revised:recipe-revised", result["preservedResults"])
        self.assertIn(f"export-hash:export-archived:{HASH_V1}", result["preservedResults"])
        self.assertIn(f"export-hash:export-revised:{HASH_V2}", result["preservedResults"])
        self.assertIn("comparison:prof-v1:prof-v2", result["preservedResults"])
        self.assertIn(
            "selected:take-archived:fw-1-0-0|logical0-main|prof-v1",
            result["preservedResults"],
        )
        self.assertNotIn(
            "selected:take-archived:fw-2-0-0|logical0-main|prof-v2",
            result["preservedResults"],
        )
        self.assertIn(ORACLE, result["reasons"])
        self.assertTrue(any("does not retarget take-archived" in item for item in result["reasons"]))

    def test_in_place_byte_replacement_is_rejected_and_keeps_recipe(self) -> None:
        raw = load_document()
        mutant = _replace_v1(raw, "bytes-replaced")
        self.assertEqual(mutant["profiles"][0]["versionId"], "prof-v1")
        self.assertNotEqual(mutant["profiles"][0]["contentHash"], HASH_V1)
        result = assess(mutant)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotEqual(result["decision"], "reproducible")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("same-identifier-byte-replacement:prof-v1", result["rejectedClaims"])
        self.assertIn("source-hash-drift:take-archived", result["rejectedClaims"])
        self.assertIn("recipe:export-archived:recipe-archived", result["preservedResults"])
        self.assertIn(f"export-hash:export-archived:{HASH_V1}", result["preservedResults"])
        self.assertIn("recipe:export-revised:recipe-revised", result["preservedResults"])
        self.assertTrue(any("prof-v2" in item for item in result["preservedResults"]))

    def test_replace_in_place_flag_rejects_the_mutant(self) -> None:
        raw = load_document()
        result = assess(raw, replace_in_place=True)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"][0], "in-place-version-identifier")
        self.assertIn(MUTANT, result["reasons"])
        self.assertIn("recipe:export-archived:recipe-archived", result["preservedResults"])
        self.assertIn(f"export-hash:export-archived:{HASH_V1}", result["preservedResults"])
        self.assertIn("comparison:prof-v1:prof-v2", result["preservedResults"])
        self.assertIn("policy:new-development-version", result["preservedResults"])

    def test_install_revision_does_not_overwrite_historical_export(self) -> None:
        raw = load_document()
        added = {
            "versionId": "prof-v3",
            "contentHash": content_digest("bytes-v3"),
            "firmware": "fw-2-0-0",
            "lensRoute": "logical0-wide",
            "status": "candidate",
            "bytesLabel": "bytes-v3",
        }
        revised = install_revision(raw, added)
        self.assertEqual(len(raw["profiles"]), 2)
        self.assertEqual(raw["exports"], revised["exports"])
        self.assertEqual(raw["sources"], revised["sources"])
        self.assertEqual(revised["profiles"][2]["versionId"], "prof-v3")
        result = assess(revised)
        self.assertEqual(result["decision"], "reproducible")
        self.assertIn("recipe:export-archived:recipe-archived", result["preservedResults"])
        self.assertIn(f"export-hash:export-archived:{HASH_V1}", result["preservedResults"])
        self.assertIn(
            "selected:take-archived:" + compatibility_key(raw["profiles"][0]),
            result["preservedResults"],
        )
        self.assertTrue(
            any("prof-v3" in item and "logical0-wide" in item for item in result["preservedResults"])
        )
        self.assertTrue(any("does not retarget take-archived" in item for item in result["reasons"]))

    def test_rollback_restores_previous_approved_profile(self) -> None:
        raw = load_document()
        promoted = copy.deepcopy(raw)
        promoted["profiles"][0]["status"] = "retired"
        promoted["profiles"][1]["status"] = "approved"
        exports_before = copy.deepcopy(promoted["exports"])
        sources_before = copy.deepcopy(promoted["sources"])
        rolled = rollback(promoted, "prof-v1")
        self.assertEqual(promoted["profiles"][0]["status"], "retired")
        self.assertEqual(promoted["profiles"][1]["status"], "approved")
        self.assertEqual(rolled["exports"], exports_before)
        self.assertEqual(rolled["sources"], sources_before)
        self.assertEqual(rolled["profiles"][0]["status"], "approved")
        self.assertEqual(rolled["profiles"][0]["bytesLabel"], "bytes-v1")
        self.assertEqual(rolled["profiles"][1]["status"], "retired")
        result = assess(rolled)
        self.assertEqual(result["decision"], "reproducible")
        self.assertIn("recipe:export-archived:recipe-archived", result["preservedResults"])
        self.assertIn(f"export-hash:export-archived:{HASH_V1}", result["preservedResults"])

    def test_compare_reports_distinct_bytes_without_rewriting(self) -> None:
        raw = load_document()
        before = copy.deepcopy(raw)
        report = compare(raw, "prof-v1", "prof-v2")
        self.assertEqual(raw, before)
        self.assertEqual(report["leftVersion"], "prof-v1")
        self.assertEqual(report["rightVersion"], "prof-v2")
        self.assertEqual(report["leftHash"], HASH_V1)
        self.assertEqual(report["rightHash"], HASH_V2)
        self.assertIs(report["bytesDiffer"], True)
        self.assertIs(report["firmwareDiffers"], True)
        self.assertIs(report["lensRouteDiffers"], False)
        self.assertNotIn("decision", report)

    def test_invalid_documents_and_flags_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P047"
        overwrite = copy.deepcopy(valid)
        overwrite["migrationPolicy"] = "overwrite-in-place"
        same_id = copy.deepcopy(valid)
        same_id["profiles"][1]["versionId"] = "prof-v1"
        drifted = copy.deepcopy(valid)
        drifted["profiles"][0]["contentHash"] = HASH_V2
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            overwrite,
            same_id,
            drifted,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, replace_in_place="true")
        with self.assertRaises(ValueError):
            rollback(valid, "prof-missing")
        with self.assertRaises(ValueError):
            compare(valid, "prof-v1", "prof-v1")
        with self.assertRaises(ValueError):
            install_revision(valid, copy.deepcopy(valid["profiles"][0]))


if __name__ == "__main__":
    unittest.main()
