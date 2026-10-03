"""Host checks for the P034 exact pairing fixture. Not a physical S23 probe.

TC-P034-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p034_pair_images_with_exact_capture_metadata import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    assess,
    refused_latest_attachments,
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
EXACT_LATE = (
    "exact:late@2000000000:exposure:10000000:black:64:neutral:0.45,1,0.55"
)
EXACT_EARLY = (
    "exact:early@1000000000:exposure:20000000:black:64:neutral:0.50,1,0.60"
)
GAP_ABSENT = "gap:absent@3000000000:missing-metadata"
PRESERVED = [
    "image:early@1000000000",
    "metadata:late@2000000000:exposure:10000000:black:64:neutral:0.45,1,0.55",
    "image:absent@3000000000",
    "image:late@2000000000",
    "metadata:early@1000000000:exposure:20000000:black:64:neutral:0.50,1,0.60",
    "stop@1500000000",
    "closed:early",
    "closed:absent",
    "closed:late",
    EXACT_LATE,
    EXACT_EARLY,
    GAP_ABSENT,
]


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P034_PAIR_IMAGES_WITH_EXACT_CAPTURE_METADATA.json").read_text(
            encoding="utf-8"
        )
    )


def image(frame_id, stamp, at_ns, *, copied=True, closed=True) -> dict:
    return {
        "kind": "image",
        "frameId": frame_id,
        "sensorTimestampNs": stamp,
        "atNs": at_ns,
        "copied": copied,
        "closed": closed,
    }


def metadata(frame_id, stamp, at_ns, exposure="10000000", black="64", neutral="0.45,1,0.55") -> dict:
    return {
        "kind": "metadata",
        "frameId": frame_id,
        "sensorTimestampNs": stamp,
        "atNs": at_ns,
        "exposureNs": exposure,
        "blackLevel": black,
        "neutral": neutral,
    }


def stop(at_ns) -> dict:
    return {"kind": "stop", "atNs": at_ns}


def document(events, **policy) -> dict:
    base = {
        "pendingLimit": 4,
        "timeoutNs": "1000000000",
        "missingMetadata": "gap",
        "duplicatePolicy": "reject_and_preserve",
    }
    base.update(policy)
    return {
        "schemaVersion": 1,
        "phase": "P034",
        "mapId": MAP_ID,
        "implementationBaseRevision": BASE_REVISION,
        "method": METHOD,
        "fixture": FIXTURE,
        "oracle": ORACLE,
        "mutant": MUTANT,
        "policy": base,
        "events": events,
    }


class P034ExactPairTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P034")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P034")
        self.assertEqual(MAP_ID, "s23-exact-pair-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("exact sensor timestamp", METHOD)
        self.assertIn("bounded pending maps", METHOD)
        self.assertIn("Close every Image", METHOD)
        self.assertEqual(
            FIXTURE,
            "Frames arriving out of callback order with one metadata entry delayed and another absent.",
        )
        self.assertIn("exact matches", ORACLE)
        self.assertEqual(MUTANT, "Attach the most recently received metadata to each incoming Image.")

    def test_fixture_pairs_exact_timestamps_only(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P034")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        refused = refused_latest_attachments(raw["events"])
        self.assertIn("absent@3000000000<-late@2000000000", refused)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "gapped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertIn(EXACT_LATE, result["preservedResults"])
        self.assertIn(EXACT_EARLY, result["preservedResults"])
        self.assertIn(GAP_ABSENT, result["preservedResults"])
        joined = " ".join(result["preservedResults"])
        self.assertNotIn("absent@3000000000:exposure", joined)
        self.assertNotIn("absent@3000000000<-late@2000000000", joined)
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("exact match late@2000000000", result["reasons"])
        self.assertIn("exact match early@1000000000", result["reasons"])
        self.assertIn("every copied image was closed", result["reasons"])
        self.assertEqual(
            result["openQuestions"],
            [GAP_ABSENT, "physical pairing unverified"],
        )
        self.assertNotIn(result["decision"], {"qualified", "allowed", "exact_paired"})

    def test_latest_metadata_mutant_is_rejected(self) -> None:
        raw = load_document()
        mutant = assess(raw, strategy="latest")
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["latest-metadata"])
        self.assertIn("image:absent@3000000000", mutant["preservedResults"])
        self.assertIn("metadata:late@2000000000:exposure:10000000:black:64:neutral:0.45,1,0.55",
                      mutant["preservedResults"])
        self.assertFalse(any(item.startswith("exact:") for item in mutant["preservedResults"]))
        self.assertIn(
            "refused latest attachment absent@3000000000<-late@2000000000",
            mutant["reasons"],
        )
        self.assertIn(MUTANT, mutant["reasons"])
        nearest = assess(raw, strategy="nearest")
        self.assertEqual(nearest["decision"], "rejected")
        self.assertIn("nearest-timestamp", nearest["rejectedClaims"])
        self.assertFalse(any(item.startswith("exact:") for item in nearest["preservedResults"]))
        self.assertIn("image:early@1000000000", nearest["preservedResults"])

    def test_timeout_gap_does_not_borrow_metadata(self) -> None:
        raw = document(
            [
                image("solo", "5000", "0"),
                metadata("other", "9000", "10"),
                stop("1000000000"),
            ],
            timeoutNs="1000000000",
        )
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "gapped")
        self.assertIn("gap:solo@5000:timeout", result["preservedResults"])
        self.assertIn("unused-metadata:other@9000", result["preservedResults"])
        self.assertNotIn("exact:solo@5000:exposure:10000000:black:64:neutral:0.45,1,0.55",
                         result["preservedResults"])
        self.assertIn("closed:solo", result["preservedResults"])

    def test_duplicate_timestamp_keeps_the_earlier_exact_pair(self) -> None:
        raw = document(
            [
                metadata("keep", "1000", "1"),
                image("keep", "1000", "2"),
                image("dup", "1000", "3"),
                stop("4"),
            ]
        )
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-timestamp:1000", result["rejectedClaims"])
        self.assertIn(
            "exact:keep@1000:exposure:10000000:black:64:neutral:0.45,1,0.55",
            result["preservedResults"],
        )
        self.assertIn("duplicate:image:dup@1000", result["preservedResults"])
        self.assertIn("image:dup@1000", result["preservedResults"])
        self.assertIn("image:keep@1000", result["preservedResults"])

    def test_pending_overflow_does_not_drop_the_oldest_image(self) -> None:
        raw = document(
            [
                image("first", "1000", "1"),
                image("second", "2000", "2"),
                stop("3"),
            ],
            pendingLimit=1,
        )
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("pending-overflow:second", result["rejectedClaims"])
        self.assertIn("gap:first@1000:missing-metadata", result["preservedResults"])
        self.assertIn("overflow:second@2000", result["preservedResults"])
        self.assertIn("image:first@1000", result["preservedResults"])
        self.assertIn("image:second@2000", result["preservedResults"])
        self.assertNotIn("gap:second@2000:missing-metadata", result["preservedResults"])

    def test_unclosed_image_is_not_paired(self) -> None:
        raw = document(
            [
                metadata("frame", "1000", "1", exposure="20000000", neutral="0.50,1,0.60"),
                image("frame", "1000", "2", closed=False),
                stop("3"),
            ]
        )
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("image-not-closed:frame", result["rejectedClaims"])
        self.assertNotIn("closed:frame", result["preservedResults"])
        self.assertFalse(any(item.startswith("exact:") for item in result["preservedResults"]))
        self.assertIn(
            "metadata:frame@1000:exposure:20000000:black:64:neutral:0.50,1,0.60",
            result["preservedResults"],
        )
        self.assertIn("unused-metadata:frame@1000", result["preservedResults"])

    def test_metadata_after_stop_does_not_pair(self) -> None:
        raw = document(
            [
                image("held", "1000", "10"),
                stop("20"),
                metadata("held", "1000", "30", exposure="20000000", neutral="0.50,1,0.60"),
            ]
        )
        result = assess(raw)
        self.assertEqual(result["decision"], "gapped")
        self.assertIn("gap:held@1000:missing-metadata", result["preservedResults"])
        self.assertIn("after-stop:metadata:held@1000", result["preservedResults"])
        self.assertFalse(any(item.startswith("exact:") for item in result["preservedResults"]))
        self.assertIn("image:held@1000", result["preservedResults"])

    def test_equal_timestamps_can_pair_without_claiming_qualification(self) -> None:
        raw = document(
            [
                metadata("only", "4000", "1", exposure="3000", black="1", neutral="1,1,1"),
                image("only", "4000", "2"),
                stop("3"),
            ]
        )
        result = assess(raw)
        self.assertEqual(result["decision"], "exact_paired")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("exact:only@4000:exposure:3000:black:1:neutral:1,1,1", result["preservedResults"])
        self.assertIn("closed:only", result["preservedResults"])
        self.assertIn("physical pairing unverified", result["openQuestions"])

    def test_invalid_document_raises(self) -> None:
        raw = load_document()
        bad = dict(raw)
        bad["phase"] = "P033"
        with self.assertRaises(ValueError):
            validate_document(bad)
        with self.assertRaises(ValueError):
            assess({"schemaVersion": True})
        drifted = load_document()
        drifted["mutant"] = "Attach the nearest metadata."
        with self.assertRaises(ValueError):
            assess(drifted)

    def test_note_names_host_command_and_non_claims(self) -> None:
        text = (ROOT / "docs" / "P034_PAIR_IMAGES_WITH_EXACT_CAPTURE_METADATA.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("host fixture", text)
        self.assertIn(
            "python3 -m unittest discover -s scripts/tests -p 'test_p034*.py' -v",
            text,
        )
        self.assertIn("not physical s23 qualification", text.lower())
        for claim in (
            "fixed cadence",
            "sensor-derived Log",
            "ten-bit",
            "film-stock",
            "cinema-camera",
        ):
            self.assertIn(claim, text)
        handoff = json.loads((ROOT / "docs" / "evidence" / "P034-handoff.json").read_text(
            encoding="utf-8"
        ))
        self.assertEqual(handoff["phase"], "P034")
        self.assertEqual(handoff["nextPhase"], "P035")
        self.assertEqual(handoff["commit"], "uncommitted")
        self.assertEqual(handoff["failures"], [])
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertEqual(len(handoff["caseIds"]), 8)


if __name__ == "__main__":
    unittest.main()
