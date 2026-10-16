"""Tests for TC-P126-02."""

from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p126_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p126_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
RULE = "present-and-verified-and-matching-hash-and-positive-byte-count"
FROZEN = {"stock": "a", "focus": 1, "grain": 7, "range": "legal", "interpretation": "logc3"}
LIVE = {"stock": "b", "focus": 2, "grain": 7, "range": "legal", "interpretation": "logc3"}


def _library(clips=None, omitted=None):
    content = "paired-result"
    encoded = content.encode("utf-8")
    default = [{
        "clip_id": "clip-result",
        "content_sha256": hashlib.sha256(encoded).hexdigest(),
        "byte_count": len(encoded),
        "present": True,
        "playable": True,
        "verification": "verified",
        "content": content,
        "role": "result",
        "bundle_id": "take-1",
    }]
    return {"clips": default if clips is None else clips, "omitted_ids": [] if omitted is None else omitted}


def _absent_playable():
    encoded = b"gone"
    return {
        "clip_id": "clip-gone",
        "content_sha256": hashlib.sha256(encoded).hexdigest(),
        "byte_count": len(encoded),
        "present": False,
        "playable": True,
        "verification": "missing",
    }


def payload(**overrides):
    base = {
        "evidenceId": "p126-evidence",
        "repeat": "Repeat",
        "frozenRecipe": dict(FROZEN),
        "liveSliders": dict(LIVE),
        "frameRecipes": [dict(FROZEN), dict(FROZEN)],
        "runningRecipeId": "job-1",
        "nextEditRecipeId": "job-2",
    }
    base.update(_library())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12602(unittest.TestCase):
    def assert_contract(self, result, evidence="p126-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P126-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("playableRule=" + RULE, blob(result))
        self.assertTrue(result["reasons"])

    def test_frozen_recipe_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        frozen = "frozenRecipeSha256=" + _MODULE.recipe_sha256(FROZEN)
        self.assertIn(frozen, result["reasons"])
        self.assertIn(frozen, result["preservedResults"])
        self.assertIn("subsequent edit uses job-2", result["reasons"])

    def test_live_slider_frame_is_rejected(self):
        result = evaluate(payload(frameRecipes=[dict(FROZEN), dict(LIVE)]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("p126-evidence", result["preservedResults"])

    def test_unrelated_frame_recipe_is_rejected(self):
        other = dict(FROZEN)
        other["grain"] = 9
        result = evaluate(payload(frameRecipes=[other]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LEFT_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_subsequent_edit_cannot_reuse_the_running_id(self):
        result = evaluate(payload(nextEditRecipeId="job-1"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.REUSE_TOKEN, result["rejectedClaims"])

    def test_playable_without_bytes_is_rejected(self):
        result = evaluate(payload(**_library(clips=[_absent_playable()])))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("playable-absent-bytes", result["rejectedClaims"])
        self.assertIn("missing:clip-gone", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p126-grain"
        result = evaluate(payload(evidenceId=evidence, repeat="grain"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
