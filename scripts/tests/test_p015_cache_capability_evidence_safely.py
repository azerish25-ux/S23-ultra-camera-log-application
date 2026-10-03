"""Host checks for the P015 capability cache. Not a physical S23 probe.

TC-P015-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p015_cache_capability_evidence_safely import (  # noqa: E402
    BASE_REVISION,
    CACHE_ID,
    FIXTURE,
    METHOD,
    MUTANT,
    ORACLE,
    assess_selection,
    cache_key,
    current_selection,
    mutant_key,
    mutant_selection,
    validate_cache,
    view_history,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
OLD_FP = "samsung/dm3q/dm3q:14/UP1A.231005.007/S918BXXU3BWJM:user/release-keys"
NEW_FP = "samsung/dm3q/dm3q:14/UP1A.231005.007/S918BXXU4CXA1:user/release-keys"
REAR = "hist-firmware-a-hevc-main10"
FRONT = "hist-front-jpeg-unaffected"
CANDIDATE = "sel-hevc-main10-rear"


def load_cache() -> dict:
    return json.loads(
        (ROOT / "docs" / "P015_CACHE_CAPABILITY_EVIDENCE_SAFELY.json").read_text(encoding="utf-8")
    )


def _align(record: dict, current: dict) -> None:
    for field in (
        "buildFingerprint",
        "appProtocolVersion",
        "codecIdentity",
        "codecCapabilityResponse",
        "marketingName",
    ):
        if field in record and record.get("route", current["route"]) == current["route"]:
            record[field] = current[field]


class P015CapabilityCacheTests(unittest.TestCase):
    def test_module_encodes_method_fixture_oracle_and_mutant(self) -> None:
        self.assertIn("build fingerprint", METHOD)
        self.assertIn("app protocol version", METHOD)
        self.assertIn("codec identity", METHOD)
        self.assertIn("historical", METHOD)
        self.assertIn("Revalidate stale candidates", METHOD)
        self.assertEqual(
            FIXTURE,
            "A firmware update with the same marketing phone name but a changed codec capability response.",
        )
        self.assertIn("old report remains inspectable", ORACLE)
        self.assertIn("refuses to certify", ORACLE)
        self.assertEqual(MUTANT, "Key the cache only by the string Galaxy S23 Ultra.")

    def test_fixture_is_a_same_name_firmware_update(self) -> None:
        raw = load_cache()
        self.assertIsNone(validate_cache(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P015")
        self.assertEqual(raw["cacheId"], CACHE_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["marketingName"], "Galaxy S23 Ultra")
        rear = raw["historical"][0]
        current = raw["currentEnvironment"]
        self.assertEqual(rear["reportId"], REAR)
        self.assertIs(rear["immutable"], True)
        self.assertEqual(rear["buildFingerprint"], OLD_FP)
        self.assertEqual(current["buildFingerprint"], NEW_FP)
        self.assertNotEqual(rear["buildFingerprint"], current["buildFingerprint"])
        self.assertEqual(rear["marketingName"], current["marketingName"])
        self.assertNotEqual(rear["codecCapabilityResponse"], current["codecCapabilityResponse"])
        self.assertEqual(rear["codecCapabilityResponse"], "Main10-surface-available")
        self.assertEqual(current["codecCapabilityResponse"], "Main10-surface-unavailable")
        self.assertEqual(raw["historical"][1]["reportId"], FRONT)
        self.assertEqual(raw["selectionCache"][0]["candidateId"], CANDIDATE)
        self.assertEqual(raw["selectionCache"][0]["sourceReportId"], REAR)

    def test_mutant_key_collides_and_real_key_does_not(self) -> None:
        raw = load_cache()
        rear = raw["historical"][0]
        current = raw["currentEnvironment"]
        self.assertEqual(mutant_key(rear), "Galaxy S23 Ultra")
        self.assertEqual(mutant_key(current), mutant_key(rear))
        self.assertNotEqual(cache_key(rear), cache_key(current))
        self.assertNotIn("Galaxy S23 Ultra", cache_key(rear))
        self.assertNotIn("Galaxy S23 Ultra", cache_key(current))
        self.assertIn("buildFingerprint=", cache_key(current))
        self.assertIn("appProtocolVersion=", cache_key(current))
        self.assertIn("route=", cache_key(current))
        self.assertIn("codecIdentity=", cache_key(current))
        mutant_would_reuse = mutant_key(rear) == mutant_key(current) and rear["previouslyWorking"]
        self.assertTrue(mutant_would_reuse)

    def test_old_report_stays_inspectable_while_planner_withholds(self) -> None:
        raw = load_cache()
        before = copy.deepcopy(raw)
        history = view_history(raw)
        result = assess_selection(raw)
        self.assertEqual(raw, before)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P015")
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "reused"})
        ids = [item["reportId"] for item in history]
        self.assertEqual(ids, [REAR, FRONT])
        self.assertTrue(all(item["immutable"] is True for item in history))
        self.assertTrue(all(item["currentCertification"] is False for item in history))
        self.assertEqual(result["preservedResults"], [REAR, FRONT])
        self.assertIn(REAR, result["preservedResults"])
        self.assertIn(FRONT, result["preservedResults"])
        self.assertEqual(current_selection(raw), [])
        self.assertEqual(mutant_selection(raw), [CANDIDATE])
        self.assertIn("stale-route-certification", result["rejectedClaims"])
        self.assertIn("marketing-name-cache-hit", result["rejectedClaims"])
        self.assertTrue(result["reasons"])
        joined = " ".join(result["reasons"])
        self.assertIn("old report remains inspectable", joined)
        self.assertIn("refuses to certify the changed route from stale data", joined)
        self.assertIn("previously working mode is unavailable", joined)
        self.assertIn("Main10-surface-available", joined)
        self.assertIn("Main10-surface-unavailable", joined)
        self.assertIn("Galaxy S23 Ultra does not bypass", joined)
        self.assertEqual(
            result["openQuestions"],
            ["requalification required before the changed route can be selected"],
        )

    def test_matching_environment_is_reused_without_qualification(self) -> None:
        raw = load_cache()
        current = raw["currentEnvironment"]
        for item in raw["historical"]:
            if item["route"] == current["route"]:
                _align(item, current)
        for item in raw["selectionCache"]:
            _align(item, current)
        self.assertEqual(cache_key(raw["historical"][0]), cache_key(current))
        result = assess_selection(raw)
        self.assertEqual(result["decision"], "reused")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], [REAR, FRONT])
        self.assertEqual(result["openQuestions"], [])
        self.assertTrue(any("not physical S23 qualification" in item for item in result["reasons"]))
        self.assertEqual(len(current_selection(raw)), 1)
        self.assertEqual(current_selection(raw)[0]["candidateId"], CANDIDATE)
        self.assertIs(current_selection(raw)[0]["certified"], False)
        history_ids = [item["reportId"] for item in view_history(raw)]
        self.assertNotIn(CANDIDATE, history_ids)

    def test_capability_response_change_is_revalidated_even_when_fingerprint_matches(self) -> None:
        raw = load_cache()
        current = raw["currentEnvironment"]
        raw["historical"][0]["buildFingerprint"] = current["buildFingerprint"]
        raw["selectionCache"][0]["buildFingerprint"] = current["buildFingerprint"]
        self.assertEqual(cache_key(raw["historical"][0]), cache_key(current))
        self.assertNotEqual(
            raw["historical"][0]["codecCapabilityResponse"],
            current["codecCapabilityResponse"],
        )
        result = assess_selection(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "reused"})
        self.assertEqual(current_selection(raw), [])
        self.assertIn(REAR, result["preservedResults"])
        self.assertIn(FRONT, result["preservedResults"])
        self.assertTrue(any("codec capability response changed" in item for item in result["reasons"]))
        self.assertTrue(any("previously working mode is unavailable" in item for item in result["reasons"]))

    def test_protocol_and_codec_software_changes_stay_withheld(self) -> None:
        for field, new_value in (
            ("appProtocolVersion", "capability-probe/2"),
            ("codecIdentity", "c2.exynos.hevc.encoder/2.0"),
        ):
            raw = load_cache()
            current = raw["currentEnvironment"]
            raw["historical"][0]["buildFingerprint"] = current["buildFingerprint"]
            raw["historical"][0]["codecCapabilityResponse"] = current["codecCapabilityResponse"]
            raw["selectionCache"][0]["buildFingerprint"] = current["buildFingerprint"]
            raw["selectionCache"][0]["codecCapabilityResponse"] = current["codecCapabilityResponse"]
            current[field] = new_value
            self.assertNotEqual(cache_key(raw["selectionCache"][0]), cache_key(current))
            self.assertEqual(mutant_key(raw["selectionCache"][0]), mutant_key(current))
            result = assess_selection(raw)
            self.assertEqual(result["decision"], "withheld")
            self.assertNotIn(result["decision"], {"qualified", "allowed", "reused"})
            self.assertIn("marketing-name-cache-hit", result["rejectedClaims"])
            self.assertIn(REAR, result["preservedResults"])
            self.assertIn(FRONT, result["preservedResults"])
            self.assertEqual(current_selection(raw), [])
            self.assertIn(CANDIDATE, mutant_selection(raw))

    def test_invalid_caches_raise(self) -> None:
        valid = load_cache()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["selectionCache"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P014"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        mutable = copy.deepcopy(valid)
        mutable["historical"][0]["immutable"] = False
        empty = copy.deepcopy(valid)
        empty["historical"] = []
        duplicate = copy.deepcopy(valid)
        duplicate["historical"][1]["reportId"] = REAR
        orphan = copy.deepcopy(valid)
        orphan["selectionCache"][0]["sourceReportId"] = "missing-report"
        renamed = copy.deepcopy(valid)
        renamed["currentEnvironment"]["marketingName"] = "Other Phone"
        bool_revision = copy.deepcopy(valid)
        bool_revision["schemaVersion"] = True
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            mutable,
            empty,
            duplicate,
            orphan,
            renamed,
            bool_revision,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_cache(sample)
                with self.assertRaises(ValueError):
                    assess_selection(sample)

    def test_note_and_handoff_are_host_scope(self) -> None:
        note = (ROOT / "docs" / "P015_CACHE_CAPABILITY_EVIDENCE_SAFELY.md").read_text(encoding="utf-8")
        self.assertIn("host fixture", note.lower())
        self.assertIn("python3 -m unittest discover -s scripts/tests -p 'test_p015*.py' -v", note)
        self.assertIn("Non-claims", note)
        self.assertIn("not a physical s23", note.lower())
        handoff = json.loads((ROOT / "docs" / "evidence" / "P015-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(
            list(handoff),
            [
                "phase",
                "caseIds",
                "changedFiles",
                "commit",
                "testsRun",
                "failures",
                "unverified",
                "nextPhase",
            ],
        )
        self.assertEqual(handoff["phase"], "P015")
        self.assertEqual(handoff["commit"], None)
        self.assertEqual(handoff["nextPhase"], "blocked")
        self.assertEqual(handoff["failures"], [])
        self.assertEqual(len(handoff["caseIds"]), 8)
        self.assertTrue(handoff["testsRun"])
        self.assertTrue(any("physical S23" in item for item in handoff["unverified"]))


if __name__ == "__main__":
    unittest.main()
