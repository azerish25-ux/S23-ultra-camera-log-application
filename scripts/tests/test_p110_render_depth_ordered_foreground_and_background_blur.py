"""Host checks for P110. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "gates" / "p110_render_depth_ordered_foreground_and_background_blur.py"
_SPEC = importlib.util.spec_from_file_location("p110_render_depth_ordered_foreground_and_background_blur", _PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

assess = _MODULE.assess
render_depth_ordered = _MODULE.render_depth_ordered
render_uniform_gaussian = _MODULE.render_uniform_gaussian
render_unknown_as_far = _MODULE.render_unknown_as_far
classify_depth = _MODULE.classify_depth
defocus_radius = _MODULE.defocus_radius
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE
BASE_REVISION = _MODULE.BASE_REVISION
FOCUS_EPSILON = _MODULE.FOCUS_EPSILON
DEFOCUS_RADIUS_SCALE = _MODULE.DEFOCUS_RADIUS_SCALE
BLUR_RULE = _MODULE.BLUR_RULE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def strip():
    return [
        {"depth": 0.0, "value": 0.75, "layer": "foreground"},
        {"depth": 0.5, "value": 1.0, "layer": "foreground"},
        {"depth": 2.0, "value": 0.25, "layer": "focus"},
        {"depth": 2.0, "value": 0.5, "layer": "focus"},
        {"depth": 5.0, "value": 1.0, "layer": "background"},
        {"depth": 4.0, "value": 0.0, "layer": "background"},
        {"depth": None, "value": -1.0, "layer": "unknown"},
    ]


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P110",
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": "p110-branch-face-light",
        "focus": 2.0,
        "samples": strip(),
        "claim": "occlusion-aware-bokeh",
        "label": "depth-ordered",
    }
    value.update(overrides)
    return value


class P110Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(ORACLE, "The branch spreads appropriately without leaking background color through the opaque focused face.")
        self.assertEqual(MUTANT, "Apply one gather blur radius per pixel without any depth-order reasoning.")
        self.assertIn("unknown depth stays unknown", BLUR_RULE)
        self.assertEqual(DEFOCUS_RADIUS_SCALE, 1.0)

    def test_depth_ordered_strip_is_recorded_not_qualified(self):
        result = assess(document())
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P110")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p110-branch-face-light", result["preservedResults"])
        self.assertIn("occlusion-aware-bokeh", result["preservedResults"])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_focus_plane_neighbour_weight_is_zero_and_face_stays_sharp(self):
        outputs = render_depth_ordered(strip(), 2.0)
        self.assertEqual(outputs[2]["neighbourWeight"], 0.0)
        self.assertEqual(outputs[3]["neighbourWeight"], 0.0)
        self.assertEqual(outputs[2]["value"], 0.25)
        self.assertEqual(outputs[3]["value"], 0.5)
        self.assertFalse(outputs[2]["blurred"])
        near = [
            {"depth": 2.0 + FOCUS_EPSILON, "value": 0.25, "layer": "focus"},
            {"depth": 0.0, "value": 0.75, "layer": "foreground"},
        ]
        held = render_depth_ordered(near, 2.0)
        self.assertEqual(classify_depth(2.0 + FOCUS_EPSILON, 2.0), "focus")
        self.assertEqual(held[0]["neighbourWeight"], 0.0)
        self.assertEqual(held[0]["value"], 0.25)

    def test_background_radius_is_proportional_and_excludes_foreground(self):
        outputs = render_depth_ordered(strip(), 2.0)
        self.assertEqual(defocus_radius(5.0, 2.0), DEFOCUS_RADIUS_SCALE * 3.0)
        self.assertEqual(outputs[4]["radius"] / 3.0, outputs[5]["radius"] / 2.0)
        self.assertEqual(outputs[4]["foregroundWeight"], 0.0)
        self.assertEqual(outputs[5]["foregroundWeight"], 0.0)
        self.assertGreater(abs(outputs[4]["value"] - 0.75), 1e-6)
        self.assertGreater(abs(outputs[5]["value"] - 0.75), 1e-6)
        self.assertGreater(outputs[4]["neighbourWeight"], 0.0)
        self.assertLessEqual(outputs[4]["value"], 1.0)
        self.assertGreaterEqual(outputs[4]["value"], 0.0)
        self.assertAlmostEqual(outputs[4]["kernelEnergy"], 1.0)
        self.assertAlmostEqual(outputs[5]["kernelEnergy"], 1.0)

    def test_foreground_spreads_without_entering_background_bins(self):
        outputs = render_depth_ordered(strip(), 2.0)
        self.assertNotEqual(outputs[0]["value"], 0.75)
        self.assertGreater(outputs[0]["neighbourWeight"], 0.0)
        self.assertEqual(outputs[0]["layer"], "foreground")
        self.assertTrue(all(item["layer"] != "background" or item["foregroundWeight"] == 0.0 for item in outputs))

    def test_unknown_depth_stays_unknown(self):
        outputs = render_depth_ordered(strip(), 2.0)
        self.assertEqual(outputs[6]["value"], -1.0)
        self.assertEqual(outputs[6]["layer"], "unknown")
        self.assertEqual(outputs[6]["neighbourWeight"], 0.0)
        self.assertFalse(outputs[6]["blurred"])
        self.assertEqual(classify_depth(None, 2.0), "unknown")

    def test_uniform_gaussian_labelled_optical_bokeh_is_rejected(self):
        blurred = render_uniform_gaussian(strip(), 2.0)
        self.assertGreater(blurred[4]["foregroundWeight"], 0.0)
        self.assertNotEqual(blurred[2]["neighbourWeight"], 0.0)
        result = assess(document(label="optical_bokeh"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("optical_bokeh", result["rejectedClaims"])
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("foreground-bleed", result["rejectedClaims"])
        self.assertIn("focus-plane-blurred", result["rejectedClaims"])
        self.assertIn("p110-branch-face-light", result["preservedResults"])
        labelled = assess(document(claim="optical_bokeh", label="depth-ordered"))
        self.assertEqual(labelled["decision"], "rejected")
        self.assertIn("optical_bokeh", labelled["rejectedClaims"])

    def test_unknown_treated_as_far_is_rejected(self):
        illegal = render_unknown_as_far(strip(), 2.0)
        self.assertEqual(illegal[6]["layer"], "background")
        self.assertNotEqual(illegal[6]["value"], -1.0)
        self.assertTrue(illegal[6]["blurred"])
        result = assess(document(label="unknown-as-far"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unknown-treated-as-far", result["rejectedClaims"])
        self.assertIn("p110-branch-face-light", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_flat_background_keeps_normalized_energy(self):
        flat = [
            {"depth": 4.0, "value": 0.5, "layer": "background"},
            {"depth": 6.0, "value": 0.5, "layer": "background"},
            {"depth": 5.0, "value": 0.5, "layer": "background"},
        ]
        outputs = render_depth_ordered(flat, 2.0)
        for output in outputs:
            self.assertAlmostEqual(output["value"], 0.5)
            self.assertAlmostEqual(output["kernelEnergy"], 1.0)
        self.assertEqual(len(outputs), len(flat))

    def test_fixture_file_is_recorded(self):
        path = Path(__file__).resolve().parents[2] / "docs" / "P110_RENDER_DEPTH_ORDERED_FOREGROUND_AND_BACKGROUND_BLUR.json"
        loaded = json.loads(path.read_text(encoding="utf-8"))
        result = assess(loaded)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("p110-branch-face-light", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(samples=[{"depth": float("nan"), "value": 0.2, "layer": "foreground"}]))
        with self.assertRaises(ValueError):
            assess(document(samples=[{"depth": 5.0, "value": 0.2, "layer": "foreground"}]))
        with self.assertRaises(ValueError):
            assess(document(samples=[{"depth": None, "value": 0.2, "layer": "background"}]))
        with self.assertRaises(ValueError):
            assess(document(label="gather"))
        with self.assertRaises(ValueError):
            assess(document(implementationBaseRevision="not-the-spec"))
