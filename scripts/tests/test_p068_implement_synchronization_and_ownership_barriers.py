"""Host checks for the P068 ownership barriers. Not a physical S23 probe.

TC-P068-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p068_implement_synchronization_and_ownership_barriers import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_PATH,
    ORACLE,
    assess,
    frame_faults,
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
SLOW = (
    "frame:slow-gpu:generation=1:lifetime=in-flight:submitted=true:fence=false:"
    "cancelled=true:partial=true:payload=slow-partial:reads=false:status=held"
)
NEXT_BLOCKED = (
    "frame:next-frame:generation=2:lifetime=in-flight:submitted=false:fence=false:"
    "cancelled=false:partial=false:payload=next-clean:reads=true:status=blocked"
)
NEXT_RECYCLED = (
    "frame:next-frame:generation=2:lifetime=in-flight:submitted=false:fence=false:"
    "cancelled=false:partial=false:payload=next-clean:reads=true:status=recycled"
)


def load_document() -> dict:
    path = ROOT / "docs" / "P068_IMPLEMENT_SYNCHRONIZATION_AND_OWNERSHIP_BARRIERS.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _completed_reuse() -> dict:
    raw = load_document()
    slow, nxt = raw["frames"]
    slow["fenceComplete"] = True
    slow["partialWrite"] = False
    slow["lifetime"] = "released"
    slow["payload"] = "slow-done"
    nxt["lifetime"] = "in-flight"
    return raw


class P068OwnershipBarrierTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P068")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-synchronization-ownership-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("frame identity and lifetime", METHOD)
        self.assertIn("verify completion before reuse or release", METHOD)
        self.assertIn("Separate correctness synchronization from performance measurements.", METHOD)
        self.assertEqual(
            FIXTURE,
            "A slow GPU frame followed by rapid cancellation and reuse of the same "
            "texture pool slot.",
        )
        self.assertEqual(
            ORACLE,
            "The next frame cannot read partially written or previous-generation "
            "data and cancellation releases only completed ownership.",
        )
        self.assertEqual(MUTANT, "Recycle a texture immediately after command submission.")

    def test_fixture_blocks_partial_and_previous_generation(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P068")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertIs(raw["synchronization"]["correctnessSeparated"], True)
        self.assertIs(raw["synchronization"]["performanceMeasured"], False)
        self.assertEqual(raw["synchronization"]["inFlightBound"], "2")
        self.assertEqual(frame_faults(raw), ["partial-read", "previous-generation"])
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["partial-read", "previous-generation"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "completion_verified", "ownership_held"})
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertIn(
            "cancellation of slow-gpu did not release incomplete ownership",
            result["reasons"],
        )
        self.assertIn("next-frame blocked on texture-pool-0: partial-read, previous-generation", result["reasons"])
        preserved = result["preservedResults"]
        self.assertIn("slot:texture-pool-0:kind=texture", preserved)
        self.assertIn("bound:2", preserved)
        self.assertIn("correctness-separated:true", preserved)
        self.assertIn("performance-measured:false", preserved)
        self.assertIn(SLOW, preserved)
        self.assertIn(NEXT_BLOCKED, preserved)

    def test_mutant_immediate_recycle_does_not_free_the_slot(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(mutant)
        self.assertEqual(honest["decision"], "rejected")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(
            mutant["rejectedClaims"],
            ["partial-read", "previous-generation", "immediate-recycle"],
        )
        self.assertNotIn(
            mutant["decision"],
            {"qualified", "allowed", "completion_verified", "ownership_held"},
        )
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("recycling immediately after command submission was rejected", mutant["reasons"])
        self.assertIn("mutant immediate recycle was rejected before reuse", mutant["openQuestions"])
        self.assertIn(SLOW, mutant["preservedResults"])
        self.assertIn(NEXT_RECYCLED, mutant["preservedResults"])
        self.assertIn("payload=slow-partial", " ".join(mutant["preservedResults"]))
        self.assertIn("payload=next-clean", " ".join(mutant["preservedResults"]))
        self.assertEqual(
            [item for item in honest["preservedResults"] if item.startswith("slot:")],
            [item for item in mutant["preservedResults"] if item.startswith("slot:")],
        )

    def test_completed_reuse_is_not_the_mutant(self) -> None:
        raw = _completed_reuse()
        typed = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(typed)
        self.assertEqual(typed["decision"], "completion_verified")
        self.assertEqual(typed["rejectedClaims"], [])
        self.assertNotIn(typed["decision"], {"qualified", "allowed"})
        self.assertIn("cancellation of slow-gpu released completed ownership", typed["reasons"])
        self.assertTrue(any(item.endswith("status=released") and "payload=slow-done" in item for item in typed["preservedResults"]))
        self.assertTrue(any(item.endswith("status=readable") and "payload=next-clean" in item for item in typed["preservedResults"]))
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["immediate-recycle"])
        self.assertTrue(any(item.endswith("status=recycled") for item in mutant["preservedResults"]))
        self.assertNotIn(mutant["decision"], {"completion_verified", "ownership_held", "qualified", "allowed"})

    def test_same_payload_after_completion_is_still_previous_generation(self) -> None:
        raw = _completed_reuse()
        raw["frames"][1]["payload"] = "slow-done"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["previous-generation"])
        self.assertIn("payload=slow-done", result["preservedResults"][4])
        self.assertIn("payload=slow-done", result["preservedResults"][5])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "completion_verified"})

    def test_performance_measurement_does_not_clear_the_fence(self) -> None:
        raw = load_document()
        raw["synchronization"]["performanceMeasured"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["partial-read", "previous-generation"])
        self.assertIn("performance-measured:true", result["preservedResults"])
        self.assertIn(SLOW, result["preservedResults"])
        self.assertIn("performance measurements do not authorize reuse", result["openQuestions"])

    def test_performance_substituted_for_a_fence_keeps_the_inventory(self) -> None:
        raw = load_document()
        raw["synchronization"]["correctnessSeparated"] = False
        raw["synchronization"]["performanceMeasured"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["performance-substituted", "partial-read", "previous-generation"],
        )
        self.assertIn("a performance measurement was substituted for a fence", result["reasons"])
        self.assertIn("correctness-separated:false", result["preservedResults"])
        self.assertIn(NEXT_BLOCKED, result["preservedResults"])

    def test_incomplete_release_and_unbounded_in_flight_stay_rejected(self) -> None:
        raw = load_document()
        raw["synchronization"]["inFlightBound"] = "1"
        raw["frames"][0]["lifetime"] = "released"
        raw["frames"][1]["readsSlot"] = False
        raw["frames"].append(
            {
                "frameId": "extra-frame",
                "generation": "3",
                "lifetime": "in-flight",
                "submitted": True,
                "fenceComplete": False,
                "cancelled": False,
                "partialWrite": False,
                "payload": "extra-clean",
                "readsSlot": False,
            }
        )
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["in-flight-unbounded", "incomplete-release"])
        self.assertIn("in-flight work exceeded the declared bound", result["reasons"])
        self.assertTrue(any("status=released-early" in item and "frame:slow-gpu:" in item for item in result["preservedResults"]))
        self.assertIn("payload=slow-partial", " ".join(result["preservedResults"]))
        self.assertIn("payload=next-clean", " ".join(result["preservedResults"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed", "ownership_held"})

    def test_cancelled_in_flight_without_a_reader_holds_ownership(self) -> None:
        raw = load_document()
        raw["frames"] = [raw["frames"][0]]
        result = assess(raw)
        self.assertEqual(result["decision"], "ownership_held")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(SLOW, result["preservedResults"])
        self.assertIn("ownership of texture-pool-0 stayed with the in-flight frame", result["reasons"])
        mutant = assess(raw, path=MUTANT_PATH)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["immediate-recycle"])
        self.assertIn(SLOW, mutant["preservedResults"])

    def test_no_submission_is_withheld_and_keeps_the_slot(self) -> None:
        raw = load_document()
        raw["frames"] = [raw["frames"][1]]
        raw["frames"][0]["generation"] = "1"
        raw["frames"][0]["readsSlot"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("slot:texture-pool-0:kind=texture", result["preservedResults"])
        self.assertIn("frame:next-frame:generation=1:lifetime=in-flight:submitted=false:fence=false:cancelled=false:partial=false:payload=next-clean:reads=false:status=recorded", result["preservedResults"])

    def test_repeat_sites_cancellation_and_buffer_are_separate(self) -> None:
        cancelled = load_document()
        cancelled["frames"][1]["readsSlot"] = False
        held = assess(cancelled)
        self.assertEqual(held["decision"], "ownership_held")
        buffer_doc = load_document()
        buffer_doc["pool"]["kind"] = "buffer"
        buffer_doc["pool"]["slotId"] = "buffer-pool-0"
        blocked = assess(buffer_doc)
        self.assertEqual(blocked["decision"], "rejected")
        self.assertEqual(blocked["rejectedClaims"], ["partial-read", "previous-generation"])
        self.assertIn("slot:buffer-pool-0:kind=buffer", blocked["preservedResults"])
        self.assertIn("next-frame blocked on buffer-pool-0: partial-read, previous-generation", blocked["reasons"])

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P067"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        string_flag = copy.deepcopy(valid)
        string_flag["synchronization"]["correctnessSeparated"] = "true"
        bad_bound = copy.deepcopy(valid)
        bad_bound["synchronization"]["inFlightBound"] = "02"
        zero_bound = copy.deepcopy(valid)
        zero_bound["synchronization"]["inFlightBound"] = "0"
        bad_kind = copy.deepcopy(valid)
        bad_kind["pool"]["kind"] = "image"
        duplicate = copy.deepcopy(valid)
        duplicate["frames"].append(copy.deepcopy(duplicate["frames"][0]))
        same_generation = copy.deepcopy(valid)
        same_generation["frames"][1]["generation"] = "1"
        decreasing = copy.deepcopy(valid)
        decreasing["frames"][0]["generation"] = "2"
        decreasing["frames"][1]["generation"] = "1"
        early_fence = copy.deepcopy(valid)
        early_fence["frames"][1]["fenceComplete"] = True
        empty_frames = copy.deepcopy(valid)
        empty_frames["frames"] = []
        bad_life = copy.deepcopy(valid)
        bad_life["frames"][0]["lifetime"] = "free"
        bad_payload = copy.deepcopy(valid)
        bad_payload["frames"][0]["payload"] = "Slow"
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            string_flag,
            bad_bound,
            zero_bound,
            bad_kind,
            duplicate,
            same_generation,
            decreasing,
            early_fence,
            empty_frames,
            bad_life,
            bad_payload,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, path="qualified")
        with self.assertRaises(ValueError):
            assess(valid, path="allowed")


if __name__ == "__main__":
    unittest.main()
