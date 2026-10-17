"""Host checks for P142. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p142_implement_constrained_reference_matching",
    Path(__file__).resolve().parents[1] / "gates" / "p142_implement_constrained_reference_matching.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P142_IMPLEMENT_CONSTRAINED_REFERENCE_MATCHING.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def suggestion_with(**overrides):
    value = document()
    suggestion = dict(value["suggestion"])
    suggestion.update(overrides)
    value["suggestion"] = suggestion
    return value


def fitted(source_overrides=None, reference_overrides=None, suggestion_overrides=None):
    source = _MODULE.make_source(**(source_overrides or {}))
    reference = _MODULE.make_reference(**(reference_overrides or {}))
    fit = _MODULE.fit_bounded_parameters(source, reference)
    suggestion = _MODULE.make_suggestion(
        exposure=fit["exposure"],
        contrast=fit["contrast"],
        saturation=fit["saturation"],
        output_sha256=source["source_sha256"],
    )
    if suggestion_overrides:
        suggestion.update(suggestion_overrides)
    return document(source=source, reference=reference, suggestion=suggestion)


def record(result):
    return result["preservedResults"][1]


class P142Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p142-reference-match"):
        self.assertEqual(tuple(result), KEYS)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])
        self.assertFalse(record(result)["newSource"])

    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P142")
        self.assertEqual(_MODULE.WORKSTREAM, 18)
        self.assertEqual(_MODULE.TITLE, "Implement constrained reference matching")
        self.assertEqual(
            _MODULE.GOAL,
            "Use optional analysis to suggest renderer parameters without replacing source content.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Analyze approved reference material for broad color, tone, texture, and contrast characteristics. "
            "Fit bounded parameters in our renderer, preserve scene structure, and expose the result as a suggestion. "
            "Keep lighting and composition mismatch visible as limitations.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A reference shot with dramatic directional lighting and a user source recorded under flat overhead light.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The tool proposes a bounded grade but does not claim to recreate the missing lighting geometry.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Use unconstrained neural stylization and call altered faces faithful source footage.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Parameter suggestion prototype and structure-preservation tests")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P141",))
        self.assertEqual(_MODULE.PARAMETER_NAMES, ("exposure", "contrast", "saturation"))
        self.assertEqual(_MODULE.DECLARED_BOUNDS["exposure"], (-2.0, 2.0))
        self.assertEqual(_MODULE.DECLARED_BOUNDS["contrast"], (0.5, 1.5))
        self.assertEqual(_MODULE.DECLARED_BOUNDS["saturation"], (0.0, 2.0))
        self.assertEqual(_MODULE.MAX_FACE_LANDMARK_DRIFT, 0.02)
        self.assertEqual(_MODULE.METHOD_STYLIZE, "stylize")
        self.assertEqual(_MODULE.METHOD_PARAMETERS, "parameters")

    def test_fixture_records_a_parameter_suggestion_not_a_new_source(self):
        source = load_document()
        result = assess(source)
        self.assert_contract(result, source["evidenceId"])
        self.assertEqual(result["caseId"], "P142")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn("recorded as a parameter suggestion, not a new source", result["reasons"])
        self.assertIn("texture_energy analyzed; not a renderer parameter", result["reasons"])
        kept = record(result)
        self.assertEqual(kept["role"], "parameter-suggestion")
        self.assertEqual(kept["source_sha256"], _MODULE.FIXTURE_SOURCE_SHA256)
        self.assertEqual(kept["output_sha256"], _MODULE.FIXTURE_SOURCE_SHA256)
        self.assertTrue(kept["hashMatchesSource"])
        self.assertTrue(kept["withinBounds"])
        self.assertEqual(kept["method"], "parameters")
        self.assertEqual(kept["label"], "parameter-suggestion")
        self.assertEqual(kept["limitations"], ["lighting-geometry-mismatch", "composition-mismatch"])
        fit = _MODULE.fit_bounded_parameters(source["source"], source["reference"])
        self.assertTrue(math.isclose(kept["exposure"], fit["exposure"]))
        self.assertTrue(math.isclose(kept["contrast"], fit["contrast"]))
        self.assertTrue(math.isclose(kept["saturation"], fit["saturation"]))
        self.assertTrue(_MODULE.value_in_bounds("exposure", fit["exposure"]))
        self.assertTrue(_MODULE.value_in_bounds("contrast", fit["contrast"]))
        self.assertTrue(_MODULE.value_in_bounds("saturation", fit["saturation"]))
        self.assertIn("lighting geometry was not recreated from the reference", result["openQuestions"])
        evaluated = evaluate({
            "caseId": "P142",
            "evidenceId": source["evidenceId"],
            "claim": source["claim"],
            "applyMutant": False,
            "source": source["source"],
            "reference": source["reference"],
            "suggestion": source["suggestion"],
        })
        self.assertEqual(evaluated["decision"], "recorded")
        self.assertEqual(evaluated["rejectedClaims"], result["rejectedClaims"])
        self.assertEqual(record(evaluated)["role"], "parameter-suggestion")

    def test_hash_difference_labelled_source_footage_is_rejected(self):
        for label in ("source-footage", "faithful-source"):
            result = assess(suggestion_with(
                output_sha256=_MODULE.ALTERED_OUTPUT_SHA256,
                label=label,
            ))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "rejected")
            self.assertIn(_MODULE.LABELLED_SOURCE_FOOTAGE, result["rejectedClaims"])
            self.assertIn(_MODULE.HASH_CHANGED, result["rejectedClaims"])
            self.assertEqual(record(result)["source_sha256"], _MODULE.FIXTURE_SOURCE_SHA256)
            self.assertNotEqual(record(result)["output_sha256"], record(result)["source_sha256"])
            self.assertFalse(record(result)["newSource"])
            self.assertIn("p142-reference-match", result["preservedResults"])

    def test_stylize_that_changes_pixels_is_not_faithful_source(self):
        result = assess(suggestion_with(
            method="stylize",
            output_sha256=_MODULE.ALTERED_OUTPUT_SHA256,
            label="faithful-source",
            changes_facial_geometry=True,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STYLIZE_CHANGED_PIXELS, result["rejectedClaims"])
        self.assertIn(_MODULE.NON_PARAMETER_METHOD, result["rejectedClaims"])
        self.assertIn(_MODULE.LABELLED_SOURCE_FOOTAGE, result["rejectedClaims"])
        self.assertIn(_MODULE.FACIAL_GEOMETRY, result["rejectedClaims"])
        self.assertIn("not faithful source footage", " ".join(result["reasons"]))
        self.assertFalse(record(result)["newSource"])
        self.assertIn(_MODULE.FIXTURE_SOURCE_SHA256, record(result)["source_sha256"])

    def test_stylize_without_pixel_change_is_still_not_a_parameter_suggestion(self):
        result = assess(suggestion_with(method="Stylize"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NON_PARAMETER_METHOD, result["rejectedClaims"])
        self.assertNotIn(_MODULE.STYLIZE_CHANGED_PIXELS, result["rejectedClaims"])

    def test_face_landmark_drift_above_max_is_rejected(self):
        at_max = assess(suggestion_with(face_landmark_drift=_MODULE.MAX_FACE_LANDMARK_DRIFT))
        self.assertEqual(at_max["decision"], "recorded")
        self.assertEqual(record(at_max)["faceLandmarkDrift"], 0.02)
        missing = assess(suggestion_with(face_landmark_drift=None))
        self.assertEqual(missing["decision"], "recorded")
        over = assess(suggestion_with(face_landmark_drift=_MODULE.MAX_FACE_LANDMARK_DRIFT + 1e-6))
        self.assertEqual(over["decision"], "rejected")
        self.assertIn(_MODULE.LANDMARK_DRIFT, over["rejectedClaims"])
        self.assertIn("p142-reference-match", over["preservedResults"])

    def test_suggestions_outside_declared_bounds_are_rejected(self):
        exposure = fitted({"mean_luma": 0.5}, {"mean_luma": 4.0})
        exposure_result = assess(exposure)
        self.assertEqual(exposure_result["decision"], "rejected")
        self.assertIn(_MODULE.PARAMETER_OUT_OF_BOUNDS, exposure_result["rejectedClaims"])
        self.assertIn("exposure", " ".join(exposure_result["reasons"]))
        contrast = fitted({}, {"contrast": 0.25})
        self.assertIn(_MODULE.PARAMETER_OUT_OF_BOUNDS, assess(contrast)["rejectedClaims"])
        saturation = fitted({}, {"saturation": 3.0})
        saturation_result = assess(saturation)
        self.assertEqual(saturation_result["decision"], "rejected")
        self.assertIn("saturation", " ".join(saturation_result["reasons"]))
        smuggled = suggestion_with(exposure=9.0)
        smuggled_result = assess(smuggled)
        self.assertIn(_MODULE.PARAMETER_OUT_OF_BOUNDS, smuggled_result["rejectedClaims"])
        self.assertIn(_MODULE.FIT_MISMATCH, smuggled_result["rejectedClaims"])

    def test_bounds_are_inclusive_and_sha_case_does_not_change_the_source(self):
        high = fitted({"mean_luma": 0.25}, {"mean_luma": 1.0})
        self.assertEqual(assess(high)["decision"], "recorded")
        self.assertTrue(math.isclose(record(assess(high))["exposure"], 2.0))
        low = fitted({"mean_luma": 1.0}, {"mean_luma": 0.25})
        self.assertEqual(assess(low)["decision"], "recorded")
        self.assertTrue(math.isclose(record(assess(low))["exposure"], -2.0))
        contrast = fitted({"contrast": 1.0}, {"contrast": 0.5, "saturation": 0.0})
        contrast_result = assess(contrast)
        self.assertEqual(contrast_result["decision"], "recorded")
        self.assertTrue(math.isclose(record(contrast_result)["contrast"], 0.5))
        self.assertTrue(math.isclose(record(contrast_result)["saturation"], 0.0))
        wide = fitted({}, {"saturation": 2.0, "contrast": 1.5})
        self.assertEqual(assess(wide)["decision"], "recorded")
        cased = suggestion_with(output_sha256=_MODULE.FIXTURE_SOURCE_SHA256.upper())
        cased_result = assess(cased)
        self.assertEqual(cased_result["decision"], "recorded")
        self.assertTrue(record(cased_result)["hashMatchesSource"])
        self.assertEqual(record(cased_result)["role"], "parameter-suggestion")

    def test_geometry_texture_new_source_and_unapproved_reference_are_rejected(self):
        facial = assess(suggestion_with(changes_facial_geometry=True))
        self.assertIn(_MODULE.FACIAL_GEOMETRY, facial["rejectedClaims"])
        texture = assess(suggestion_with(replaces_scene_texture=True))
        self.assertIn(_MODULE.SCENE_TEXTURE, texture["rejectedClaims"])
        claimed = assess(suggestion_with(claims_new_source=True))
        self.assertEqual(claimed["decision"], "rejected")
        self.assertIn(_MODULE.NEW_SOURCE, claimed["rejectedClaims"])
        self.assertFalse(record(claimed)["newSource"])
        lighting = assess(suggestion_with(recreates_lighting_geometry=True))
        self.assertIn(_MODULE.LIGHTING_GEOMETRY, lighting["rejectedClaims"])
        self.assertIn(_MODULE.ORACLE, lighting["reasons"])
        unapproved = document()
        unapproved["reference"] = _MODULE.make_reference(approved=False)
        unapproved_result = assess(unapproved)
        self.assertIn(_MODULE.UNAPPROVED_REFERENCE, unapproved_result["rejectedClaims"])

    def test_mutant_flag_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertIn("p142-reference-match", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertFalse(record(result)["newSource"])

    def test_same_hash_mislabeled_as_source_footage_is_not_recorded_as_source(self):
        result = assess(suggestion_with(label="source-footage"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISLABELLED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.LABELLED_SOURCE_FOOTAGE, result["rejectedClaims"])
        self.assertEqual(record(result)["source_sha256"], _MODULE.FIXTURE_SOURCE_SHA256)

    def test_not_source_footage_catalogue(self):
        text = " ".join(_MODULE.NOT_SOURCE_FOOTAGE)
        self.assertIn("output_sha256", text)
        self.assertIn("source footage", text)
        self.assertIn("stylize", text)
        self.assertIn("face landmark drift", text)
        self.assertIn("bounds", text)
        self.assertIn("not a new source", text)
        self.assertIn("generated scene", text)

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P143"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            suggestion_with(output_sha256="not-a-digest"),
            suggestion_with(exposure=float("nan")),
            suggestion_with(face_landmark_drift=-0.01),
            suggestion_with(method=""),
            suggestion_with(label="looks-like-film"),
            document(source=_MODULE.make_source(mean_luma=0)),
            document(source=_MODULE.make_source(contrast=0)),
            suggestion_with(claims_new_source="no"),
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    assess(payload)
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P142-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P142")
        self.assertEqual(handoff["nextPhase"], "P143")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(handoff["nonClaims"], "Host reference only. Not a physical S23 qualification.")
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p142*.py' -v",
        )
        note = (_ROOT / "docs" / "P142_IMPLEMENT_CONSTRAINED_REFERENCE_MATCHING.md").read_text(encoding="utf-8")
        self.assertIn("Parameter suggestion prototype and structure-preservation tests", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("source_sha256", note)
        self.assertIn("stylize", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p142_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p142_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P142-0{index}")
            self.assertEqual(module.CASE["phase"], "P142")
            self.assertEqual(module.CASE["workstream"], 18)
            with self.assertRaises(ValueError):
                module.evaluate({})
