"""Host checks for the P017 resource-lifetime map. Not a physical S23 probe.

TC-P017-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p008_protocol import validate_handoff
from p017_model_camera_resource_ownership import (
    BASE_REVISION,
    CLOSE_ORDER,
    FIXTURE,
    METHOD,
    MUTANT,
    MUTANT_CLAIM,
    ORACLE,
    RESULT_KEYS,
    assess_ownership,
    failure_events,
    ownership_edges,
    release_plan,
    validate_map,
)


def load_map() -> dict:
    path = ROOT / "docs" / "P017_MODEL_CAMERA_RESOURCE_OWNERSHIP.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_handoff() -> dict:
    path = ROOT / "docs" / "evidence" / "P017-handoff.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _lease(lease_id, kind, generation, state, object_ref, depends_on):
    owner = {
        "camera_device": "application",
        "session": "application",
        "surface": "activity",
        "image": "application",
    }[kind]
    return {
        "id": lease_id,
        "kind": kind,
        "owner": owner,
        "generation": generation,
        "state": state,
        "objectRef": object_ref,
        "dependsOn": depends_on,
    }


def minimal(**overrides) -> dict:
    value = {
        "schemaVersion": 1,
        "phase": "P017",
        "mapId": "s23-resource-lifetime-fixture",
        "implementationBaseRevision": BASE_REVISION,
        "method": METHOD,
        "fixture": FIXTURE,
        "oracle": ORACLE,
        "mutant": MUTANT,
        "closeOrder": list(CLOSE_ORDER),
        "activityGeneration": 1,
        "reuseSurfaceBecauseNonNull": False,
        "callback": {
            "kind": "session",
            "generation": 1,
            "surfaceRef": "Surface#1",
            "success": True,
        },
        "leases": [
            _lease("camera-1", "camera_device", 1, "open", "CameraDevice#1", None),
            _lease("session-1", "session", 1, "open", "Session#1", "camera-1"),
            _lease("surface-1", "surface", 1, "open", "Surface#1", "session-1"),
            _lease("image-1", "image", 1, "open", "Image#1", "session-1"),
        ],
    }
    value.update(overrides)
    return value


class P017ResourceOwnershipTests(unittest.TestCase):
    def test_fixture_validates_method_fixture_oracle_and_mutant(self) -> None:
        raw = load_map()
        self.assertIsNone(validate_map(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P017")
        self.assertEqual(raw["mapId"], "s23-resource-lifetime-fixture")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["closeOrder"], list(CLOSE_ORDER))
        self.assertEqual(raw["activityGeneration"], 2)
        self.assertIs(raw["reuseSurfaceBecauseNonNull"], False)
        self.assertEqual(raw["callback"]["generation"], 1)
        self.assertEqual(raw["callback"]["surfaceRef"], "Surface#prev")
        self.assertIs(raw["callback"]["success"], True)
        prev = next(item for item in raw["leases"] if item["id"] == "surface-prev")
        active = next(item for item in raw["leases"] if item["id"] == "surface-active")
        self.assertEqual(prev["state"], "released")
        self.assertEqual(prev["objectRef"], "Surface#prev")
        self.assertEqual(prev["owner"], "activity")
        self.assertEqual(active["state"], "open")
        self.assertEqual(active["generation"], 2)
        self.assertEqual(active["owner"], "activity")
        camera = next(item for item in raw["leases"] if item["id"] == "camera-1")
        self.assertEqual(camera["owner"], "application")
        kinds = {item["kind"] for item in raw["leases"]}
        self.assertEqual(kinds, set(CLOSE_ORDER))

    def test_late_callback_keeps_active_preview_and_does_not_double_close(self) -> None:
        raw = load_map()
        result = assess_ownership(raw)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P017")
        self.assertEqual(result["decision"], "stale_ignored")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "reused"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            ["image-active", "surface-active", "session-active", "camera-1"],
        )
        self.assertIn("surface-active", result["preservedResults"])
        self.assertNotIn("surface-prev", result["preservedResults"])
        self.assertNotIn("image-stale", result["preservedResults"])
        self.assertNotIn("session-stale", result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("cannot attach to the new generation" in item for item in result["reasons"]))
        self.assertTrue(any("double-closed" in item for item in result["reasons"]))
        self.assertTrue(any("active preview remains valid" in item for item in result["reasons"]))
        self.assertTrue(result["openQuestions"])
        self.assertEqual(release_plan(raw), ["image-stale", "session-stale"])
        self.assertNotIn("surface-prev", release_plan(raw))
        self.assertNotIn("camera-1", release_plan(raw))
        self.assertEqual(
            failure_events(raw),
            [
                "stale_callback",
                "attach_refused",
                "double_close_refused",
                "released:image-stale",
                "released:session-stale",
                "preview_retained:surface-active",
            ],
        )

    def test_non_null_released_surface_is_not_reused(self) -> None:
        """Fails if a surface is reused solely because objectRef is non-null."""
        raw = load_map()
        prev = next(item for item in raw["leases"] if item["id"] == "surface-prev")
        self.assertTrue(prev["objectRef"])
        self.assertEqual(prev["state"], "released")
        result = assess_ownership(raw)
        self.assertNotEqual(result["decision"], "reused")
        self.assertNotIn("surface-prev", result["preservedResults"])
        self.assertIn("surface-active", result["preservedResults"])
        self.assertNotIn("reused_surface", failure_events(raw))
        flagged = copy.deepcopy(raw)
        flagged["reuseSurfaceBecauseNonNull"] = True
        refused = assess_ownership(flagged)
        self.assertEqual(refused["decision"], "rejected")
        self.assertNotIn(refused["decision"], {"qualified", "allowed"})
        self.assertEqual(refused["rejectedClaims"], [MUTANT_CLAIM])
        self.assertIn(MUTANT, refused["reasons"])
        self.assertEqual(refused["preservedResults"], result["preservedResults"])
        self.assertNotIn("surface-prev", refused["preservedResults"])
        self.assertIn("surface-active", refused["preservedResults"])
        self.assertEqual(failure_events(flagged)[0], "mutant_refused")
        self.assertEqual(release_plan(flagged), release_plan(raw))

    def test_close_order_is_reverse_dependency_and_camera_stays_if_needed(self) -> None:
        raw = load_map()
        edges = ownership_edges(raw)
        self.assertIn(
            {"child": "surface-active", "parent": "session-active", "kind": "surface", "owner": "activity"},
            edges,
        )
        self.assertTrue(all(item["owner"] == "application" or item["kind"] == "surface" for item in edges))
        plan = release_plan(raw)
        by_id = {item["id"]: item for item in raw["leases"]}
        rank = {kind: index for index, kind in enumerate(CLOSE_ORDER)}
        ranks = [rank[by_id[item]["kind"]] for item in plan]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(plan, ["image-stale", "session-stale"])
        self.assertLess(CLOSE_ORDER.index("image"), CLOSE_ORDER.index("session"))
        self.assertLess(CLOSE_ORDER.index("surface"), CLOSE_ORDER.index("session"))
        self.assertLess(CLOSE_ORDER.index("session"), CLOSE_ORDER.index("camera_device"))

    def test_current_generation_callback_retains_preview_without_release(self) -> None:
        result = assess_ownership(minimal())
        self.assertEqual(result["decision"], "preview_retained")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(
            result["preservedResults"],
            ["image-1", "surface-1", "session-1", "camera-1"],
        )
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(release_plan(minimal()), [])
        self.assertEqual(failure_events(minimal()), ["preview_retained:surface-1"])

    def test_matching_generation_failure_is_typed_and_preview_remains(self) -> None:
        document = minimal()
        document["callback"]["success"] = False
        result = assess_ownership(document)
        self.assertEqual(result["decision"], "failure_propagated")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("surface-1", result["preservedResults"])
        self.assertIn("capture_failure", failure_events(document))
        self.assertIn("preview_retained:surface-1", failure_events(document))

    def test_obsolete_surface_on_the_current_generation_is_rejected(self) -> None:
        raw = load_map()
        raw["callback"]["generation"] = 2
        raw["callback"]["surfaceRef"] = "Surface#prev"
        result = assess_ownership(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["obsolete-surface"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("surface-active", result["preservedResults"])
        self.assertNotIn("surface-prev", result["preservedResults"])
        self.assertNotIn("surface-prev", release_plan(raw))
        self.assertIn("double_close_refused", failure_events(raw))

    def test_unprotected_stale_camera_closes_after_its_children(self) -> None:
        document = minimal(activityGeneration=2)
        document["callback"] = {
            "kind": "session",
            "generation": 1,
            "surfaceRef": "Surface#old",
            "success": True,
        }
        document["leases"] = [
            _lease("camera-old", "camera_device", 1, "open", "CameraDevice#old", None),
            _lease("camera-new", "camera_device", 2, "open", "CameraDevice#new", None),
            _lease("session-old", "session", 1, "open", "Session#old", "camera-old"),
            _lease("session-new", "session", 2, "open", "Session#new", "camera-new"),
            _lease("surface-old", "surface", 1, "released", "Surface#old", "session-old"),
            _lease("surface-new", "surface", 2, "open", "Surface#new", "session-new"),
            _lease("image-old", "image", 1, "open", "Image#old", "session-old"),
            _lease("image-new", "image", 2, "open", "Image#new", "session-new"),
        ]
        self.assertIsNone(validate_map(document))
        self.assertEqual(
            release_plan(document),
            ["image-old", "session-old", "camera-old"],
        )
        result = assess_ownership(document)
        self.assertEqual(result["decision"], "stale_ignored")
        self.assertEqual(
            result["preservedResults"],
            ["image-new", "surface-new", "session-new", "camera-new"],
        )
        self.assertNotIn("camera-old", result["preservedResults"])
        self.assertIn("surface-new", result["preservedResults"])

    def test_handoff_is_blocked_without_a_commit(self) -> None:
        handoff = load_handoff()
        self.assertIsNone(validate_handoff(handoff))
        self.assertEqual(handoff["phase"], "P017")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["nextPhase"], "blocked")
        self.assertEqual(handoff["failures"], [])
        self.assertEqual(len(handoff["caseIds"]), 8)
        self.assertIn("physical S23 camera ownership", handoff["unverified"])
        self.assertTrue(handoff["testsRun"])

    def test_invalid_maps_raise(self) -> None:
        valid = load_map()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["callback"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P016"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        bad_order = copy.deepcopy(valid)
        bad_order["closeOrder"] = ["camera_device", "session", "surface", "image"]
        mutant_text = copy.deepcopy(valid)
        mutant_text["mutant"] = "reuse any non-null surface"
        independent = copy.deepcopy(valid)
        independent["leases"][0]["owner"] = "activity"
        double_ref = copy.deepcopy(valid)
        double_ref["leases"][1]["objectRef"] = "Surface#prev"
        released_parent = copy.deepcopy(valid)
        released_parent["leases"][0]["state"] = "released"
        released_parent["leases"][0]["objectRef"] = "CameraDevice#1"
        no_preview = copy.deepcopy(valid)
        no_preview["activityGeneration"] = 9
        bool_gen = copy.deepcopy(valid)
        bool_gen["activityGeneration"] = True
        reuse_flag = copy.deepcopy(valid)
        reuse_flag["reuseSurfaceBecauseNonNull"] = "true"
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            bad_order,
            mutant_text,
            independent,
            double_ref,
            released_parent,
            no_preview,
            bool_gen,
            reuse_flag,
            minimal(schemaVersion=1.0),
            minimal(callback={"kind": "image", "generation": 1, "surfaceRef": "Surface#1", "success": True}),
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_map(sample)


if __name__ == "__main__":
    unittest.main()
