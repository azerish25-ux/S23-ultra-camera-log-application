"""Host checks for the P065 typed render graph. Not a physical S23 probe.

TC-P065-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p065_define_a_typed_render_graph import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_PATH,
    ORACLE,
    assess,
    edge_faults,
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


def load_document() -> dict:
    path = ROOT / "docs" / "P065_DEFINE_A_TYPED_RENDER_GRAPH.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _edge(document: dict, edge_id: str) -> str:
    return next(item for item in document if item.startswith(f"edge:{edge_id}:"))


class P065TypedRenderGraphTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P065")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-typed-render-graph-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("precision requirements", METHOD)
        self.assertIn("before allocation", METHOD)
        self.assertIn("alter geometry, exposure, color, texture, or time", METHOD)
        self.assertEqual(
            FIXTURE,
            "A film-density node connected directly to an encoded YUV surface and a "
            "display overlay connected to clean-master export.",
        )
        self.assertEqual(
            ORACLE,
            "The graph validator rejects both invalid connections before processing frames.",
        )
        self.assertEqual(MUTANT, "Represent all intermediate images as untyped texture handles.")

    def test_fixture_rejects_both_invalid_connections_before_frames(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P065")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertIs(raw["validation"]["framesProcessed"], False)
        self.assertIs(raw["validation"]["allocated"], False)
        faults = {edge["id"]: edge_faults(raw, edge) for edge in raw["edges"]}
        self.assertEqual(faults["working-to-density"], [])
        self.assertEqual(faults["density-to-yuv"], ["domain-mismatch", "precision-mismatch"])
        self.assertEqual(
            faults["overlay-to-master"],
            ["domain-mismatch", "precision-mismatch", "geometry-mismatch"],
        )
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["density-to-yuv", "overlay-to-master"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "edges_validated"})
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertIn("both invalid connections were rejected before processing frames", result["reasons"])
        preserved = result["preservedResults"]
        self.assertIn(
            "node:film-density:precision=rgba16f:halo=2:temporal=none:deterministic=true:"
            "parameters=density-curve:alters=color,exposure,texture",
            preserved,
        )
        self.assertIn(
            "port:film-density:density:domain=film-density:precision=rgba16f:geometry=image-plane",
            preserved,
        )
        self.assertIn(
            "port:encoded-yuv-surface:encoded:domain=encoded-yuv:precision=yuv420:geometry=image-plane",
            preserved,
        )
        self.assertIn(
            "port:display-overlay:overlay:domain=display-overlay:precision=rgba8:geometry=overlay-plane",
            preserved,
        )
        self.assertIn(
            "port:clean-master-export:master:domain=clean-master:precision=rgba16f:geometry=export-plane",
            preserved,
        )
        self.assertIn("status=compatible", _edge(preserved, "working-to-density"))
        self.assertIn("status=rejected", _edge(preserved, "density-to-yuv"))
        self.assertIn("status=rejected", _edge(preserved, "overlay-to-master"))
        self.assertIn("frames-processed:false", preserved)
        self.assertIn("allocated:false", preserved)
        self.assertIn("stage:before-allocation", preserved)
        self.assertIn("node:scene-linear-source:precision=rgba16f:halo=2:temporal=none:deterministic=true:parameters=identity:alters=color", preserved)

    def test_mutant_untyped_handles_do_not_accept_invalid_edges(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(mutant)
        self.assertEqual(honest["decision"], "rejected")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(
            mutant["rejectedClaims"],
            ["density-to-yuv", "overlay-to-master", "untyped-texture-handles"],
        )
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "edges_validated"})
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("untyped texture handles do not make incompatible domains connect", mutant["reasons"])
        self.assertIn("mutant untyped handles were rejected before allocation", mutant["openQuestions"])
        self.assertIn("status=rejected", _edge(mutant["preservedResults"], "density-to-yuv"))
        self.assertIn("status=rejected", _edge(mutant["preservedResults"], "overlay-to-master"))
        self.assertIn("status=compatible", _edge(mutant["preservedResults"], "working-to-density"))
        self.assertIn(
            "port:film-density:density:domain=film-density:precision=rgba16f:geometry=image-plane",
            mutant["preservedResults"],
        )
        joined = " ".join(mutant["preservedResults"])
        self.assertNotIn("domain=untyped", joined)
        self.assertNotIn("precision=untyped", joined)
        self.assertEqual(
            [item for item in honest["preservedResults"] if item.startswith("port:")],
            [item for item in mutant["preservedResults"] if item.startswith("port:")],
        )

    def test_typed_compatible_graph_is_not_the_mutant(self) -> None:
        raw = load_document()
        raw["edges"] = [edge for edge in raw["edges"] if edge["id"] == "working-to-density"]
        typed = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(typed)
        self.assertEqual(typed["decision"], "edges_validated")
        self.assertEqual(typed["rejectedClaims"], [])
        self.assertNotIn(typed["decision"], {"qualified", "allowed"})
        self.assertIn("status=compatible", _edge(typed["preservedResults"], "working-to-density"))
        self.assertIn("node:film-density:precision=rgba16f:halo=2:temporal=none:deterministic=true:parameters=density-curve:alters=color,exposure,texture", typed["preservedResults"])
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["untyped-texture-handles"])
        self.assertIn("status=compatible", _edge(mutant["preservedResults"], "working-to-density"))
        self.assertNotIn(mutant["decision"], {"edges_validated", "qualified", "allowed"})

    def test_untyped_ports_stay_rejected_on_the_typed_path(self) -> None:
        raw = load_document()
        raw["edges"] = [edge for edge in raw["edges"] if edge["id"] == "working-to-density"]
        for node in raw["nodes"]:
            if node["id"] in {"scene-linear-source", "film-density"}:
                node["precisionRequirement"] = "untyped"
                for port in node["inputs"] + node["outputs"]:
                    port["domain"] = "untyped"
                    port["precision"] = "untyped"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["working-to-density"])
        self.assertIn("working-to-density rejected: untyped-port, domain-mismatch, precision-mismatch", result["reasons"])
        self.assertIn(
            "port:scene-linear-source:working:domain=untyped:precision=untyped:geometry=image-plane",
            result["preservedResults"],
        )
        self.assertNotIn(result["decision"], {"qualified", "allowed", "edges_validated"})

    def test_halo_temporal_and_nondeterministic_faults_keep_the_inventory(self) -> None:
        raw = load_document()
        raw["edges"] = [edge for edge in raw["edges"] if edge["id"] == "working-to-density"]
        source = next(node for node in raw["nodes"] if node["id"] == "scene-linear-source")
        source["halo"] = "0"
        source["temporal"] = "history"
        source["deterministic"] = False
        source["parameters"] = []
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["working-to-density"])
        self.assertIn(
            "working-to-density rejected: halo-short, temporal-mismatch, nondeterministic",
            result["reasons"],
        )
        self.assertIn(
            "node:scene-linear-source:precision=rgba16f:halo=0:temporal=history:deterministic=false:parameters=none:alters=color",
            result["preservedResults"],
        )
        self.assertIn(
            "node:encoded-yuv-surface:precision=yuv420:halo=0:temporal=none:deterministic=true:parameters=bt709:alters=color",
            result["preservedResults"],
        )

    def test_processed_frames_do_not_validate_a_compatible_edge(self) -> None:
        raw = load_document()
        raw["edges"] = [edge for edge in raw["edges"] if edge["id"] == "working-to-density"]
        raw["validation"]["framesProcessed"] = True
        raw["validation"]["allocated"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["processed-before-validation"])
        self.assertIn("status=compatible", _edge(result["preservedResults"], "working-to-density"))
        self.assertIn("frames-processed:true", result["preservedResults"])
        self.assertIn("allocated:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "edges_validated"})

    def test_empty_edges_are_withheld_and_keep_nodes(self) -> None:
        raw = load_document()
        raw["edges"] = []
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any(item.startswith("node:film-density:") for item in result["preservedResults"]))
        self.assertIn("stage:before-allocation", result["preservedResults"])

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P064"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        bad_stage = copy.deepcopy(valid)
        bad_stage["validation"]["stage"] = "after-frames"
        string_flag = copy.deepcopy(valid)
        string_flag["validation"]["framesProcessed"] = "false"
        dangling = copy.deepcopy(valid)
        dangling["edges"][0]["toNode"] = "missing-node"
        wrong_side = copy.deepcopy(valid)
        wrong_side["edges"][0]["fromPort"] = "density-in"
        duplicate = copy.deepcopy(valid)
        duplicate["nodes"].append(copy.deepcopy(duplicate["nodes"][0]))
        bad_halo = copy.deepcopy(valid)
        bad_halo["nodes"][0]["halo"] = "02"
        precision_drift = copy.deepcopy(valid)
        precision_drift["nodes"][1]["outputs"][0]["precision"] = "rgba8"
        empty_nodes = copy.deepcopy(valid)
        empty_nodes["nodes"] = []
        bad_alter = copy.deepcopy(valid)
        bad_alter["nodes"][0]["alters"] = ["light"]
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            bad_stage,
            string_flag,
            dangling,
            wrong_side,
            duplicate,
            bad_halo,
            precision_drift,
            empty_nodes,
            bad_alter,
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
