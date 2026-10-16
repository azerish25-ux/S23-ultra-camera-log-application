"""Host checks for P121. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p121_inspect_imported_media_before_rendering",
    Path(__file__).resolve().parents[1] / "gates" / "p121_inspect_imported_media_before_rendering.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE

_ROOT = Path(__file__).resolve().parents[2]
_KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
_SHA = "c6e9310719623a935277fb6301b1d9bc7e42ed4abd8fc32df9f6e1e7f33c19e4"


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P121",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p121-portrait-clip",
        "claim": "synthetic-host-fixture",
        "sourceUri": "file://import/portrait.mov",
        "filename": "portrait.mov",
        "duration_seconds": 2.0,
        "fps": 24,
        "video_timebase": "1/24000",
        "audio_timebase": "1/48000",
        "audio_absent": False,
        "audio_duration_seconds": 2.0,
        "color_transfer": "bt709",
        "color_primaries": "bt709",
        "range": "tv",
        "frame_count": 48,
        "content_sha256": _SHA,
        "rotation_degrees": 90,
        "rotation_policy": "declared-portrait-rotation",
        "variable_frame_rate": False,
        "vfr_policy": None,
        "rewritten_transfer": None,
        "transfer_interpretation": None,
        "range_interpretation": None,
        "render_allowed": True,
        "listed_missing_fields": [],
        "hide_av_delta": False,
        "color_from_extension": False,
        "cloud_metadata": None,
        "applyMutant": False,
    }
    value.update(overrides)
    return value


def _facts(result):
    return result["preservedResults"][2]


class P121Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P121")
        self.assertEqual(_MODULE.TITLE, "Inspect imported media before rendering")
        self.assertEqual(_MODULE.WORKSTREAM, 16)
        self.assertEqual(_MODULE.DEPENDENCIES, ("P025", "P032", "P057", "P064"))
        self.assertEqual(
            _MODULE.GOAL,
            "Determine source timing, geometry, color tags, rotation, and decoder support before assigning a look.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "An untagged HDR-looking clip, a rotated portrait clip, and a variable-frame-rate recording.",
        )
        self.assertEqual(
            _MODULE.DELIVERABLE,
            "Media inspection report and import normalization policy",
        )
        self.assertEqual(_MODULE.MUTANT, "Infer source color space solely from the filename extension.")
        self.assertIn("explicit interpretation", _MODULE.METHOD)
        self.assertEqual(_MODULE.AV_DELTA_LIMIT_SECONDS, 0.04)
        self.assertEqual(_MODULE.FORBIDDEN_RELABELS, ("logc3", "arri_log"))

    def test_blocking_fields_are_timestamps_hash_and_required_inspection(self):
        with_audio = _MODULE.blocking_fields(audio_absent=False)
        silent = _MODULE.blocking_fields(audio_absent=True)
        for name in (
            "duration_seconds",
            "video_timebase",
            "audio_timebase",
            "audio_duration_seconds",
            "content_sha256",
            "fps",
            "color_transfer",
            "color_primaries",
            "range",
            "frame_count",
            "rotation_degrees",
        ):
            self.assertIn(name, with_audio)
        self.assertNotIn("audio_timebase", silent)
        self.assertNotIn("audio_duration_seconds", silent)
        self.assertIn("content_sha256", silent)
        self.assertIn("duration_seconds", silent)

    def test_portrait_fixture_is_recorded_without_relabel(self):
        result = assess(document())
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "P121")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p121-portrait-clip", result["preservedResults"])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))
        self.assertTrue(any("cloud metadata was not invented" in item for item in result["openQuestions"]))
        facts = _facts(result)
        self.assertEqual(facts["color_transfer"], "bt709")
        self.assertIsNone(facts["rewritten_transfer"])
        self.assertEqual(facts["content_sha256"], _SHA)
        self.assertEqual(facts["rotation_degrees"], 90)
        self.assertEqual(facts["sourceUri"], "file://import/portrait.mov")
        self.assertEqual(facts["missing_fields"], [])
        self.assertEqual(facts["av_delta_seconds"], 0.0)
        self.assertTrue(facts["render_allowed"])
        self.assertNotIn("av-duration-delta-above-0.04s", " ".join(result["reasons"]))

    def test_fixture_file_and_handoff(self):
        payload = json.loads(
            (_ROOT / "docs" / "P121_INSPECT_IMPORTED_MEDIA_BEFORE_RENDERING.json").read_text()
        )
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(_facts(result)["content_sha256"], _SHA)
        self.assertEqual(_facts(result)["frame_count"], 48)
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P121-handoff.json").read_text())
        self.assertEqual(handoff["nextPhase"], "P122")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertIn("physical S23 capture", handoff["unverified"])

    def test_bt709_is_not_rewritten_to_logc3_or_arri_log(self):
        logc = assess(document(rewritten_transfer="logc3"))
        self.assertEqual(logc["decision"], "rejected")
        self.assertIn("bt709-rewritten-to-logc3", logc["rejectedClaims"])
        self.assertEqual(_facts(logc)["color_transfer"], "bt709")
        self.assertEqual(_facts(logc)["rewritten_transfer"], "logc3")
        self.assertIn("p121-portrait-clip", logc["preservedResults"])
        arri = assess(document(transfer_interpretation="arri_log"))
        self.assertEqual(arri["decision"], "rejected")
        self.assertIn("bt709-rewritten-to-arri_log", arri["rejectedClaims"])
        self.assertEqual(_facts(arri)["color_transfer"], "bt709")
        self.assertNotIn(arri["decision"], {"qualified", "allowed"})

    def test_filename_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("p121-portrait-clip", result["preservedResults"])
        extension = assess(document(color_from_extension=True, evidenceId="p121-extension"))
        self.assertEqual(extension["decision"], "rejected")
        self.assertIn(MUTANT, extension["rejectedClaims"])
        self.assertEqual(_facts(extension)["color_transfer"], "bt709")
        self.assertIn("p121-extension", extension["preservedResults"])

    def test_missing_hash_blocks_render_and_honest_incomplete_is_recorded(self):
        blocked = assess(document(content_sha256=None, render_allowed=True))
        self.assertEqual(blocked["decision"], "rejected")
        self.assertIn("render-allowed-while-blocked", blocked["rejectedClaims"])
        self.assertIn("missing-fields-not-listed", blocked["rejectedClaims"])
        self.assertTrue(any("missing hash blocks rendering: content_sha256" in item for item in blocked["reasons"]))
        self.assertIsNone(_facts(blocked)["content_sha256"])
        self.assertFalse(_facts(blocked)["render_allowed"])
        honest = assess(
            document(
                content_sha256=None,
                render_allowed=False,
                listed_missing_fields=["content_sha256"],
                evidenceId="p121-no-hash",
            )
        )
        self.assertEqual(honest["decision"], "recorded")
        self.assertEqual(honest["rejectedClaims"], [])
        self.assertIn("honest incomplete media recorded", honest["reasons"])
        self.assertIn("missing fields: content_sha256", honest["reasons"])
        self.assertIsNone(_facts(honest)["content_sha256"])
        self.assertNotEqual(_facts(honest)["content_sha256"], _SHA)

    def test_missing_timestamps_reject_a_forced_render(self):
        result = assess(
            document(
                duration_seconds=None,
                video_timebase=None,
                render_allowed=True,
                listed_missing_fields=["duration_seconds", "video_timebase"],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("render-allowed-while-blocked", result["rejectedClaims"])
        self.assertNotIn("missing-fields-not-listed", result["rejectedClaims"])
        self.assertTrue(
            any(
                "missing timestamps block rendering: duration_seconds, video_timebase" in item
                for item in result["reasons"]
            )
        )
        self.assertIsNone(_facts(result)["duration_seconds"])
        self.assertIsNone(_facts(result)["video_timebase"])
        self.assertFalse(_facts(result)["render_allowed"])
        hidden = assess(
            document(video_timebase=None, render_allowed=False, listed_missing_fields=[])
        )
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn("missing-fields-not-listed", hidden["rejectedClaims"])

    def test_audio_absent_does_not_require_audio_timestamps(self):
        result = assess(
            document(
                audio_absent=True,
                audio_timebase=None,
                audio_duration_seconds=None,
                evidenceId="p121-silent",
            )
        )
        self.assertEqual(result["decision"], "recorded")
        self.assertIsNone(_facts(result)["av_delta_seconds"])
        self.assertIsNone(_facts(result)["audio_timebase"])
        dishonest = assess(
            document(
                audio_absent=True,
                audio_timebase=None,
                audio_duration_seconds=None,
                listed_missing_fields=["audio_timebase"],
            )
        )
        self.assertEqual(dishonest["decision"], "rejected")
        self.assertIn("missing-fields-not-listed", dishonest["rejectedClaims"])

    def test_missing_audio_timebase_blocks_when_audio_is_present(self):
        result = assess(
            document(
                audio_timebase=None,
                render_allowed=True,
                listed_missing_fields=["audio_timebase"],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("render-allowed-while-blocked", result["rejectedClaims"])
        self.assertTrue(any("audio_timebase" in item for item in result["reasons"]))
        honest = assess(
            document(
                audio_timebase=None,
                render_allowed=False,
                listed_missing_fields=["audio_timebase"],
                evidenceId="p121-no-audio-timebase",
            )
        )
        self.assertEqual(honest["decision"], "recorded")
        self.assertIsNone(_facts(honest)["audio_timebase"])

    def test_av_delta_above_limit_is_a_warning_unless_hidden(self):
        warned = assess(document(audio_duration_seconds=2.05, evidenceId="p121-drift"))
        self.assertEqual(warned["decision"], "recorded")
        self.assertTrue(any(item.startswith("av-duration-delta-above-0.04s:") for item in warned["reasons"]))
        self.assertAlmostEqual(_facts(warned)["av_delta_seconds"], 0.05, places=6)
        self.assertEqual(warned["rejectedClaims"], [])
        hidden = assess(document(audio_duration_seconds=2.05, hide_av_delta=True))
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn("hidden-av-duration-delta", hidden["rejectedClaims"])
        self.assertTrue(any(item.startswith("av-duration-delta-above-0.04s:") for item in hidden["reasons"]))
        self.assertIn("p121-portrait-clip", hidden["preservedResults"])
        boundary = assess(document(audio_duration_seconds=2.04))
        self.assertEqual(boundary["decision"], "recorded")
        self.assertFalse(any("av-duration-delta-above-0.04s" in item for item in boundary["reasons"]))

    def test_untagged_hdr_is_not_guessed_and_vfr_needs_a_policy(self):
        untagged = assess(
            document(
                evidenceId="p121-untagged-hdr",
                filename="untagged-hdr.mov",
                color_transfer=None,
                color_primaries=None,
                range=None,
                transfer_interpretation="untagged-hdr-looking-not-sdr",
                range_interpretation="explicit-unknown-range",
                render_allowed=False,
                listed_missing_fields=["color_transfer", "color_primaries", "range"],
                rotation_degrees=0,
                rotation_policy=None,
            )
        )
        self.assertEqual(untagged["decision"], "recorded")
        self.assertIsNone(_facts(untagged)["color_transfer"])
        self.assertNotEqual(_facts(untagged)["color_transfer"], "bt709")
        self.assertEqual(_facts(untagged)["transfer_interpretation"], "untagged-hdr-looking-not-sdr")
        self.assertIn("color_transfer", _facts(untagged)["missing_fields"])
        guessed = assess(
            document(
                color_transfer=None,
                color_primaries=None,
                range=None,
                render_allowed=False,
                listed_missing_fields=["color_transfer", "color_primaries", "range"],
                rotation_degrees=0,
                rotation_policy=None,
            )
        )
        self.assertEqual(guessed["decision"], "recorded")
        self.assertTrue(any("unknown transfer was not guessed" in item for item in guessed["reasons"]))
        self.assertIsNone(_facts(guessed)["color_transfer"])
        vfr = assess(
            document(
                evidenceId="p121-vfr",
                variable_frame_rate=True,
                vfr_policy="declared-vfr",
                filename="vfr.mov",
                rotation_degrees=0,
                rotation_policy=None,
            )
        )
        self.assertEqual(vfr["decision"], "recorded")
        self.assertTrue(_facts(vfr)["variable_frame_rate"])
        bare = assess(document(variable_frame_rate=True, vfr_policy=None, rotation_degrees=0, rotation_policy=None))
        self.assertEqual(bare["decision"], "rejected")
        self.assertIn("undeclared-variable-frame-rate-policy", bare["rejectedClaims"])
        turned = assess(document(rotation_policy=None))
        self.assertEqual(turned["decision"], "rejected")
        self.assertIn("undeclared-rotation-policy", turned["rejectedClaims"])
        self.assertEqual(_facts(turned)["rotation_degrees"], 90)

    def test_cloud_metadata_is_rejected_without_being_invented(self):
        result = assess(document(cloud_metadata={"lookup": "remote-color"}))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("invented-cloud-metadata", result["rejectedClaims"])
        self.assertEqual(_facts(result)["color_transfer"], "bt709")
        self.assertTrue(any("not fetched" in item for item in result["reasons"]))
        self.assertIn("p121-portrait-clip", result["preservedResults"])

    def test_missing_fps_is_an_honest_incomplete_only_when_listed(self):
        result = assess(
            document(
                fps=None,
                render_allowed=False,
                listed_missing_fields=["fps"],
                evidenceId="p121-no-fps",
            )
        )
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("missing inspection fields block rendering: fps" in item for item in result["reasons"]))
        self.assertIsNone(_facts(result)["fps"])
        forced = assess(document(fps=None, render_allowed=True, listed_missing_fields=["fps"]))
        self.assertEqual(forced["decision"], "rejected")
        self.assertIn("render-allowed-while-blocked", forced["rejectedClaims"])

    def test_evaluate_uses_the_same_inspection(self):
        payload = document()
        payload.pop("schemaVersion")
        payload.pop("phase")
        payload.pop("implementationBaseRevision")
        payload["caseId"] = "P121"
        payload["evidenceId"] = "p121-evaluate"
        result = evaluate(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "P121")
        self.assertIn("p121-evaluate", result["preservedResults"])
        self.assertEqual(_facts(result)["frame_count"], 48)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(fps=True))
        with self.assertRaises(ValueError):
            assess(document(duration_seconds=float("nan")))
        with self.assertRaises(ValueError):
            assess(document(content_sha256="abc"))
        with self.assertRaises(ValueError):
            assess(document(video_timebase="0/1"))
        with self.assertRaises(ValueError):
            evaluate({"caseId": "P121"})
        with self.assertRaises(ValueError):
            assess(document(sourceUri="https://cloud.example/clip"))
        with self.assertRaises(ValueError):
            assess(document(audio_absent=True, audio_timebase="1/48000", audio_duration_seconds=None))
