"""Host checks for P135. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p135_build_side_by_side_comparison_tools",
    Path(__file__).resolve().parents[1] / "gates" / "p135_build_side_by_side_comparison_tools.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P135_BUILD_SIDE_BY_SIDE_COMPARISON_TOOLS.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def with_comparison(**overrides):
    value = document()
    value["comparison"] = _MODULE.make_comparison(**overrides)
    return value


def with_side(which, **overrides):
    value = document()
    value["comparison"] = _MODULE.replace_side(value["comparison"], which, **overrides)
    return value


def record_of(result):
    return result["preservedResults"][1]


class P135Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P135")
        self.assertEqual(_MODULE.WORKSTREAM, 17)
        self.assertEqual(_MODULE.TITLE, "Build side-by-side comparison tools")
        self.assertEqual(
            _MODULE.GOAL,
            "Help users judge real improvements with matched inputs and controllable viewing.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Provide synchronized playback, split views, exposure-consistent comparisons, effect bypass, "
            "and recipe metadata. Avoid comparing different moments or differently scaled thumbnails. "
            "Allow inspecting clean source and processed output without accidental double transforms.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "Two renders of the same clip with different duration mappings and different display transforms.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The comparison aligns time explicitly and makes differing transforms visible rather than "
            "implying a fair matched test.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Compare unrelated frames and automatically boost one version\u2019s contrast.",
        )
        self.assertIn("\u2019", _MODULE.MUTANT)
        self.assertEqual(_MODULE.DELIVERABLE, "Comparison viewer and synchronized playback tests")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P134",))

    def test_fixture_records_a_matched_disclosed_comparison(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P135")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn(_MODULE.MATCH_RULE, result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn("source hashes match", result["reasons"])
        self.assertIn("frames match at index 24", result["reasons"])
        self.assertIn("contrast_boost is 1 on both sides", result["reasons"])
        self.assertIn("synchronized playback offset is 0", result["reasons"])
        self.assertIn("matchedInputs=true", result["reasons"])
        self.assertIn("duration mappings differ; disclosed", result["reasons"])
        record = record_of(result)
        self.assertTrue(record["sourcesMatch"])
        self.assertTrue(record["framesMatch"])
        self.assertTrue(record["transfersDeclared"])
        self.assertTrue(record["transfersDiffer"])
        self.assertTrue(record["contrastBoostUnity"])
        self.assertFalse(record["automaticContrastBoost"])
        self.assertTrue(record["offsetAccepted"])
        self.assertTrue(record["matchedInputs"])
        self.assertEqual(record["left"]["source_sha256"], _MODULE.FIXTURE_SOURCE_SHA256)
        self.assertEqual(record["right"]["source_sha256"], _MODULE.FIXTURE_SOURCE_SHA256)
        self.assertEqual(record["left"]["frame_index"], 24)
        self.assertEqual(record["right"]["frame_index"], 24)
        self.assertEqual(record["left"]["transfer"], "bt709")
        self.assertEqual(record["right"]["transfer"], "hlg")
        self.assertEqual(record["left"]["contrast_boost"], 1.0)
        self.assertEqual(record["right"]["contrast_boost"], 1.0)
        self.assertTrue(record["transformsVisible"])
        self.assertFalse(record["impliesFairMatch"])
        self.assertEqual(record["recipeMetadata"], "print-sim-v1")
        self.assertTrue(record["effectBypass"])
        self.assertFalse(record["doubleTransform"])
        same = evaluate(source)
        self.assertEqual(same["decision"], "recorded")
        self.assertEqual(same["rejectedClaims"], [])

    def test_evaluate_payload_uses_the_match_rule(self):
        result = evaluate({
            "caseId": "TC-P135-07",
            "evidenceId": "p135-eval",
            "claim": _MODULE.CLAIM,
            "applyMutant": False,
            "comparison": _MODULE.make_comparison(),
        })
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P135-07")
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("p135-eval", result["preservedResults"])
        self.assertTrue(record_of(result)["matchedInputs"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_mismatched_frames_and_source_hashes_are_rejected(self):
        frames = assess(with_side("right", frame_index=25))
        self.assertEqual(frames["decision"], "rejected")
        self.assertIn(_MODULE.MISMATCHED_FRAMES, frames["rejectedClaims"])
        self.assertNotIn(_MODULE.MUTANT_CLAIM, frames["rejectedClaims"])
        self.assertFalse(record_of(frames)["framesMatch"])
        self.assertFalse(record_of(frames)["matchedInputs"])
        self.assertEqual(record_of(frames)["left"]["frame_index"], 24)
        self.assertEqual(record_of(frames)["right"]["frame_index"], 25)
        self.assertIn("p135-comparison", frames["preservedResults"])
        sources = assess(with_side("left", source_sha256="ab" * 32))
        self.assertEqual(sources["decision"], "rejected")
        self.assertIn(_MODULE.MISMATCHED_SOURCE, sources["rejectedClaims"])
        self.assertTrue(record_of(sources)["framesMatch"])
        self.assertFalse(record_of(sources)["sourcesMatch"])

    def test_sha_case_still_matches(self):
        result = assess(with_side("right", source_sha256=_MODULE.FIXTURE_SOURCE_SHA256.upper()))
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(record_of(result)["sourcesMatch"])
        self.assertEqual(record_of(result)["right"]["source_sha256"], _MODULE.FIXTURE_SOURCE_SHA256.upper())

    def test_contrast_boost_and_automatic_boost_are_rejected(self):
        boosted = assess(with_side("left", contrast_boost=1.25))
        self.assertEqual(boosted["decision"], "rejected")
        self.assertIn(_MODULE.CONTRAST_NOT_UNITY, boosted["rejectedClaims"])
        self.assertNotIn(_MODULE.MUTANT_CLAIM, boosted["rejectedClaims"])
        self.assertFalse(record_of(boosted)["contrastBoostUnity"])
        self.assertFalse(record_of(boosted)["matchedInputs"])
        automatic = assess(with_comparison(automatic_contrast_boost=True))
        self.assertEqual(automatic["decision"], "rejected")
        self.assertIn(_MODULE.AUTOMATIC_CONTRAST_BOOST, automatic["rejectedClaims"])
        self.assertNotIn(_MODULE.CONTRAST_NOT_UNITY, automatic["rejectedClaims"])
        self.assertTrue(record_of(automatic)["automaticContrastBoost"])
        self.assertIn("automatic contrast boost is rejected", automatic["reasons"])

    def test_unrelated_frames_with_contrast_boost_are_the_mutant(self):
        comparison = _MODULE.replace_side(
            _MODULE.make_comparison(automatic_contrast_boost=True),
            "right",
            frame_index=3,
            contrast_boost=1.8,
        )
        result = assess(document(comparison=comparison))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISMATCHED_FRAMES, result["rejectedClaims"])
        self.assertIn(_MODULE.CONTRAST_NOT_UNITY, result["rejectedClaims"])
        self.assertIn(_MODULE.AUTOMATIC_CONTRAST_BOOST, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT_CLAIM, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertIn("p135-comparison", result["preservedResults"])
        flagged = assess(document(applyMutant=True))
        self.assertEqual(flagged["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT_CLAIM, flagged["rejectedClaims"])
        self.assertTrue(record_of(flagged)["matchedInputs"])
        self.assertNotIn(flagged["decision"], {"qualified", "allowed"})

    def test_undeclared_transfer_is_rejected(self):
        result = assess(with_side("right", transfer=None))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNDECLARED_TRANSFER, result["rejectedClaims"])
        self.assertFalse(record_of(result)["transfersDeclared"])
        self.assertFalse(record_of(result)["matchedInputs"])
        blank = assess(with_side("left", transfer=""))
        self.assertIn(_MODULE.UNDECLARED_TRANSFER, blank["rejectedClaims"])

    def test_sync_offset_must_be_zero_or_disclosed(self):
        hidden = assess(with_comparison(sync_offset=2, offset_disclosed=False))
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn(_MODULE.UNDISCLOSED_OFFSET, hidden["rejectedClaims"])
        self.assertFalse(record_of(hidden)["offsetAccepted"])
        self.assertFalse(record_of(hidden)["matchedInputs"])
        shown = assess(with_comparison(sync_offset=2, offset_disclosed=True))
        self.assertEqual(shown["decision"], "recorded")
        self.assertTrue(record_of(shown)["offsetAccepted"])
        self.assertTrue(record_of(shown)["matchedInputs"])
        self.assertIn("synchronized playback offset is explicitly disclosed", shown["reasons"])

    def test_differing_transforms_stay_visible_and_are_not_a_fair_match(self):
        hidden = assess(with_comparison(transforms_visible=False))
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn(_MODULE.HIDDEN_TRANSFORMS, hidden["rejectedClaims"])
        self.assertTrue(record_of(hidden)["matchedInputs"])
        implied = assess(with_comparison(implies_fair_match=True))
        self.assertEqual(implied["decision"], "rejected")
        self.assertIn(_MODULE.FAIR_MATCH_IMPLIED, implied["rejectedClaims"])
        undisclosed = assess(with_comparison(duration_mapping_disclosed=False))
        self.assertIn(_MODULE.UNDISCLOSED_DURATION, undisclosed["rejectedClaims"])
        scaled = assess(with_comparison(scale_right=0.5))
        self.assertIn(_MODULE.DIFFERENT_SCALES, scaled["rejectedClaims"])
        fair = _MODULE.make_comparison(
            left=_MODULE.make_side(transfer="bt709"),
            right=_MODULE.make_side(transfer="BT.709"),
            duration_mapping_left="source-duration",
            duration_mapping_right="Source-Duration",
            implies_fair_match=True,
            transforms_visible=False,
        )
        matched = assess(document(comparison=fair))
        self.assertEqual(matched["decision"], "recorded")
        self.assertFalse(record_of(matched)["transfersDiffer"])
        self.assertFalse(record_of(matched)["durationMappingsDiffer"])
        self.assertTrue(record_of(matched)["impliesFairMatch"])

    def test_viewing_controls_reject_hidden_processing(self):
        doubled = assess(with_comparison(double_transform=True))
        self.assertIn(_MODULE.DOUBLE_TRANSFORM, doubled["rejectedClaims"])
        bypass = assess(with_comparison(effect_bypass=False))
        self.assertIn(_MODULE.EFFECT_BYPASS_MISSING, bypass["rejectedClaims"])
        recipe = assess(with_comparison(recipe_metadata=""))
        self.assertIn(_MODULE.RECIPE_MISSING, recipe["rejectedClaims"])
        exposure = assess(with_comparison(exposure_consistent=False))
        self.assertIn(_MODULE.EXPOSURE_INCONSISTENT, exposure["rejectedClaims"])
        split = assess(with_comparison(split_view=False))
        self.assertIn(_MODULE.SPLIT_VIEW_MISSING, split["rejectedClaims"])
        for result in (doubled, bypass, recipe, exposure, split):
            self.assertEqual(result["decision"], "rejected")
            self.assertIn("p135-comparison", result["preservedResults"])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P136"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            with_side("left", source_sha256="not-a-digest"),
            with_side("right", frame_index=-1),
            with_side("right", frame_index=True),
            with_side("right", frame_index=1.5),
            with_side("left", contrast_boost=float("nan")),
            with_side("left", contrast_boost="1"),
            with_comparison(scale_left=0),
            with_comparison(sync_offset="0"),
            with_comparison(offset_disclosed="yes"),
            evaluate,
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    assess(payload)
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate({"caseId": "TC-P135-07", "decision": "qualified"})

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P135-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P135")
        self.assertEqual(handoff["nextPhase"], "P136")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p135*.py' -v",
        )
        self.assertEqual(
            handoff["caseIds"],
            [f"TC-P135-0{index}" for index in range(1, 9)],
        )
        note = (_ROOT / "docs" / "P135_BUILD_SIDE_BY_SIDE_COMPARISON_TOOLS.md").read_text(encoding="utf-8")
        self.assertIn("Comparison viewer and synchronized playback tests", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("fixed cadence", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("source_sha256", note)
        self.assertIn("contrast_boost", note)
        self.assertIn(_MODULE.MATCH_RULE, note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p135_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p135_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P135-0{index}")
            self.assertEqual(module.CASE["phase"], "P135")
            self.assertEqual(module.CASE["workstream"], 17)
            with self.assertRaises(ValueError):
                module.evaluate({})
