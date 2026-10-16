"""Host checks for P112. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import math
import statistics
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p112_qualify_temporal_lens_quality_at_normal_playback",
    Path(__file__).resolve().parents[1] / "gates" / "p112_qualify_temporal_lens_quality_at_normal_playback.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
temporal_metrics = _MODULE.temporal_metrics
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE
BASE_REVISION = _MODULE.BASE_REVISION
OPEN_QUESTION = _MODULE.OPEN_QUESTION

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
BRIGHTNESS = [0.40, 0.42, 0.41, 0.43, 0.40, 0.44, 0.41, 0.42]
EDGE = [0.80, 0.81, 0.79, 0.82, 0.78, 0.80, 0.81, 0.79]
FOCUS = [2.0, 2.0, 2.1, 2.1, 2.0, 2.2, 2.2, 2.0]


def calm_frames(severity=0.1, focus=None, count=8):
    distances = FOCUS if focus is None else focus
    frames = []
    for index in range(count):
        if isinstance(severity, list):
            boundary = severity[index]
        else:
            boundary = severity
        frames.append({
            "edge_energy": EDGE[index % len(EDGE)],
            "brightness": BRIGHTNESS[index % len(BRIGHTNESS)],
            "focus_distance": distances[index % len(distances)],
            "boundary_severity": boundary,
        })
    return frames


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P112",
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": "p112-playback",
        "claim": "synthetic-host-fixture",
        "playback_fps": 24,
        "frames": calm_frames(),
        "flicker_limit": 0.05,
        "edge_crawl_limit": 0.05,
        "severity_limit": 1.0,
        "still_as_playback": False,
        "still_sharpness": 0.92,
        "measured_on_device": False,
        "claims_physical_lens_qualification": False,
        "applyMutant": False,
    }
    value.update(overrides)
    return value


def _metric(result, name):
    token = name + "="
    for item in result["preservedResults"]:
        if item.startswith(token):
            raw = item[len(token):]
            if raw == "uncomputed":
                return None
            return float(raw)
    raise AssertionError(name + " missing")


class P112Tests(unittest.TestCase):
    def test_fixture_json_is_recorded_not_qualified(self):
        path = Path(__file__).resolve().parents[2] / "docs" / "P112_QUALIFY_TEMPORAL_LENS_QUALITY_AT_NORMAL_PLAYBACK.json"
        fixture = json.loads(path.read_text())
        result = assess(fixture)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P112")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p112-playback", result["preservedResults"])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertIn(OPEN_QUESTION, result["openQuestions"])

    def test_metrics_match_sample_stdev_and_breathing_is_reported(self):
        frames = calm_frames()
        result = assess(document(frames=frames))
        brightness_deltas = [BRIGHTNESS[i] - BRIGHTNESS[i - 1] for i in range(1, 8)]
        edge_deltas = [EDGE[i] - EDGE[i - 1] for i in range(1, 8)]
        self.assertAlmostEqual(_metric(result, "flicker"), statistics.stdev(brightness_deltas))
        self.assertAlmostEqual(_metric(result, "edge_crawl"), statistics.stdev(edge_deltas))
        self.assertAlmostEqual(_metric(result, "focus_distance_variance"), statistics.variance(FOCUS))
        self.assertTrue(any("focus_distance variance is not hidden" in item for item in result["reasons"]))
        self.assertGreater(_metric(result, "focus_distance_variance"), 0.0)

    def test_flicker_over_limit_is_not_averaged_into_a_pass(self):
        frames = calm_frames()
        for frame in frames:
            frame["edge_energy"] = 0.2
        alternating = [0.0, 1.0] * 4
        for index, frame in enumerate(frames):
            frame["brightness"] = alternating[index]
        result = assess(document(frames=frames, flicker_limit=0.01, edge_crawl_limit=1.0))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("flicker-exceeds-declared-limit", result["rejectedClaims"])
        self.assertNotIn("edge-crawl-exceeds-declared-limit", result["rejectedClaims"])
        self.assertIn("p112-playback", result["preservedResults"])
        self.assertGreater(_metric(result, "flicker"), 0.01)
        self.assertEqual(_metric(result, "edge_crawl"), 0.0)

    def test_edge_crawl_over_limit_is_rejected_alone(self):
        frames = calm_frames()
        for frame in frames:
            frame["brightness"] = 0.4
        for index, frame in enumerate(frames):
            frame["edge_energy"] = float(index % 2)
        result = assess(document(frames=frames, flicker_limit=0.0, edge_crawl_limit=0.01))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("edge-crawl-exceeds-declared-limit", result["rejectedClaims"])
        self.assertNotIn("flicker-exceeds-declared-limit", result["rejectedClaims"])
        self.assertEqual(_metric(result, "flicker"), 0.0)

    def test_metric_equal_to_the_limit_is_recorded(self):
        frames = calm_frames()
        metrics = temporal_metrics(frames)
        result = assess(document(
            frames=frames,
            flicker_limit=metrics["flicker"],
            edge_crawl_limit=metrics["edge_crawl"],
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_limit_just_below_the_metric_is_rejected(self):
        frames = calm_frames()
        metrics = temporal_metrics(frames)
        result = assess(document(
            frames=frames,
            flicker_limit=math.nextafter(metrics["flicker"], 0.0),
            edge_crawl_limit=metrics["edge_crawl"],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("flicker-exceeds-declared-limit", result["rejectedClaims"])

    def test_short_sequence_is_rejected_and_metrics_stay_visible(self):
        frames = calm_frames(count=7)
        result = assess(document(frames=frames))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("frame-count-below-playback-minimum", result["rejectedClaims"])
        self.assertIsNotNone(_metric(result, "flicker"))
        self.assertIsNotNone(_metric(result, "focus_distance_variance"))
        self.assertIn("p112-playback", result["preservedResults"])

    def test_empty_sequence_is_rejected(self):
        result = assess(document(frames=[]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("frame-count-below-playback-minimum", result["rejectedClaims"])
        self.assertIsNone(_metric(result, "flicker"))

    def test_still_sharpness_cannot_qualify_playback(self):
        result = assess(document(still_as_playback=True, still_sharpness=100.0))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("still-frame-sharpness-cannot-qualify-playback", result["rejectedClaims"])
        self.assertIn("still_sharpness=100.0", result["preservedResults"])

    def test_physical_claim_without_measurement_is_rejected(self):
        result = assess(document(claims_physical_lens_qualification=True, measured_on_device=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("physical-lens-qualification-without-measured-on-device", result["rejectedClaims"])
        self.assertIn(OPEN_QUESTION, result["openQuestions"])

    def test_physical_claim_with_flag_is_recorded_not_qualified(self):
        result = assess(document(claims_physical_lens_qualification=True, measured_on_device=True))
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertNotIn("physical-lens-qualification-without-measured-on-device", result["rejectedClaims"])
        self.assertIn(OPEN_QUESTION, result["openQuestions"])

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("p112-playback", result["preservedResults"])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])

    def test_thirty_fps_is_accepted_and_other_rates_raise(self):
        self.assertEqual(assess(document(playback_fps=30))["decision"], "recorded")
        for fps in (25, 23, 60, 24.0, True, "24"):
            with self.assertRaises(ValueError):
                assess(document(playback_fps=fps))

    def test_severe_boundary_is_not_hidden_by_a_favorable_mean(self):
        severity = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 5.0]
        result = assess(document(frames=calm_frames(severity=severity), severity_limit=1.0))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("severe-boundary-failure-not-averaged-into-a-pass", result["rejectedClaims"])
        self.assertLess(_metric(result, "mean_boundary_severity"), 1.0)
        self.assertGreater(_metric(result, "peak_boundary_severity"), 1.0)
        self.assertIn("catastrophic_frames=7", result["preservedResults"])

    def test_invalid_document_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(phase="P111"))
        with self.assertRaises(ValueError):
            assess(document(implementationBaseRevision="0" * 40))
        with self.assertRaises(ValueError):
            bad = document()
            bad["frames"][0]["brightness"] = float("nan")
            assess(bad)
        with self.assertRaises(ValueError):
            bad = document()
            bad["frames"][0]["brightness"] = True
            assess(bad)
        with self.assertRaises(ValueError):
            bad = document()
            del bad["frames"]
            assess(bad)
        with self.assertRaises(ValueError):
            bad = document()
            bad["extra"] = 1
            assess(bad)
        with self.assertRaises(ValueError):
            assess(document(evidenceId=" padded"))
        with self.assertRaises(ValueError):
            bad = document()
            bad["frames"][0]["focus_distance"] = 0.0
            assess(bad)
