"""Tests for TC-P142-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p142_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p142_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p142-tc07",
        "repeat": "faces",
        "source": _GATE.fixture_source(),
        "reference": _GATE.fixture_reference(),
        "suggestion": _GATE.fixture_suggestion(),
        "subject": "faces",
        "altered": False,
        "visuallySimilar": False,
    }
    base.update(overrides)
    return base


class TCP14207(unittest.TestCase):
    def assert_contract(self, result, evidence="p142-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P142-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertFalse(result["preservedResults"][1]["newSource"])

    def test_bounded_parameters_are_recorded_for_each_subject(self):
        for subject in ("faces", "text", "fine-patterns", "moving-objects"):
            result = evaluate(payload(subject=subject, repeat=subject, evidenceId="p142-tc07-" + subject))
            self.assert_contract(result, "p142-tc07-" + subject)
            self.assertEqual(result["decision"], "recorded")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertEqual(result["preservedResults"][1]["role"], "parameter-suggestion")
            self.assertEqual(result["preservedResults"][1]["method"], "parameters")
            self.assertEqual(
                result["preservedResults"][2]["parameters"],
                ("exposure", "contrast", "saturation"),
            )

    def test_similar_generated_scene_is_not_camera_footage(self):
        suggestion = _GATE.fixture_suggestion()
        suggestion["method"] = "stylize"
        suggestion["output_sha256"] = _GATE.ALTERED_OUTPUT_SHA256
        suggestion["label"] = "source-footage"
        suggestion["changes_facial_geometry"] = True
        suggestion["face_landmark_drift"] = 0.2
        result = evaluate(payload(suggestion=suggestion, altered=True, visuallySimilar=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_GATE.STYLIZE_CHANGED_PIXELS, result["rejectedClaims"])
        self.assertIn(_GATE.LABELLED_SOURCE_FOOTAGE, result["rejectedClaims"])
        self.assertIn(_GATE.LANDMARK_DRIFT, result["rejectedClaims"])
        self.assertIn(_GATE.FACIAL_GEOMETRY, result["rejectedClaims"])
        self.assertIn(_MODULE.SYNTHESIS, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)
        self.assertFalse(result["preservedResults"][1]["newSource"])

    def test_texture_replacement_is_rejected(self):
        suggestion = _GATE.fixture_suggestion()
        suggestion["replaces_scene_texture"] = True
        result = evaluate(payload(
            suggestion=suggestion,
            subject="fine-patterns",
            altered=True,
            visuallySimilar=True,
            repeat="fine-patterns",
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.SCENE_TEXTURE, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_parameter_outside_bounds_is_rejected(self):
        source = _GATE.make_source(mean_luma=0.5)
        reference = _GATE.make_reference(mean_luma=4.0)
        fit = _GATE.fit_bounded_parameters(source, reference)
        suggestion = _GATE.make_suggestion(
            exposure=fit["exposure"],
            contrast=fit["contrast"],
            saturation=fit["saturation"],
            output_sha256=source["source_sha256"],
        )
        result = evaluate(payload(source=source, reference=reference, suggestion=suggestion, repeat="moving-objects"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.PARAMETER_OUT_OF_BOUNDS, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(subject="sky"))
