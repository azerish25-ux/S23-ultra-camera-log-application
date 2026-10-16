"""Host checks for P117. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p117_integrate_stabilization_with_geometry",
    Path(__file__).resolve().parents[1] / "gates" / "p117_integrate_stabilization_with_geometry.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def independent_fov(width, hfov, crop_x, crop_width):
    focal = (width / 2.0) / math.tan(math.radians(hfov) / 2.0)
    left = math.atan((crop_x - width / 2.0) / focal)
    right = math.atan((crop_x + crop_width - width / 2.0) / focal)
    return math.degrees(right - left)


def document(**overrides):
    value = _MODULE.recorded_document()
    value.update(overrides)
    return value


def blob(result):
    return " ".join(str(item) for item in result["reasons"] + result["preservedResults"])


class P117Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P117")
        self.assertEqual(_MODULE.WORKSTREAM, 15)
        self.assertEqual(_MODULE.TITLE, "Integrate stabilization with geometry")
        self.assertEqual(
            _MODULE.GOAL,
            "Keep camera-motion correction, crop, depth, and lens mapping in a shared coordinate system.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A stabilized crop that moves across the original image while a depth map remains in source coordinates.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "All render inputs align after transformation and the field-of-view report reflects the changing crop.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Stabilize RGB while leaving depth and subject masks untransformed.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Stabilization geometry contract and alignment tests")
        self.assertIn("explicit per-frame transforms", _MODULE.METHOD)
        self.assertEqual(_MODULE.DEPENDENCIES, ("P116",))

    def test_translation_crop_is_recorded_and_unknown_samples_stay_empty(self):
        fov = independent_fov(4, 90, 0, 3)
        self.assertAlmostEqual(fov, _MODULE.expected_horizontal_fov(4, 90, 0, 3))
        result = assess(document())
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P117")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p117-stabilized-crop", result["preservedResults"])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])
        self.assertIn("cropCoverage=6/8=0.75", result["preservedResults"])
        self.assertIn(
            "sample[0] layer=depth output=(1,0) source=(0,0) status=known inCrop=yes depth=0",
            result["preservedResults"],
        )
        unknown = "sample[1] layer=depth output=(0,0) source=(-1,0) status=unknown inCrop=no"
        self.assertIn(unknown, result["preservedResults"])
        self.assertNotIn("depth=", unknown)
        self.assertIn("expectedHorizontalFovDegrees=71.5650511771", blob(result))
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn(_MODULE.CROP_RULE, " ".join(result["reasons"]))

    def test_published_fixture_matches_the_recorded_crop(self):
        payload = json.loads(
            (ROOT / "docs" / "P117_INTEGRATE_STABILIZATION_WITH_GEOMETRY.json").read_text()
        )
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p117-stabilized-crop", result["preservedResults"])
        self.assertIn("cropCoverage=6/8=0.75", blob(result))
        self.assertIn("status=unknown", blob(result))
        self.assertFalse(any("status=unknown" in item and "depth=" in item for item in result["preservedResults"]))

    def test_coverage_one_is_recorded_only_for_a_zero_warp(self):
        geometry = _MODULE.recorded_geometry()
        geometry["warp"] = {"dx": 0.0, "dy": 0.0}
        geometry["layers"] = {name: {"dx": 0.0, "dy": 0.0} for name in ("rgb", "depth", "mask")}
        geometry["corrections"] = [{"kind": "post", "dx": 0.0, "dy": 0.0, "known": True}]
        geometry["crop"] = {"x": 0.0, "y": 0.0, "width": 4.0, "height": 2.0}
        geometry["cropRecorded"] = False
        geometry["stabilized"] = {"lensId": "s23-main", "timestamp": 0.0, "aspect": 2.0}
        geometry["reportedHorizontalFovDegrees"] = 90.0
        geometry["samples"] = [{"x": 0.5, "y": 0.5, "layer": "depth"}]
        payload = document()
        payload.update(geometry)
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("cropCoverage=8/8=1", blob(result))

    def test_full_frame_nonzero_translation_hides_lost_borders(self):
        geometry = _MODULE.recorded_geometry()
        geometry["crop"] = {"x": 0.0, "y": 0.0, "width": 4.0, "height": 2.0}
        geometry["stabilized"] = {"lensId": "s23-main", "timestamp": 0.0, "aspect": 2.0}
        geometry["reportedHorizontalFovDegrees"] = independent_fov(4, 90, 0, 4)
        payload = document()
        payload.update(geometry)
        result = assess(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FULL_FRAME_HIDES_BORDERS, result["rejectedClaims"])
        self.assertIn(_MODULE.CROP_OUTSIDE_VALID, result["rejectedClaims"])
        self.assertNotIn(_MODULE.FOV_MISMATCH, result["rejectedClaims"])
        self.assertIn("cropCoverage=8/8=1", blob(result))
        self.assertIn("p117-stabilized-crop", result["preservedResults"])

    def test_partial_crop_that_includes_the_lost_border_is_rejected(self):
        geometry = _MODULE.recorded_geometry()
        geometry["crop"] = {"x": 0.0, "y": 0.0, "width": 3.5, "height": 2.0}
        geometry["stabilized"] = {"lensId": "s23-main", "timestamp": 0.0, "aspect": 1.75}
        geometry["reportedHorizontalFovDegrees"] = independent_fov(4, 90, 0, 3.5)
        payload = document()
        payload.update(geometry)
        result = assess(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CROP_OUTSIDE_VALID, result["rejectedClaims"])
        self.assertNotIn(_MODULE.FULL_FRAME_HIDES_BORDERS, result["rejectedClaims"])
        self.assertIn("cropCoverage=7/8=0.875", blob(result))

    def test_generated_fill_and_inpaint_are_rejected_without_texture(self):
        generated = document()
        generated["fill"] = "generated"
        result = assess(generated)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GENERATED_FILL, result["rejectedClaims"])
        unknown = [item for item in result["preservedResults"] if "status=unknown" in item]
        self.assertTrue(unknown)
        self.assertTrue(all("depth=" not in item for item in unknown))

        painted = document()
        painted["inpaint"] = True
        painted["samples"] = [{"x": 1.0, "y": 0.0, "layer": "depth"}]
        result = assess(painted)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.INPAINT, result["rejectedClaims"])
        self.assertIn("depth=0", blob(result))

    def test_unrecorded_aspect_or_lens_change_is_rejected(self):
        geometry = _MODULE.recorded_geometry()
        geometry["cropRecorded"] = False
        payload = document()
        payload.update(geometry)
        result = assess(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNRECORDED_ASPECT, result["rejectedClaims"])

        geometry = _MODULE.recorded_geometry()
        geometry["warp"] = {"dx": 0.0, "dy": 0.0}
        geometry["layers"] = {name: {"dx": 0.0, "dy": 0.0} for name in ("rgb", "depth", "mask")}
        geometry["corrections"] = [{"kind": "post", "dx": 0.0, "dy": 0.0, "known": True}]
        geometry["crop"] = {"x": 0.0, "y": 0.0, "width": 4.0, "height": 2.0}
        geometry["cropRecorded"] = False
        geometry["stabilized"] = {"lensId": "virtual-50", "timestamp": 0.0, "aspect": 2.0}
        geometry["reportedHorizontalFovDegrees"] = 90.0
        payload = document()
        payload.update(geometry)
        result = assess(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DROPPED_LENS, result["rejectedClaims"])
        self.assertIn(_MODULE.UNRECORDED_LENS, result["rejectedClaims"])
        self.assertIn("sourceLensId=s23-main", blob(result))

    def test_recorded_lens_change_still_drops_identity(self):
        payload = document()
        payload["stabilized"] = {"lensId": "virtual-50", "timestamp": 0.0, "aspect": 1.5}
        result = assess(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DROPPED_LENS, result["rejectedClaims"])
        self.assertNotIn(_MODULE.UNRECORDED_LENS, result["rejectedClaims"])

    def test_dropped_timestamp_is_rejected(self):
        payload = document()
        payload["stabilized"] = {"lensId": "s23-main", "timestamp": 1.0, "aspect": 1.5}
        result = assess(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DROPPED_TIMESTAMP, result["rejectedClaims"])
        self.assertIn("sourceTimestamp=0", blob(result))

    def test_depth_and_mask_must_share_the_rgb_translation(self):
        payload = document()
        payload["layers"] = {
            "rgb": {"dx": 1.0, "dy": 0.0},
            "depth": {"dx": 0.0, "dy": 0.0},
            "mask": {"dx": 1.0, "dy": 0.0},
        }
        result = assess(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DEPTH_UNTRANSFORMED, result["rejectedClaims"])
        self.assertIn(_MODULE.DEPTH_LEFT_IN_SOURCE, result["rejectedClaims"])
        self.assertIn(
            "sample[0] layer=depth output=(1,0) source=(1,0) status=known inCrop=yes depth=1",
            result["preservedResults"],
        )

        payload = document()
        payload["layers"] = {
            "rgb": {"dx": 1.0, "dy": 0.0},
            "depth": {"dx": 1.0, "dy": 0.0},
            "mask": {"dx": 0.0, "dy": 0.0},
        }
        result = assess(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MASK_UNTRANSFORMED, result["rejectedClaims"])

    def test_mutant_flag_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn("p117-stabilized-crop", result["preservedResults"])
        self.assertIn("cropCoverage=6/8=0.75", blob(result))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_unknown_correction_is_not_stacked(self):
        payload = document()
        payload["corrections"] = [
            {"kind": "eis", "dx": 1.0, "dy": 0.0, "known": False},
        ]
        result = assess(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNKNOWN_CORRECTION, result["rejectedClaims"])
        self.assertIn(_MODULE.WARP_CORRECTION_MISMATCH, result["rejectedClaims"])

    def test_stale_field_of_view_is_rejected(self):
        payload = document()
        payload["reportedHorizontalFovDegrees"] = 90.0
        result = assess(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FOV_MISMATCH, result["rejectedClaims"])

    def test_crop_outside_the_source_is_rejected(self):
        payload = document()
        payload["crop"] = {"x": -1.0, "y": 0.0, "width": 3.0, "height": 2.0}
        result = assess(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CROP_OUTSIDE_SOURCE, result["rejectedClaims"])
        self.assertIn("cropCoverage=", blob(result))

    def test_negative_translation_reads_the_shifted_source_pixel(self):
        geometry = _MODULE.recorded_geometry()
        geometry["warp"] = {"dx": -1.0, "dy": 0.0}
        geometry["layers"] = {name: {"dx": -1.0, "dy": 0.0} for name in ("rgb", "depth", "mask")}
        geometry["corrections"] = [{"kind": "post", "dx": -1.0, "dy": 0.0, "known": True}]
        geometry["crop"] = {"x": 1.0, "y": 0.0, "width": 3.0, "height": 2.0}
        geometry["reportedHorizontalFovDegrees"] = independent_fov(4, 90, 1, 3)
        geometry["samples"] = [{"x": 0.0, "y": 0.0, "layer": "depth"}]
        payload = document()
        payload.update(geometry)
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn(
            "sample[0] layer=depth output=(0,0) source=(1,0) status=known inCrop=yes depth=1",
            result["preservedResults"],
        )

    def test_evaluate_uses_the_same_contract(self):
        payload = _MODULE.recorded_document()
        payload.pop("schemaVersion")
        payload.pop("phase")
        payload.pop("implementationBaseRevision")
        payload["caseId"] = "TC-P117-05"
        result = evaluate(payload)
        self.assertEqual(result["caseId"], "TC-P117-05")
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("cropCoverage=6/8=0.75", blob(result))

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            evaluate({})
        payload = document()
        payload["warp"] = {"dx": float("nan"), "dy": 0.0}
        with self.assertRaises(ValueError):
            assess(payload)
        payload = document()
        payload["crop"] = {"x": 0.0, "y": 0.0, "width": -1.0, "height": 2.0}
        with self.assertRaises(ValueError):
            assess(payload)
        payload = document()
        payload["implementationBaseRevision"] = "deadbeef"
        with self.assertRaises(ValueError):
            assess(payload)

    def test_handoff_points_at_p118(self):
        handoff = json.loads((ROOT / "docs" / "evidence" / "P117-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P117")
        self.assertEqual(handoff["commit"], None)
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(handoff["nextPhase"], "P118")
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p117*.py' -v",
        )
        self.assertIn("TC-P117-01", handoff["caseIds"])
        self.assertIn("TC-P117-08", handoff["caseIds"])
