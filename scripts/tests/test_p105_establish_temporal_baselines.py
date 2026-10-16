"""Host checks for P105. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import math
import statistics
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p105_establish_temporal_baselines",
    Path(__file__).resolve().parents[1] / "gates" / "p105_establish_temporal_baselines.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P105_ESTABLISH_TEMPORAL_BASELINES.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = load_document()
    value.update(overrides)
    return value


def sample_stdev(values: list[float]) -> float:
    center = sum(values) / len(values)
    return math.sqrt(sum((item - center) ** 2 for item in values) / (len(values) - 1))


class P105Tests(unittest.TestCase):
    def test_phase_constants_match_the_directive(self):
        self.assertEqual(_MODULE.PHASE, "P105")
        self.assertEqual(
            _MODULE.GOAL,
            "Measure frame-independent depth and a simple stabilized baseline before adding a complex temporal model.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Render the same sequences with no stabilization, a documented confidence-aware baseline, and candidate temporal methods. Quantify scale drift, focus pumping, edge flicker, and lag separately. Preserve per-frame depth outputs for diagnosis.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A stationary scene followed by a moving subject and a sudden camera cut.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The benchmark exposes both flicker reduction and temporal lag instead of rewarding smoothness alone.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Average depth heavily and ignore the resulting delay behind moving subjects.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Temporal baseline suite and artifact taxonomy")
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")

    def test_fixture_records_gap_flicker_and_mean_interval(self):
        source = load_document()
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P105")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn("cadence_break", " ".join(result["reasons"]))
        stamps = source["frameTimestampsMs"]
        nominal = source["nominalFramePeriodMs"]
        intervals = [stamps[index] - stamps[index - 1] for index in range(1, len(stamps))]
        luma = source["lumaMeans"]
        differences = [luma[index] - luma[index - 1] for index in range(1, len(luma))]
        metrics = result["preservedResults"][1]
        self.assertEqual(metrics["intervalsMs"], intervals)
        self.assertAlmostEqual(metrics["meanIntervalMs"], sum(intervals) / len(intervals))
        self.assertAlmostEqual(metrics["meanIntervalMs"], statistics.mean(intervals))
        self.assertEqual(metrics["maxGapMs"], max(intervals))
        self.assertAlmostEqual(metrics["maxGapRelativeToNominal"], max(intervals) / nominal)
        self.assertGreater(metrics["maxGapRelativeToNominal"], 1.5)
        self.assertAlmostEqual(metrics["flicker"], statistics.stdev(differences))
        self.assertAlmostEqual(metrics["flicker"], sample_stdev(differences))
        self.assertEqual(len(metrics["cadenceBreaks"]), 1)
        self.assertEqual(metrics["cadenceBreaks"][0]["kind"], "cadence_break")
        self.assertEqual(metrics["cadenceBreaks"][0]["intervalMs"], 160)
        self.assertNotEqual(metrics["intervalsMs"], [metrics["meanIntervalMs"]] * len(intervals))

    def test_gap_at_one_and_a_half_periods_is_not_a_break(self):
        result = assess(
            document(
                frameTimestampsMs=[0, 40, 80, 120, 160, 200, 260, 300],
                lumaMeans=[0.2, 0.22, 0.21, 0.23, 0.24, 0.22, 0.25, 0.23],
            )
        )
        self.assertEqual(result["decision"], "recorded")
        metrics = result["preservedResults"][1]
        self.assertEqual(metrics["cadenceBreaks"], [])
        self.assertAlmostEqual(metrics["maxGapRelativeToNominal"], 1.5)

    def test_gap_just_over_one_and_a_half_periods_stays_recorded(self):
        result = assess(
            document(
                frameTimestampsMs=[0, 40, 80, 120, 160, 200, 261, 301],
                lumaMeans=[0.2, 0.22, 0.21, 0.23, 0.24, 0.22, 0.25, 0.23],
            )
        )
        self.assertEqual(result["decision"], "recorded")
        metrics = result["preservedResults"][1]
        self.assertEqual(metrics["cadenceBreaks"][0]["kind"], "cadence_break")
        self.assertGreater(metrics["cadenceBreaks"][0]["relativeToNominal"], 1.5)

    def test_optional_luma_still_records_interval_metrics(self):
        result = assess(
            document(
                frameTimestampsMs=[0, 40, 80, 120, 160, 200, 240, 280],
                lumaMeans=None,
            )
        )
        self.assertEqual(result["decision"], "recorded")
        metrics = result["preservedResults"][1]
        self.assertIsNone(metrics["flicker"])
        self.assertAlmostEqual(metrics["meanIntervalMs"], 40.0)
        self.assertTrue(math.isfinite(metrics["maxGapRelativeToNominal"]))

    def test_single_still_frame_is_rejected(self):
        result = assess(document(frameTimestampsMs=[0], lumaMeans=[0.4]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("single-still-frame", result["rejectedClaims"])
        self.assertNotIn("fewer-than-eight-frames", result["rejectedClaims"])
        self.assertIn("p105-temporal-baseline", result["preservedResults"])
        self.assertIsNone(result["preservedResults"][1]["meanIntervalMs"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_fewer_than_eight_frames_is_rejected(self):
        result = assess(
            document(
                frameTimestampsMs=[0, 40, 80, 120, 160, 200, 240],
                lumaMeans=[0.2, 0.21, 0.2, 0.22, 0.21, 0.23, 0.22],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("fewer-than-eight-frames", result["rejectedClaims"])
        self.assertNotIn("single-still-frame", result["rejectedClaims"])
        self.assertAlmostEqual(result["preservedResults"][1]["meanIntervalMs"], 40.0)
        self.assertIn("p105-temporal-baseline", result["preservedResults"])

    def test_hidden_gap_is_rejected_but_break_remains(self):
        result = assess(document(hideGap=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hidden-cadence-gap", result["rejectedClaims"])
        metrics = result["preservedResults"][1]
        self.assertEqual(metrics["cadenceBreaks"][0]["kind"], "cadence_break")
        self.assertEqual(metrics["maxGapMs"], 160)
        self.assertIn(160, metrics["intervalsMs"])
        self.assertIn("p105-temporal-baseline", result["preservedResults"])

    def test_keyframe_score_is_not_the_sequence_baseline(self):
        result = assess(document(useKeyframeAsBaseline=True, keyframeScore=0.99))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("pretty-keyframe-score-as-sequence-baseline", result["rejectedClaims"])
        metrics = result["preservedResults"][1]
        self.assertNotIn("keyframeScore", metrics)
        self.assertNotEqual(metrics["meanIntervalMs"], 0.99)
        self.assertIn(160, metrics["intervalsMs"])
        self.assertIn("p105-temporal-baseline", result["preservedResults"])

    def test_ignored_keyframe_score_does_not_block_a_sequence(self):
        result = assess(
            document(
                frameTimestampsMs=[0, 40, 80, 120, 160, 200, 240, 280],
                lumaMeans=[0.2, 0.22, 0.21, 0.23, 0.24, 0.22, 0.25, 0.23],
                useKeyframeAsBaseline=False,
                keyframeScore=0.99,
            )
        )
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotEqual(result["preservedResults"][1]["meanIntervalMs"], 0.99)

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("heavy-average-ignores-subject-delay", result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertIn("p105-temporal-baseline", result["preservedResults"])
        self.assertIn(160, result["preservedResults"][1]["intervalsMs"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            document(schemaVersion=2),
            document(phase="P106"),
            document(frameTimestampsMs=[0, 0, 40, 80, 120, 160, 200, 240]),
            document(frameTimestampsMs=[0, 40], lumaMeans=[0.1]),
            document(nominalFramePeriodMs=0),
            document(frameTimestampsMs=[0, float("nan"), 80, 120, 160, 200, 240, 280]),
            document(applyMutant="no"),
            document(extra=True),
            [],
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    assess(payload)

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P105-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P105")
        self.assertEqual(handoff["nextPhase"], "P106")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        note = (_ROOT / "docs" / "P105_ESTABLISH_TEMPORAL_BASELINES.md").read_text(encoding="utf-8")
        self.assertIn("Temporal baseline suite and artifact taxonomy", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
