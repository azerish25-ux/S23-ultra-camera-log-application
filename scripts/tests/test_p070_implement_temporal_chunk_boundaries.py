"""Host checks for P070 temporal chunk boundaries. Not a physical S23 probe.

TC-P070-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p070_implement_temporal_chunk_boundaries import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_PATH,
    ORACLE,
    assess,
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
NODE_LINE = (
    "node:temporal-denoise:history=4:lookahead=2:checkpoint=true:cache-bound=true:"
    "source=focus-pull-source:model=temporal-model-a:graph=deferred-export:algorithm=overlap-trim-a"
)


def load_document() -> dict:
    path = ROOT / "docs" / "P070_IMPLEMENT_TEMPORAL_CHUNK_BOUNDARIES.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P070TemporalChunkBoundaryTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P070")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-temporal-chunk-boundaries-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("history and lookahead", METHOD)
        self.assertIn("overlap frames", METHOD)
        self.assertIn("Scene cuts invalidate appropriate history", METHOD)
        self.assertEqual(
            FIXTURE,
            "A subject crossing a chunk boundary during a focus pull with a process restart at the boundary.",
        )
        self.assertEqual(
            ORACLE,
            "The resumed output preserves temporal continuity within the declared tolerance and exact frame count.",
        )
        self.assertEqual(MUTANT, "Restart the temporal model from an empty state at every export chunk.")

    def test_fixture_preserves_continuity_and_exact_frame_count(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P070")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["subject"], "focus-pull-subject")
        self.assertIs(raw["focusPull"], True)
        self.assertIs(raw["boundaryCrossed"], True)
        self.assertIs(raw["resumed"]["restartAtBoundary"], True)
        self.assertIs(raw["resumed"]["emptyState"], False)
        self.assertIs(raw["resumed"]["checkpointLoaded"], True)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "continuity_preserved")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertIn("resumed continuity 0.006 is within tolerance 0.01", result["reasons"])
        self.assertIn("resumed frame count 8 matches expected 8", result["reasons"])
        self.assertIn("overlap frames were not duplicated in the final output", result["reasons"])
        preserved = result["preservedResults"]
        self.assertIn(
            "subject:focus-pull-subject:focus-pull=true:boundary-crossed=true",
            preserved,
        )
        self.assertIn(
            "identity:source=focus-pull-source:model=temporal-model-a:"
            "graph=deferred-export:algorithm=overlap-trim-a",
            preserved,
        )
        self.assertIn("tolerance:0.01", preserved)
        self.assertIn("expected-frame-count:8", preserved)
        self.assertIn(NODE_LINE, preserved)
        self.assertIn(
            "chunk:chunk-0:start=0:end=4:overlap-in=0:overlap-out=2:scene-cut=false:"
            "history-invalidated=false:emitted=0,1,2,3:overlap=4,5:delta=0.002",
            preserved,
        )
        self.assertIn(
            "chunk:chunk-1:start=4:end=8:overlap-in=2:overlap-out=0:scene-cut=false:"
            "history-invalidated=false:emitted=4,5,6,7:overlap=2,3:delta=0.004",
            preserved,
        )
        self.assertIn(
            "run:uninterrupted:frames=8:delta=0.003:duplicates=none:checkpoint=false:empty=false",
            preserved,
        )
        self.assertIn(
            "run:resumed:frames=8:delta=0.006:duplicates=none:checkpoint=true:empty=false:restart=true",
            preserved,
        )

    def test_mutant_empty_restart_is_rejected_and_keeps_the_inventory(self) -> None:
        """Fails if an empty-state restart at every chunk is treated as success."""
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(mutant)
        self.assertEqual(honest["decision"], "continuity_preserved")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["empty-state-restart"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "continuity_preserved"})
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn(
            "empty-state restart at every export chunk discards checkpointed history",
            mutant["reasons"],
        )
        self.assertIn("mutant empty-state restart was rejected", mutant["openQuestions"])
        self.assertEqual(mutant["preservedResults"], honest["preservedResults"])
        self.assertIn(NODE_LINE, mutant["preservedResults"])
        self.assertIn(
            "chunk:chunk-0:start=0:end=4:overlap-in=0:overlap-out=2:scene-cut=false:"
            "history-invalidated=false:emitted=0,1,2,3:overlap=4,5:delta=0.002",
            mutant["preservedResults"],
        )
        self.assertIn("checkpoint=true", mutant["preservedResults"][-1])
        self.assertNotIn("empty=true", " ".join(mutant["preservedResults"]))

    def test_recorded_empty_state_fails_on_the_checkpointed_path(self) -> None:
        raw = load_document()
        raw["resumed"]["emptyState"] = True
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["empty-state-restart"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "continuity_preserved"})
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertIn("resumed run restarted the temporal model from an empty state", result["reasons"])
        self.assertIn(
            "run:resumed:frames=8:delta=0.006:duplicates=none:checkpoint=true:empty=true:restart=true",
            result["preservedResults"],
        )
        self.assertIn(NODE_LINE, result["preservedResults"])

    def test_overlap_duplicated_in_final_output_keeps_both_chunks(self) -> None:
        raw = load_document()
        raw["chunks"][0]["emittedFrames"].append("4")
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            [
                "overlap-emitted",
                "emitted-outside-owned-range",
                "duplicate-output-frame",
                "frame-count-mismatch",
            ],
        )
        self.assertNotIn(result["decision"], {"qualified", "allowed", "continuity_preserved"})
        preserved = result["preservedResults"]
        self.assertIn(
            "chunk:chunk-0:start=0:end=4:overlap-in=0:overlap-out=2:scene-cut=false:"
            "history-invalidated=false:emitted=0,1,2,3,4:overlap=4,5:delta=0.002",
            preserved,
        )
        self.assertIn(
            "chunk:chunk-1:start=4:end=8:overlap-in=2:overlap-out=0:scene-cut=false:"
            "history-invalidated=false:emitted=4,5,6,7:overlap=2,3:delta=0.004",
            preserved,
        )

    def test_scene_cut_must_invalidate_history_and_a_real_cut_can_still_pass(self) -> None:
        kept = load_document()
        kept["chunks"][1]["sceneCut"] = True
        rejected = assess(kept)
        self.assertEqual(rejected["decision"], "rejected")
        self.assertEqual(rejected["rejectedClaims"], ["scene-cut-history-kept"])
        self.assertIn("chunk chunk-1 scene cut did not invalidate history", rejected["reasons"])
        self.assertIn("history-invalidated=false", " ".join(rejected["preservedResults"]))
        self.assertIn("emitted=4,5,6,7", " ".join(rejected["preservedResults"]))

        cleared = load_document()
        cleared["chunks"][1]["sceneCut"] = True
        cleared["chunks"][1]["historyInvalidated"] = True
        accepted = assess(cleared)
        self.assertEqual(accepted["decision"], "continuity_preserved")
        self.assertEqual(accepted["rejectedClaims"], [])
        self.assertIn(
            "chunk:chunk-1:start=4:end=8:overlap-in=2:overlap-out=0:scene-cut=true:"
            "history-invalidated=true:emitted=4,5,6,7:overlap=2,3:delta=0.004",
            accepted["preservedResults"],
        )

    def test_history_cleared_without_a_scene_cut_is_rejected(self) -> None:
        raw = load_document()
        raw["chunks"][1]["historyInvalidated"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["history-cleared-without-cut"])
        self.assertIn("chunk chunk-1 invalidated history without a scene cut", result["reasons"])
        self.assertIn("scene-cut=false", " ".join(result["preservedResults"]))
        self.assertIn(NODE_LINE, result["preservedResults"])

    def test_cache_must_stay_bound_to_the_four_identities(self) -> None:
        unbound = load_document()
        unbound["nodes"][0]["cacheBound"] = False
        unbound_result = assess(unbound)
        self.assertEqual(unbound_result["decision"], "rejected")
        self.assertEqual(unbound_result["rejectedClaims"], ["unbound-cache"])
        self.assertIn("cache-bound=false", " ".join(unbound_result["preservedResults"]))
        self.assertIn("model=temporal-model-a", " ".join(unbound_result["preservedResults"]))

        mismatched = load_document()
        mismatched["nodes"][0]["cache"]["modelId"] = "temporal-model-b"
        mismatched_result = assess(mismatched)
        self.assertEqual(mismatched_result["decision"], "rejected")
        self.assertEqual(mismatched_result["rejectedClaims"], ["cache-identity-mismatch"])
        self.assertIn(
            "node:temporal-denoise:history=4:lookahead=2:checkpoint=true:cache-bound=true:"
            "source=focus-pull-source:model=temporal-model-b:graph=deferred-export:algorithm=overlap-trim-a",
            mismatched_result["preservedResults"],
        )
        self.assertIn(
            "identity:source=focus-pull-source:model=temporal-model-a:"
            "graph=deferred-export:algorithm=overlap-trim-a",
            mismatched_result["preservedResults"],
        )
        self.assertNotIn(mismatched_result["decision"], {"qualified", "allowed", "continuity_preserved"})

    def test_short_lookahead_missing_checkpoint_and_continuity_budget(self) -> None:
        short = load_document()
        short["nodes"][0]["lookahead"] = "1"
        short_result = assess(short)
        self.assertEqual(short_result["rejectedClaims"], ["lookahead-short"])
        self.assertIn("lookahead=1", " ".join(short_result["preservedResults"]))
        self.assertIn("overlap-out=2", " ".join(short_result["preservedResults"]))

        blank = load_document()
        blank["nodes"][0]["checkpoint"] = False
        blank_result = assess(blank)
        self.assertEqual(blank_result["rejectedClaims"], ["missing-checkpoint"])
        self.assertIn("checkpoint=false", blank_result["preservedResults"][4])

        over = load_document()
        over["chunks"][0]["continuityDelta"] = "0.02"
        over_result = assess(over)
        self.assertEqual(over_result["rejectedClaims"], ["chunk-continuity"])
        self.assertIn("delta=0.02", " ".join(over_result["preservedResults"]))
        self.assertIn("emitted=0,1,2,3", " ".join(over_result["preservedResults"]))

    def test_frame_count_and_resumed_budget_failures_keep_frames(self) -> None:
        dropped = load_document()
        dropped["chunks"][1]["emittedFrames"] = ["4", "5", "6"]
        dropped_result = assess(dropped)
        self.assertEqual(dropped_result["decision"], "rejected")
        self.assertEqual(dropped_result["rejectedClaims"], ["frame-count-mismatch"])
        self.assertIn("emitted=4,5,6", " ".join(dropped_result["preservedResults"]))
        self.assertIn("emitted=0,1,2,3", " ".join(dropped_result["preservedResults"]))

        recounted = load_document()
        recounted["resumed"]["frameCount"] = "9"
        recounted_result = assess(recounted)
        self.assertEqual(recounted_result["rejectedClaims"], ["resumed-frame-count"])
        self.assertIn(
            "run:resumed:frames=9:delta=0.006:duplicates=none:checkpoint=true:empty=false:restart=true",
            recounted_result["preservedResults"],
        )

        loose = load_document()
        loose["resumed"]["continuityDelta"] = "0.2"
        loose_result = assess(loose)
        self.assertEqual(loose_result["rejectedClaims"], ["resumed-continuity"])
        self.assertIn("delta=0.2", loose_result["preservedResults"][-1])

        unloaded = load_document()
        unloaded["resumed"]["checkpointLoaded"] = False
        unloaded_result = assess(unloaded)
        self.assertEqual(unloaded_result["rejectedClaims"], ["checkpoint-not-loaded"])
        self.assertIn("checkpoint=false", unloaded_result["preservedResults"][-1])

    def test_owned_range_and_duplicate_run_report(self) -> None:
        outside = load_document()
        outside["chunks"][0]["endFrame"] = "3"
        outside_result = assess(outside)
        self.assertEqual(outside_result["rejectedClaims"], ["emitted-outside-owned-range"])
        self.assertIn("end=3", " ".join(outside_result["preservedResults"]))
        self.assertIn("emitted=0,1,2,3", " ".join(outside_result["preservedResults"]))

        dup = load_document()
        dup["resumed"]["duplicateFrames"] = ["4"]
        dup_result = assess(dup)
        self.assertEqual(dup_result["rejectedClaims"], ["resumed-duplicates"])
        self.assertIn("duplicates=4", dup_result["preservedResults"][-1])
        self.assertIn("emitted=4,5,6,7", " ".join(dup_result["preservedResults"]))

    def test_incomplete_restart_scenario_is_withheld_and_keeps_chunks(self) -> None:
        cases = (
            ("focusPull", False, "focus pull was not recorded"),
            ("boundaryCrossed", False, "chunk boundary crossing was not recorded"),
        )
        for key, value, question in cases:
            raw = load_document()
            raw[key] = value
            result = assess(raw)
            with self.subTest(key=key):
                self.assertEqual(result["decision"], "withheld")
                self.assertEqual(result["rejectedClaims"], [])
                self.assertIn(question, result["openQuestions"])
                self.assertIn(NODE_LINE, result["preservedResults"])
                self.assertIn("emitted=0,1,2,3", " ".join(result["preservedResults"]))
                self.assertNotIn(result["decision"], {"qualified", "allowed", "continuity_preserved"})
        raw = load_document()
        raw["resumed"]["restartAtBoundary"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("process restart at the boundary was not recorded", result["openQuestions"])
        self.assertIn("restart=false", result["preservedResults"][-1])
        self.assertIn("emitted=4,5,6,7", " ".join(result["preservedResults"]))

    def test_empty_temporal_window_reports_short_history_and_lookahead(self) -> None:
        raw = load_document()
        raw["nodes"][0]["history"] = "0"
        raw["nodes"][0]["lookahead"] = "0"
        result = assess(raw)
        self.assertEqual(
            result["rejectedClaims"],
            ["empty-temporal-window", "lookahead-short", "history-short"],
        )
        self.assertIn("history=0", " ".join(result["preservedResults"]))
        self.assertIn("lookahead=0", " ".join(result["preservedResults"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed", "continuity_preserved"})

    def test_mutant_still_rejects_when_the_scenario_is_incomplete(self) -> None:
        raw = load_document()
        raw["focusPull"] = False
        result = assess(raw, path=MUTANT_PATH)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["empty-state-restart"])
        self.assertIn("focus-pull=false", result["preservedResults"][0])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "continuity_preserved", "withheld"})

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P069"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        bad_method = copy.deepcopy(valid)
        bad_method["method"] = "Restart from an empty state."
        bad_tolerance = copy.deepcopy(valid)
        bad_tolerance["tolerance"] = "0"
        trailing = copy.deepcopy(valid)
        trailing["tolerance"] = "0.010"
        bad_count = copy.deepcopy(valid)
        bad_count["expectedFrameCount"] = "08"
        string_flag = copy.deepcopy(valid)
        string_flag["focusPull"] = "true"
        empty_nodes = copy.deepcopy(valid)
        empty_nodes["nodes"] = []
        empty_chunks = copy.deepcopy(valid)
        empty_chunks["chunks"] = []
        duplicate = copy.deepcopy(valid)
        duplicate["nodes"].append(copy.deepcopy(duplicate["nodes"][0]))
        bad_history = copy.deepcopy(valid)
        bad_history["nodes"][0]["history"] = "04"
        outside_overlap = copy.deepcopy(valid)
        outside_overlap["chunks"][0]["overlapFrames"] = ["4"]
        equal_range = copy.deepcopy(valid)
        equal_range["chunks"][0]["endFrame"] = "0"
        extra_resume = copy.deepcopy(valid)
        extra_resume["uninterrupted"]["restartAtBoundary"] = True
        unsorted = copy.deepcopy(valid)
        unsorted["chunks"][0]["emittedFrames"] = ["0", "2", "1", "3"]
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            bad_method,
            bad_tolerance,
            trailing,
            bad_count,
            string_flag,
            empty_nodes,
            empty_chunks,
            duplicate,
            bad_history,
            outside_overlap,
            equal_range,
            extra_resume,
            unsorted,
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
