"""Host checks for P126. Not a physical S23 probe."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p126_build_a_trustworthy_clip_library",
    Path(__file__).resolve().parents[1] / "gates" / "p126_build_a_trustworthy_clip_library.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
RULE = "present-and-verified-and-matching-hash-and-positive-byte-count"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _clip(text: str, **overrides):
    row = {
        "clip_id": "clip-result",
        "content_sha256": _digest(text),
        "byte_count": len(text.encode("utf-8")),
        "present": True,
        "playable": True,
        "verification": "verified",
        "content": text,
        "role": "result",
        "bundle_id": "take-1",
    }
    row.update(overrides)
    return row


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P126",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p126-wedge",
        "claim": "synthetic-host-fixture",
        "applyMutant": False,
        "omitted_ids": [],
        "clips": [_clip("p126-verified-result-v1")],
    }
    value.update(overrides)
    return value


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class P126Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P126")
        self.assertEqual(_MODULE.WORKSTREAM, 16)
        self.assertEqual(_MODULE.TITLE, "Build a trustworthy clip library")
        self.assertEqual(
            _MODULE.GOAL,
            "Keep source, result, metadata, thumbnail, and recovery identities paired.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Use thumbnail existence as the media availability check.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Clip library schema and missing-media tests")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P125",))
        self.assertEqual(
            _MODULE.FIXTURE,
            "A thumbnail remains cached after the underlying media permission is revoked.",
        )
        self.assertEqual([case["id"] for case in _MODULE.CASES], [
            "TC-P126-01",
            "TC-P126-02",
            "TC-P126-03",
            "TC-P126-04",
            "TC-P126-05",
            "TC-P126-06",
            "TC-P126-07",
            "TC-P126-08",
        ])

    def test_verified_clip_is_recorded_not_qualified(self):
        result = assess(document())
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P126")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p126-wedge", result["preservedResults"])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])
        self.assertIn("playableRule=" + RULE, blob(result))
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(_MODULE.playable_allowed(
            {"present": True, "verification": "verified", "byte_count": 4},
            True,
        ))
        self.assertFalse(_MODULE.playable_allowed(
            {"present": False, "verification": "missing", "byte_count": 4},
            None,
        ))

    def test_published_fixture_lists_revoked_media_without_trusting_the_thumbnail(self):
        payload = json.loads(
            (ROOT / "docs" / "P126_BUILD_A_TRUSTWORTHY_CLIP_LIBRARY.json").read_text()
        )
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p126-clip-library", result["preservedResults"])
        self.assertIn("missing:clip-source-revoked", result["preservedResults"])
        self.assertIn("thumbnail-not-availability:clip-source-revoked", result["reasons"])
        self.assertIn("stayed-unverified:clip-thumbnail-cached", result["reasons"])
        self.assertIn("stayed-unverified:clip-recovery-paired", result["reasons"])
        self.assertNotIn("thumbnail-certifies-availability", result["rejectedClaims"])
        self.assertNotIn("promoted-with-hash-match:clip-thumbnail-cached", " ".join(result["reasons"]))
        for role in ("source", "thumbnail", "metadata", "result", "recovery"):
            self.assertIn("role=" + role, blob(result))

    def test_playable_true_without_bytes_is_rejected_and_listed(self):
        gone = _clip("historical-source")
        gone.pop("content")
        gone.update({
            "clip_id": "clip-source-revoked",
            "present": False,
            "playable": True,
            "verification": "missing",
            "thumbnail_cached": True,
            "role": "source",
        })
        result = assess(document(clips=[gone], omitted_ids=["clip-source-revoked"]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("playable-absent-bytes", result["rejectedClaims"])
        self.assertIn("thumbnail-certifies-availability", result["rejectedClaims"])
        self.assertIn("missing:clip-source-revoked", result["preservedResults"])
        self.assertIn("p126-wedge", result["preservedResults"])

    def test_content_hash_mismatch_is_rejected(self):
        result = assess(document(clips=[_clip("p126-verified-result-v1", content="other-bytes")]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("content-sha256-mismatch", result["rejectedClaims"])
        self.assertIn("byte-count-mismatch", result["rejectedClaims"])
        self.assertIn("p126-wedge", result["preservedResults"])

    def test_duplicate_clip_id_with_different_hashes_is_rejected(self):
        first = _clip("alpha", clip_id="clip-shared", playable=False, verification="unverified")
        second = _clip("beta", clip_id="clip-shared", playable=False, verification="unverified")
        result = assess(document(clips=[first, second]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-clip-id:clip-shared", result["rejectedClaims"])
        self.assertIn("duplicate-clip-id-hash-mismatch:clip-shared", result["rejectedClaims"])

    def test_unverified_row_stays_unverified_when_the_hash_matches(self):
        row = _clip(
            "p126-cached-thumbnail-v1",
            clip_id="clip-thumbnail-cached",
            playable=False,
            verification="unverified",
            role="thumbnail",
        )
        result = assess(document(clips=[row]))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("stayed-unverified:clip-thumbnail-cached", result["reasons"])
        self.assertIn("verification=unverified", blob(result))
        self.assertNotIn("promoted-with-hash-match:clip-thumbnail-cached", " ".join(result["reasons"]))

    def test_promoting_unverified_without_a_hash_match_is_rejected(self):
        row = _clip("p126-verified-result-v1", prior_verification="unverified")
        row.pop("content")
        result = assess(document(clips=[row]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unverified-promoted-without-hash-match", result["rejectedClaims"])

    def test_promoting_unverified_with_a_hash_match_is_recorded(self):
        row = _clip("p126-verified-result-v1", prior_verification="unverified")
        result = assess(document(clips=[row]))
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("promoted-with-hash-match:clip-result", result["reasons"])

    def test_omitted_missing_id_is_rejected_and_other_missing_rows_stay_listed(self):
        bad = _clip("p126-verified-result-v1", content="tampered")
        missing = _clip("historical-source", clip_id="clip-source-revoked", role="source")
        missing.pop("content")
        missing.update({"present": False, "playable": False, "verification": "missing"})
        result = assess(document(
            clips=[missing, bad],
            omitted_ids=["clip-source-revoked", "clip-not-indexed"],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("content-sha256-mismatch", result["rejectedClaims"])
        self.assertIn("omitted-missing-id:clip-not-indexed", result["rejectedClaims"])
        self.assertIn("missing:clip-source-revoked", result["preservedResults"])
        self.assertNotIn("omitted-missing-id:clip-source-revoked", result["rejectedClaims"])

    def test_absent_clip_with_the_wrong_verification_is_rejected(self):
        row = _clip("historical-source", present=False, playable=False, verification="verified")
        row.pop("content")
        result = assess(document(clips=[row]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("absent-clip-not-missing", result["rejectedClaims"])

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn("p126-wedge", result["preservedResults"])
        self.assertIn("playableRule=" + RULE, result["preservedResults"])

    def test_uppercase_hash_and_invalid_payload_raise(self):
        with self.assertRaises(ValueError):
            assess({})
        row = _clip("p126-verified-result-v1")
        row["content_sha256"] = row["content_sha256"].upper()
        with self.assertRaises(ValueError):
            assess(document(clips=[row]))
        with self.assertRaises(ValueError):
            assess(document(clips=[_clip("p126-verified-result-v1", playable=1)]))
        copied = document()
        copied["clips"] = copy.deepcopy(copied["clips"])
        copied["extra"] = True
        with self.assertRaises(ValueError):
            assess(copied)

    def test_handoff_points_at_p127(self):
        handoff = json.loads((ROOT / "docs" / "evidence" / "P126-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P126")
        self.assertEqual(handoff["commit"], None)
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(handoff["nextPhase"], "P127")
        self.assertEqual(handoff["caseIds"], [case["id"] for case in _MODULE.CASES])
