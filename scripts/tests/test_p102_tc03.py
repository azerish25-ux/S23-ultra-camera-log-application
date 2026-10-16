"""Tests for TC-P102-03."""

from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p102_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p102_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def scene(scene_id, content, tags, split, kind="relative", unit="relative"):
    return {
        "sceneId": scene_id,
        "content": content,
        "contentSha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "tags": tags,
        "split": split,
        "frameCount": 4,
        "depthKind": kind,
        "depthUnit": unit,
        "depthError": 0.01,
        "boundaryError": 0.02,
    }


def payload(**overrides):
    base = {
        "evidenceId": "p102-evidence",
        "repeat": "hair",
        "modelRuns": True,
        "numericallyCompared": True,
        "depthTolerance": 0.05,
        "boundaryTolerance": 0.05,
        "scenes": [
            scene("train-fence", "train-fence-wires", ["thin objects"], "train"),
            scene("held-hair", "held-hair-strands", ["hair"], "held_out"),
            scene("held-glass", "held-glass-pane", ["glass"], "held_out"),
            scene("held-low-light", "held-low-light-alley", ["low light"], "held_out"),
            scene("held-thin", "held-thin-wires", ["thin objects"], "held_out"),
            scene("held-saturated", "held-saturated-neon", ["saturated"], "held_out", "metric", "metres"),
        ],
    }
    base.update(overrides)
    return base


class TCP10203(unittest.TestCase):
    def assert_contract(self, result, evidence="p102-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P102-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any(item == "physical S23 measurement was not run" for item in result["openQuestions"]))
        self.assertTrue(result["reasons"])

    def test_good_input_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("coverage-score:5/5", result["preservedResults"])

    def test_directive_negative_is_rejected(self):
        result = evaluate(payload(numericallyCompared=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("model-merely-runs-numerically-qualified", result["rejectedClaims"])
        self.assertNotIn("depth-boundary-tolerance-exceeded", result["rejectedClaims"])
        self.assertIn("p102-evidence", result["preservedResults"])

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p102-tc03-glass"
        result = evaluate(payload(evidenceId=evidence, repeat="glass"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        broken = payload()
        broken["scenes"][0]["contentSha256"] = "ab" * 32
        with self.assertRaises(ValueError):
            evaluate(broken)
