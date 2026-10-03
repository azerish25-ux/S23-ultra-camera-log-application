"""Host checks for the P029 cadence fixture. Not a physical S23 probe.

TC-P029-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p029_preserve_cadence_rather_than_hide_gaps import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    RETIMING_OPERATION,
    assess,
    frame_token,
    frames_divided_by_duration_would_approve,
    source_intervals,
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
PRESERVED = [
    "f0#p0/r0@0ms:c0:dup0",
    "f1#p1/r1@40ms:c1:dup0",
    "f2#p2/r2@88ms:c2:dup0",
    "f3#p3/r3@120ms:c3:dup0",
    "duration:120ms",
    "count:4",
    "nominal:40ms",
    "tolerance:1ms",
    "packet-order:f0,f1,f2,f3",
    "presentation-order:f0,f1,f2,f3",
    "interval:f0->f1:40ms",
    "interval:f1->f2:48ms",
    "interval:f2->f3:32ms",
]


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P029_PRESERVE_CADENCE_RATHER_THAN_HIDE_GAPS.json").read_text(
            encoding="utf-8"
        )
    )


def frame(**overrides) -> dict:
    value = {
        "id": "f0",
        "packetIndex": 0,
        "presentationIndex": 0,
        "timestampMs": "0",
        "duplicate": False,
        "contentId": "c0",
    }
    value.update(overrides)
    return value


def document(frames: list[dict], **overrides) -> dict:
    value = {
        "schemaVersion": 1,
        "phase": "P029",
        "mapId": MAP_ID,
        "implementationBaseRevision": BASE_REVISION,
        "method": METHOD,
        "fixture": FIXTURE,
        "oracle": ORACLE,
        "mutant": MUTANT,
        "nominalIntervalMs": "40",
        "toleranceMs": "1",
        "frames": frames,
        "retiming": None,
    }
    value.update(overrides)
    return value


def uniform_frames() -> list[dict]:
    return [
        frame(id="f0", packetIndex=0, presentationIndex=0, timestampMs="0", contentId="c0"),
        frame(id="f1", packetIndex=1, presentationIndex=1, timestampMs="40", contentId="c1"),
        frame(id="f2", packetIndex=2, presentationIndex=2, timestampMs="80", contentId="c2"),
    ]


class P029CadenceTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P029")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P029")
        self.assertEqual(MAP_ID, "s23-cadence-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("original timestamp intervals", METHOD)
        self.assertIn("packet ordering distinct from presentation ordering", METHOD)
        self.assertIn("not repair disguised as native capture", METHOD)
        self.assertEqual(
            FIXTURE,
            "A source containing one forty-eight-millisecond gap and a later short interval that "
            "restores the average frame rate.",
        )
        self.assertEqual(
            ORACLE,
            "The per-frame integrity gate reports the gap even when the final average falls within "
            "tolerance.",
        )
        self.assertEqual(MUTANT, "Approve cadence using only total frames divided by duration.")
        self.assertEqual(RETIMING_OPERATION, "constant_frame_rate_development")

    def test_fixture_reports_the_gap_when_the_average_matches(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P029")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["nominalIntervalMs"], "40")
        self.assertEqual(raw["toleranceMs"], "1")
        self.assertIsNone(raw["retiming"])
        self.assertEqual(source_intervals(raw), [40, 48, 32])
        self.assertTrue(frames_divided_by_duration_would_approve(raw))
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "approved"})
        self.assertEqual(
            result["rejectedClaims"],
            [
                "source-cadence-defect",
                "gap:48ms",
                "forty-eight-millisecond-gap",
                "short-interval",
                "frames-divided-by-duration",
            ],
        )
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertIn("interval:f1->f2:48ms", result["preservedResults"])
        self.assertIn("interval:f2->f3:32ms", result["preservedResults"])
        self.assertEqual(
            result["openQuestions"],
            ["average within tolerance does not hide the source gap"],
        )
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(MUTANT, result["reasons"])
        self.assertIn("per-frame integrity reports the gap", result["reasons"])
        self.assertIn("the final average falls within tolerance", result["reasons"])
        self.assertIn("analyzed count 4 and duration 120ms", result["reasons"])
        self.assertIn("original timestamp evidence is preserved", result["reasons"])

    def test_mutant_count_over_duration_does_not_approve_the_gap(self) -> None:
        raw = load_document()
        self.assertTrue(frames_divided_by_duration_would_approve(raw))
        result = assess(raw)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "approved"})
        self.assertIn("frames-divided-by-duration", result["rejectedClaims"])
        self.assertIn("forty-eight-millisecond-gap", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], PRESERVED)
        joined = " ".join(result["preservedResults"])
        self.assertIn("48ms", joined)
        self.assertNotIn("approved", joined)

    def test_codec_reorder_keeps_packet_intervals_distinct(self) -> None:
        raw = load_document()
        raw["frames"][1]["presentationIndex"] = 2
        raw["frames"][2]["presentationIndex"] = 1
        self.assertEqual(source_intervals(raw), [40, 48, 32])
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertIn("interval:f1->f2:48ms", result["preservedResults"])
        self.assertIn("packet-order:f0,f1,f2,f3", result["preservedResults"])
        self.assertIn("presentation-order:f0,f2,f1,f3", result["preservedResults"])
        self.assertIn(
            "packet ordering is distinct from presentation ordering",
            result["openQuestions"],
        )
        self.assertIn(
            "packet ordering stays distinct from presentation ordering",
            result["reasons"],
        )
        self.assertIn("forty-eight-millisecond-gap", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_named_retiming_keeps_the_source_gap(self) -> None:
        raw = load_document()
        raw["retiming"] = {
            "operation": RETIMING_OPERATION,
            "mappingId": "map-1",
            "sourceFrameIds": ["f0", "f1", "f2", "f3"],
            "outputIntervalMs": "40",
            "claimNativeCapture": False,
        }
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("interval:f1->f2:48ms", result["preservedResults"])
        self.assertIn(
            "retiming:constant_frame_rate_development:map-1:40ms",
            result["preservedResults"],
        )
        self.assertIn("claim-native:false", result["preservedResults"])
        self.assertIn(
            "retiming is a named development operation, not native capture",
            result["openQuestions"],
        )
        self.assertIn(
            "source-to-output mapping is development metadata, not native capture",
            result["reasons"],
        )
        self.assertNotIn("retiming-disguised-as-native", result["rejectedClaims"])

    def test_native_retiming_claim_is_rejected_and_intervals_remain(self) -> None:
        raw = load_document()
        raw["retiming"] = {
            "operation": RETIMING_OPERATION,
            "mappingId": "map-1",
            "sourceFrameIds": ["f0", "f1", "f2", "f3"],
            "outputIntervalMs": "40",
            "claimNativeCapture": True,
        }
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "cadence_defect"})
        self.assertIn("retiming-disguised-as-native", result["rejectedClaims"])
        self.assertIn("forty-eight-millisecond-gap", result["rejectedClaims"])
        self.assertIn("interval:f1->f2:48ms", result["preservedResults"])
        self.assertIn("claim-native:true", result["preservedResults"])
        self.assertIn("retiming must not be disguised as native capture", result["reasons"])

    def test_uniform_intervals_are_withheld_not_qualified(self) -> None:
        raw = document(uniform_frames())
        self.assertTrue(frames_divided_by_duration_would_approve(raw))
        self.assertEqual(source_intervals(raw), [40, 40])
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn("frames-divided-by-duration", result["rejectedClaims"])
        self.assertIn("interval:f0->f1:40ms", result["preservedResults"])
        self.assertIn("duration:80ms", result["preservedResults"])
        self.assertIn("count:3", result["preservedResults"])
        self.assertEqual(
            result["openQuestions"],
            ["host fixture does not certify fixed cadence"],
        )
        self.assertTrue(
            any("not physical S23 qualification" in item for item in result["reasons"])
        )

    def test_duplicate_timestamp_and_repeated_content_stay_in_inventory(self) -> None:
        frames = [
            frame(id="f0", packetIndex=0, presentationIndex=0, timestampMs="0", contentId="c0"),
            frame(
                id="f1",
                packetIndex=1,
                presentationIndex=1,
                timestampMs="0",
                duplicate=True,
                contentId="c0",
            ),
        ]
        result = assess(document(frames, nominalIntervalMs="40", toleranceMs="0"))
        self.assert_result(result)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("duplicate-timestamp", result["rejectedClaims"])
        self.assertIn("repeated-image-content", result["rejectedClaims"])
        self.assertIn(frame_token(frames[0]), result["preservedResults"])
        self.assertIn(frame_token(frames[1]), result["preservedResults"])
        self.assertIn("interval:f0->f1:0ms", result["preservedResults"])
        self.assertFalse(frames_divided_by_duration_would_approve(document(frames)))

    def test_uncompensated_gap_is_still_a_defect(self) -> None:
        frames = [
            frame(id="f0", packetIndex=0, presentationIndex=0, timestampMs="0", contentId="c0"),
            frame(id="f1", packetIndex=1, presentationIndex=1, timestampMs="40", contentId="c1"),
            frame(id="f2", packetIndex=2, presentationIndex=2, timestampMs="88", contentId="c2"),
        ]
        raw = document(frames)
        self.assertFalse(frames_divided_by_duration_would_approve(raw))
        self.assertEqual(source_intervals(raw), [40, 48])
        result = assess(raw)
        self.assertEqual(result["decision"], "cadence_defect")
        self.assertIn("forty-eight-millisecond-gap", result["rejectedClaims"])
        self.assertNotIn("frames-divided-by-duration", result["rejectedClaims"])
        self.assertNotIn("short-interval", result["rejectedClaims"])
        self.assertIn("interval:f1->f2:48ms", result["preservedResults"])
        self.assertIn(
            "the final average is outside tolerance and the per-frame defect remains",
            result["reasons"],
        )

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["frames"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P028"
        wrong_revision = copy.deepcopy(valid)
        wrong_revision["implementationBaseRevision"] = "abc"
        numeric = copy.deepcopy(valid)
        numeric["frames"][1]["timestampMs"] = 40
        bool_index = copy.deepcopy(valid)
        bool_index["frames"][0]["packetIndex"] = True
        duplicate_packet = copy.deepcopy(valid)
        duplicate_packet["frames"][1]["packetIndex"] = 0
        one = copy.deepcopy(valid)
        one["frames"] = one["frames"][:1]
        bad_op = copy.deepcopy(valid)
        bad_op["retiming"] = {
            "operation": "repair",
            "mappingId": "map-1",
            "sourceFrameIds": ["f0"],
            "outputIntervalMs": "40",
            "claimNativeCapture": False,
        }
        native_flag = copy.deepcopy(valid)
        native_flag["retiming"] = {
            "operation": RETIMING_OPERATION,
            "mappingId": "map-1",
            "sourceFrameIds": ["f0", "f1", "f2", "f3"],
            "outputIntervalMs": "40",
            "claimNativeCapture": "true",
        }
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            wrong_phase,
            wrong_revision,
            numeric,
            bool_index,
            duplicate_packet,
            one,
            bad_op,
            native_flag,
            document([frame(id="only")]),
            document(uniform_frames(), nominalIntervalMs="0"),
            document(uniform_frames(), toleranceMs="-1"),
            document(uniform_frames(), method="other"),
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)


if __name__ == "__main__":
    unittest.main()
