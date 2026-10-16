"""Host checks for P122. Not a physical S23 probe."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p122_create_non_destructive_recipe_versions",
    Path(__file__).resolve().parents[1] / "gates" / "p122_create_non_destructive_recipe_versions.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SOURCE = "9f08a9433990a82fcc30bdeb08ab218ae4f002b36466df429c12d59b72d9275c"
PARENT_PREIMAGE = (
    '{"params":{"focus":0.4,"grain":0.15},"parent":null,"source":"' + SOURCE + '"}'
)
CHILD_PREIMAGE = (
    '{"params":{"focus":0.72,"grain":0.33},"parent":"rv-1","source":"' + SOURCE + '"}'
)


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P122",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p122-wedge",
        "claim": "synthetic-host-fixture",
        "applyMutant": False,
        "mutatedInPlace": False,
        "sourceMaterial": _MODULE.SOURCE_MATERIAL,
        "versions": _MODULE.sample_versions(),
        "runningExportRecipeId": _MODULE.PARENT_ID,
        "liveParameters": dict(_MODULE.CHILD_PARAMETERS),
    }
    value.update(overrides)
    return value


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class P122Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P122")
        self.assertEqual(_MODULE.WORKSTREAM, 16)
        self.assertEqual(_MODULE.DEPENDENCIES, ("P121",))
        self.assertEqual(_MODULE.TITLE, "Create non-destructive recipe versions")
        self.assertEqual(
            _MODULE.GOAL,
            "Make every creative edit reproducible without rewriting the source or previous result.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Read live UI slider values during each frame of an export.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Recipe snapshot store and concurrent-edit tests")
        self.assertEqual(
            _MODULE.ORACLE,
            "The running export remains bound to its original recipe and the new edit receives a distinct identity.",
        )

    def test_hash_preimage_is_canonical_params_parent_source(self):
        source = _MODULE.source_digest()
        self.assertEqual(source, SOURCE)
        self.assertEqual(source, hashlib.sha256(b"s23-imported-clip-a").hexdigest())
        parent = _MODULE.make_version("rv-1", None, source, {"grain": 0.15, "focus": 0.4})
        self.assertEqual(_MODULE.canonical_preimage(None, source, parent["parameters"]), PARENT_PREIMAGE)
        self.assertEqual(parent["version_sha256"], hashlib.sha256(PARENT_PREIMAGE.encode("utf-8")).hexdigest())
        self.assertEqual(parent["version_sha256"], "cd6a49c49dda03f5a206c43f4fba5d67cb2b7d540971fe06ccc9431401a3e112")
        before = _MODULE.object_bytes(parent)
        child = _MODULE.fork_version(parent, "rv-2", {"grain": 0.33, "focus": 0.72})
        self.assertEqual(_MODULE.object_bytes(parent), before)
        self.assertEqual(_MODULE.canonical_preimage("rv-1", source, child["parameters"]), CHILD_PREIMAGE)
        self.assertEqual(child["version_sha256"], hashlib.sha256(CHILD_PREIMAGE.encode("utf-8")).hexdigest())
        self.assertNotEqual(child["id"], parent["id"])
        self.assertNotEqual(child["version_sha256"], parent["version_sha256"])
        self.assertEqual(child["source_sha256"], parent["source_sha256"])
        self.assertEqual(child["parent_id"], parent["id"])

    def test_concurrent_edit_is_recorded_and_parent_stays_byte_identical(self):
        doc = document()
        before = json.dumps(doc["versions"], sort_keys=True)
        result = assess(doc)
        self.assertEqual(json.dumps(doc["versions"], sort_keys=True), before)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P122")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p122-wedge", result["preservedResults"])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])
        self.assertIn("preimage=" + PARENT_PREIMAGE, result["preservedResults"])
        self.assertIn("preimage=" + CHILD_PREIMAGE, result["preservedResults"])
        self.assertIn("rv-2 parentByteIdentical=true", blob(result))
        self.assertIn("new edit identity rv-2", result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_published_fixture_keeps_the_running_export_on_the_parent(self):
        payload = json.loads(
            (ROOT / "docs" / "P122_CREATE_NON_DESTRUCTIVE_RECIPE_VERSIONS.json").read_text()
        )
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p122-recipe-versions", result["preservedResults"])
        self.assertIn("preimage=" + CHILD_PREIMAGE, result["preservedResults"])
        self.assertIn("runningExportRecipeId=rv-1", result["preservedResults"])
        self.assertIn("source_sha256=" + SOURCE, result["preservedResults"])

    def test_mutant_live_sliders_are_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn("p122-wedge", result["preservedResults"])
        self.assertIn("preimage=" + PARENT_PREIMAGE, result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_in_place_mutation_is_rejected(self):
        result = assess(document(mutatedInPlace=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.IN_PLACE, result["rejectedClaims"])
        self.assertIn("p122-wedge", result["preservedResults"])

    def test_changed_source_hash_is_rejected(self):
        versions = _MODULE.sample_versions()
        other = "a" * 64
        versions[1]["source_sha256"] = other
        versions[1]["version_sha256"] = _MODULE.compute_version_sha256(
            versions[1]["parent_id"], other, versions[1]["parameters"]
        )
        result = assess(document(versions=versions))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SOURCE_CHANGED, result["rejectedClaims"])
        self.assertIn(_MODULE.SOURCE_MISMATCH, result["rejectedClaims"])

    def test_missing_parent_is_rejected(self):
        versions = _MODULE.sample_versions()
        versions[1]["parent_id"] = "missing"
        versions[1]["version_sha256"] = _MODULE.compute_version_sha256(
            "missing", versions[1]["source_sha256"], versions[1]["parameters"]
        )
        result = assess(document(versions=versions))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_PARENT, result["rejectedClaims"])

    def test_hash_mismatch_is_rejected(self):
        versions = _MODULE.sample_versions()
        versions[1]["version_sha256"] = "b" * 64
        result = assess(document(versions=versions))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HASH_MISMATCH, result["rejectedClaims"])
        self.assertIn("preimage=" + CHILD_PREIMAGE, result["preservedResults"])

    def test_export_that_follows_the_live_edit_is_rejected(self):
        result = assess(document(
            runningExportRecipeId=_MODULE.CHILD_ID,
            liveParameters={"grain": 0.33, "focus": 0.72},
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.EXPORT_FOLLOWED, result["rejectedClaims"])

    def test_edit_without_a_distinct_version_is_rejected(self):
        result = assess(document(liveParameters={"focus": 0.1, "grain": 0.9}))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.EDIT_IDENTITY, result["rejectedClaims"])
        self.assertIn("p122-wedge", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        versions = _MODULE.sample_versions()
        versions[0]["source_sha256"] = SOURCE.upper()
        with self.assertRaises(ValueError):
            assess(document(versions=versions))
        with self.assertRaises(ValueError):
            _MODULE.make_version("rv-1", None, SOURCE, {"focus": float("nan")})

    def test_handoff_points_at_p123(self):
        handoff = json.loads((ROOT / "docs" / "evidence" / "P122-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P122")
        self.assertEqual(handoff["commit"], None)
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(handoff["nextPhase"], "P123")
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p122*.py' -v",
        )
        for relative in handoff["changedFiles"]:
            self.assertTrue((ROOT / relative).is_file(), relative)
