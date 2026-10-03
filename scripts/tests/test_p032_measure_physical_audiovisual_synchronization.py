"""Host checks for the P032 physical audiovisual fixture. Not a physical S23 probe.

TC-P032-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p032_measure_physical_audiovisual_synchronization import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    assess,
    event_token,
    sound_travel_ns,
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
EVENTS = [
    "flash-begin@beginning:visible=1000000000:audible=1015000000:u=200000",
    "flash-middle@middle:visible=5000000000:audible=5015000000:u=200000",
    "flash-end@end:visible=10000000000:audible=10025000000:u=200000",
]
PHYSICAL = [
    "container:video=0:audio=0",
    *EVENTS,
    "sound-travel:10000000ns",
    "initial-offset:5000000ns",
    "end-offset:15000000ns",
    "drift:10000000ns",
]


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P032_MEASURE_PHYSICAL_AUDIOVISUAL_SYNCHRONIZATION.json").read_text(
            encoding="utf-8"
        )
    )


def flash(**overrides) -> dict:
    value = {
        "id": "flash-begin",
        "position": "beginning",
        "visibleNs": "1000000000",
        "audibleNs": "1010000000",
        "uncertaintyNs": "200000",
    }
    value.update(overrides)
    return value


class P032PhysicalSyncTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P032")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P032")
        self.assertEqual(MAP_ID, "s23-physical-av-sync-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("documented geometry", METHOD)
        self.assertIn("measurement uncertainty", METHOD)
        self.assertIn("fixed offset from drift", METHOD)
        self.assertIn("sound travel", METHOD)
        self.assertEqual(
            FIXTURE,
            "A flash-and-click recording with a constant offset at the beginning and increased "
            "offset near the end.",
        )
        self.assertEqual(
            ORACLE,
            "The report distinguishes initial synchronization error from drift and does not "
            "certify lip sync from container starts alone.",
        )
        self.assertEqual(
            MUTANT,
            "Use matching first packet timestamps as the sole synchronization test.",
        )

    def test_fixture_separates_initial_error_from_drift(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P032")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(sound_travel_ns("3400", "340000"), (10_000_000, 0))
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "sync_failed")
        self.assertEqual(
            result["rejectedClaims"],
            ["initial-sync-error", "drift", "container-start-lip-sync"],
        )
        self.assertEqual(result["preservedResults"], PHYSICAL)
        self.assertIn("flash-begin@beginning:visible=1000000000:audible=1015000000:u=200000",
                      result["preservedResults"])
        self.assertIn("container:video=0:audio=0", result["preservedResults"])
        self.assertNotIn("initial-offset:0ns", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(
            "initial synchronization error 5000000ns after sound travel 10000000ns",
            result["reasons"],
        )
        self.assertIn(
            "drift 10000000ns separates the end event from the initial error",
            result["reasons"],
        )
        self.assertIn("measurement uncertainty begin 200000ns end 200000ns", result["reasons"])
        self.assertIn("aligned container starts do not certify lip sync", result["reasons"])
        self.assertIn("physical sync gate failed", result["openQuestions"])
        self.assertTrue(any("does not qualify a physical S23" in item for item in result["reasons"]))
        self.assertNotIn(MUTANT, result["reasons"])

    def test_mutant_matching_first_packets_is_rejected(self) -> None:
        raw = load_document()
        self.assertEqual(raw["packetStarts"]["videoFirstNs"], raw["packetStarts"]["audioFirstNs"])
        result = assess(raw, sole_test="matching-first-packets")
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "sync_failed", "synced"})
        self.assertEqual(
            result["rejectedClaims"],
            [
                "matching-first-packet-timestamps",
                "initial-sync-error",
                "drift",
                "container-start-lip-sync",
            ],
        )
        self.assertEqual(result["preservedResults"], PHYSICAL)
        self.assertIn("initial-offset:5000000ns", result["preservedResults"])
        self.assertIn("drift:10000000ns", result["preservedResults"])
        self.assertNotIn("initial-offset:0ns", result["preservedResults"])
        self.assertNotIn("lip-sync:0ns", result["preservedResults"])
        self.assertIn(MUTANT, result["reasons"])
        self.assertIn(
            "drift 10000000ns separates the end event from the initial error",
            result["reasons"],
        )
        self.assertIn("packet-only synchronization was rejected", result["openQuestions"])
        joined = " ".join(result["preservedResults"])
        self.assertIn("flash-end@end", joined)
        self.assertNotIn("packet-delta:0", joined)

    def test_mutant_still_rejects_when_packets_differ_by_the_initial_error(self) -> None:
        raw = load_document()
        raw["packetStarts"]["audioFirstNs"] = "5000000"
        result = assess(raw, sole_test="matching-first-packets")
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("matching-first-packet-timestamps", result["rejectedClaims"])
        self.assertIn("drift", result["rejectedClaims"])
        self.assertIn("container:video=0:audio=5000000", result["preservedResults"])
        self.assertIn("drift:10000000ns", result["preservedResults"])
        self.assertIn("initial-offset:5000000ns", result["preservedResults"])
        self.assertNotIn("container-start-lip-sync", result["rejectedClaims"])
        self.assertIn("container timing stays distinct from the physical offset", result["reasons"])

    def test_within_uncertainty_is_withheld_not_certified(self) -> None:
        raw = load_document()
        raw["events"] = [
            flash(),
            flash(
                id="flash-middle",
                position="middle",
                visibleNs="5000000000",
                audibleNs="5010000000",
            ),
            flash(
                id="flash-end",
                position="end",
                visibleNs="10000000000",
                audibleNs="10010000000",
            ),
        ]
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["container-start-lip-sync"])
        self.assertIn("initial-offset:0ns", result["preservedResults"])
        self.assertIn("drift:0ns", result["preservedResults"])
        self.assertIn("sound-travel:10000000ns", result["preservedResults"])
        self.assertEqual(result["preservedResults"][1], event_token(raw["events"][0]))
        self.assertIn(
            "offsets are inside reported uncertainty; lip sync is still not certified",
            result["openQuestions"],
        )
        self.assertNotIn("physical sync gate failed", result["openQuestions"])

    def test_undocumented_distance_does_not_invent_a_corrected_offset(self) -> None:
        raw = load_document()
        raw["geometry"]["documented"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "sync_failed"})
        self.assertIn("sound-travel:unaccounted", result["preservedResults"])
        self.assertNotIn("initial-offset:5000000ns", result["preservedResults"])
        self.assertNotIn("drift:10000000ns", result["preservedResults"])
        self.assertTrue(all(event_token(item) in result["preservedResults"] for item in raw["events"]))
        self.assertIn("sound travel was not applied", result["openQuestions"])
        self.assertIn("container:video=0:audio=0", result["preservedResults"])

    def test_middle_disagreement_is_kept_with_the_end_drift(self) -> None:
        raw = load_document()
        raw["events"][1]["audibleNs"] = "5025000000"
        result = assess(raw)
        self.assertEqual(result["decision"], "sync_failed")
        self.assertIn("middle-drift", result["rejectedClaims"])
        self.assertIn("drift", result["rejectedClaims"])
        self.assertIn(
            "flash-middle@middle:visible=5000000000:audible=5025000000:u=200000",
            result["preservedResults"],
        )
        self.assertTrue(any("middle event flash-middle" in item for item in result["reasons"]))

    def test_sound_travel_remainder_is_reported_without_erasing_events(self) -> None:
        raw = load_document()
        raw["geometry"]["fixtureDistanceMm"] = "1"
        raw["geometry"]["speedOfSoundMmPerS"] = "343000"
        self.assertEqual(sound_travel_ns("1", "343000"), (2915, 155000))
        result = assess(raw)
        self.assert_result(result)
        self.assertIn("sound-travel:2915ns", result["preservedResults"])
        self.assertIn("sound-travel truncation remainder 155000ns", result["openQuestions"])
        self.assertTrue(all(token in result["preservedResults"] for token in (
            event_token(raw["events"][0]),
            event_token(raw["events"][1]),
            event_token(raw["events"][2]),
        )))
        self.assertIn("container:video=0:audio=0", result["preservedResults"])

    def test_invalid_documents_and_sole_test_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["events"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P031"
        wrong_revision = copy.deepcopy(valid)
        wrong_revision["implementationBaseRevision"] = "abc"
        numeric = copy.deepcopy(valid)
        numeric["events"][0]["visibleNs"] = 1000000000
        no_end = copy.deepcopy(valid)
        no_end["events"] = no_end["events"][:2]
        duplicate = copy.deepcopy(valid)
        duplicate["events"].append(copy.deepcopy(duplicate["events"][0]))
        undocumented_bool = copy.deepcopy(valid)
        undocumented_bool["geometry"]["documented"] = "true"
        schema_bool = copy.deepcopy(valid)
        schema_bool["schemaVersion"] = True
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            wrong_phase,
            wrong_revision,
            numeric,
            no_end,
            duplicate,
            undocumented_bool,
            schema_bool,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, sole_test="packet-only")


if __name__ == "__main__":
    unittest.main()
