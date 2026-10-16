"""Host checks for P102. Not a physical S23 probe."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p102_construct_a_difficult_scene_depth_corpus",
    Path(__file__).resolve().parents[1] / "gates" / "p102_construct_a_difficult_scene_depth_corpus.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def fixture():
    path = _ROOT / "docs" / "P102_CONSTRUCT_A_DIFFICULT_SCENE_DEPTH_CORPUS.json"
    return json.loads(path.read_text(encoding="utf-8"))


def easy_scene(scene_id, content, split):
    return {
        "sceneId": scene_id,
        "content": content,
        "contentSha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "tags": ["portrait", "textured", "simple background"],
        "split": split,
        "frameCount": 4,
        "depthKind": "relative",
        "depthUnit": "relative",
        "labelSource": "qualitative",
        "rightsCleared": True,
        "boundaryFailures": [],
        "orderingFailures": [],
    }


class P102Tests(unittest.TestCase):
    def test_fixture_is_recorded_not_qualified(self):
        document = fixture()
        for scene in document["scenes"]:
            digest = hashlib.sha256(scene["content"].encode("utf-8")).hexdigest()
            self.assertEqual(digest, scene["contentSha256"])
        result = assess(document)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P102")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p102-difficult-scene-corpus", result["preservedResults"])
        self.assertIn("coverage-score:6/6", result["preservedResults"])
        self.assertIn("unique-scenes:8", result["preservedResults"])
        self.assertIn("boundary:person-behind-fence:fence-occludes-person", result["preservedResults"])
        self.assertIn("ordering:person-behind-fence:reflection-nearer-than-person", result["preservedResults"])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertIn("coverage-score=6/6", result["reasons"])
        self.assertTrue(any(item == "physical S23 measurement was not run" for item in result["openQuestions"]))
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P102")
        self.assertEqual(_MODULE.DELIVERABLE, "Difficult-scene corpus and per-category evaluation protocol")

    def test_easy_portrait_benchmark_is_rejected(self):
        document = fixture()
        document["scenes"] = [
            easy_scene("portrait-a", "portrait-simple-background-v1", "train"),
            easy_scene("portrait-b", "portrait-textured-backdrop-v1", "held_out"),
        ]
        result = assess(document)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("easy-textured-scenes-only", result["rejectedClaims"])
        self.assertIn("missing-required-difficult-tag", result["rejectedClaims"])
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("p102-difficult-scene-corpus", result["preservedResults"])
        self.assertIn("coverage-score:0/6", result["preservedResults"])

    def test_duplicate_hash_is_not_a_new_scene(self):
        document = fixture()
        clone = copy.deepcopy(document["scenes"][0])
        clone["sceneId"] = "duplicate-fence"
        document["scenes"].append(clone)
        result = assess(document)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-content-hash", result["rejectedClaims"])
        self.assertIn("unique-scenes:8", result["preservedResults"])
        self.assertIn("listed-scenes:9", result["preservedResults"])
        self.assertIn(document["evidenceId"], result["preservedResults"])

    def test_tag_only_in_train_does_not_cover_held_out(self):
        document = fixture()
        document["scenes"] = [scene for scene in document["scenes"] if scene["sceneId"] != "held-glass"]
        result = assess(document)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-required-difficult-tag", result["rejectedClaims"])
        self.assertIn("coverage-score:5/6", result["preservedResults"])
        self.assertTrue(any("glass" in item for item in result["reasons"]))

    def test_relative_depth_called_metres_is_rejected(self):
        document = fixture()
        document["scenes"][2]["depthUnit"] = "metres"
        result = assess(document)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("relative-depth-called-metres", result["rejectedClaims"])
        self.assertIn(document["evidenceId"], result["preservedResults"])

    def test_global_score_is_rejected(self):
        document = fixture()
        document["protocol"]["globalScore"] = 0.91
        result = assess(document)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("averaged-into-one-global-score", result["rejectedClaims"])
        self.assertIn("boundary:person-behind-fence:fence-occludes-person", result["preservedResults"])

    def test_changed_evidence_id_is_preserved(self):
        document = fixture()
        document["evidenceId"] = "p102-other-evidence"
        result = assess(document)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("p102-other-evidence", result["preservedResults"])

    def test_invalid_payload_raises(self):
        document = fixture()
        document["scenes"][0]["contentSha256"] = "0" * 64
        with self.assertRaises(ValueError):
            assess(document)
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess([])
