"""Host checks for P119. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p119_add_practical_cinematographic_guidance",
    Path(__file__).resolve().parents[1] / "gates" / "p119_add_practical_cinematographic_guidance.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

_ROOT = Path(__file__).resolve().parents[2]
_KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _limit():
    return {
        "id": "mode-48",
        "fps": 48.0,
        "shutter_angle": 172.8,
        "max_stable_motion_px": 6.0,
        "mode_available": True,
    }


def _statements():
    return [
        {
            "text": _MODULE.HONEST_180,
            "limitId": "mode-48",
            "recommendsFps": None,
            "recommendsShutter": None,
            "observedMotionPx": 2.0,
            "claimsStableMotion": True,
            "promises": [],
        },
        {
            "text": "the face is clipped; guidance will not restore it",
            "limitId": "mode-48",
            "recommendsFps": None,
            "recommendsShutter": None,
            "observedMotionPx": None,
            "claimsStableMotion": False,
            "promises": [],
        },
        {
            "text": "the source is physically out of focus; a virtual shallow-focus recipe will not restore focus",
            "limitId": "mode-48",
            "recommendsFps": None,
            "recommendsShutter": None,
            "observedMotionPx": None,
            "claimsStableMotion": False,
            "promises": [],
        },
    ]


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P119",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p119-honest-shutter",
        "claim": "mode cannot do 180 degrees at 48 fps",
        "applyMutant": False,
        "selectedLimitId": "mode-48",
        "measuredLimits": [_limit()],
        "guidance": _statements(),
        "sourceClipped": True,
        "sourceOutOfFocus": True,
        "virtualShallowFocusSelected": True,
        "cinematicPresetActive": True,
        "clippingWarningsVisible": True,
        "adviceChangesSettings": False,
        "changesCameraPosition": False,
        "relabelsLighting": False,
    }
    value.update(overrides)
    return value


def _quiet(**overrides):
    """Same measured limit, no clipped-source obligations."""
    value = document(
        evidenceId="p119-quiet",
        claim="grounded-advice",
        guidance=[
            {
                "text": "keep the measured shutter and fps",
                "limitId": "mode-48",
                "recommendsFps": None,
                "recommendsShutter": None,
                "observedMotionPx": 2.0,
                "claimsStableMotion": True,
                "promises": [],
            }
        ],
        sourceClipped=False,
        sourceOutOfFocus=False,
        virtualShallowFocusSelected=False,
        cinematicPresetActive=False,
    )
    value.update(overrides)
    return value


class P119Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P119")
        self.assertEqual(_MODULE.WORKSTREAM, 15)
        self.assertEqual(_MODULE.TITLE, "Add practical cinematographic guidance")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P118",))
        self.assertEqual(
            _MODULE.GOAL,
            "Help the user obtain suitable source footage instead of relying on postprocessing to conceal capture failures.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Provide optional guidance for exposure, focus, source sharpness, clipping, framing, and "
            "virtual-lens compatibility. Separate advice from automatic changes. Do not change physical "
            "camera position or lighting claims through software labels.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A heavily clipped face and a virtual shallow-focus recipe selected for a physically out-of-focus source.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The app explains the source limitations and preserves user control rather than promising restoration.",
        )
        self.assertEqual(_MODULE.MUTANT, "Hide clipping warnings whenever a cinematic preset is active.")
        self.assertEqual(_MODULE.DELIVERABLE, "Capture guidance rules and nonintrusive UI tests")
        self.assertEqual(_MODULE.HONEST_180, "this mode cannot do 180 degrees at this fps")
        self.assertEqual(_MODULE.REFERENCE_SHUTTER_DEGREES, 180.0)
        self.assertEqual(_MODULE.PROMISE_FILM_STOCK, "film-stock fidelity")
        self.assertEqual(_MODULE.PROMISE_ARRI, "ARRI equivalence")
        self.assertEqual(_MODULE.PROMISE_SENSOR_LOG, "sensor-derived Log")

    def test_honest_180_is_recorded_and_exposure_is_measured(self):
        self.assertAlmostEqual(_MODULE.exposure_seconds(172.8, 48.0), 0.01, delta=1e-12)
        self.assertGreater(_MODULE.exposure_seconds(180.0, 48.0), 0.01)
        result = assess(document())
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "P119")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p119-honest-shutter", result["preservedResults"])
        self.assertEqual(result["preservedResults"][2]["fps"], 48.0)
        self.assertEqual(result["preservedResults"][2]["shutter_angle"], 172.8)
        self.assertEqual(result["preservedResults"][2]["max_stable_motion_px"], 6.0)
        self.assertTrue(result["preservedResults"][2]["mode_available"])
        self.assertIn(_MODULE.HONEST_180, result["preservedResults"][3])
        self.assertTrue(any("honest-180:" in item for item in result["reasons"]))
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_fixture_file_matches_the_honest_example(self):
        payload = json.loads(
            (_ROOT / "docs" / "P119_ADD_PRACTICAL_CINEMATOGRAPHIC_GUIDANCE.json").read_text()
        )
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p119-honest-shutter", result["preservedResults"])
        self.assertEqual(result["preservedResults"][2]["shutter_angle"], 172.8)
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P119-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P119")
        self.assertEqual(handoff["nextPhase"], "P120")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertEqual(handoff["caseIds"], list(_MODULE.CASE_IDS))

    def test_ungrounded_guidance_is_rejected_and_evidence_remains(self):
        statement = {
            "text": "raise the shutter to 180 degrees",
            "limitId": None,
            "recommendsFps": None,
            "recommendsShutter": 180.0,
            "observedMotionPx": None,
            "claimsStableMotion": False,
            "promises": [],
        }
        result = assess(_quiet(evidenceId="p119-ungrounded", guidance=[statement]))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.CLAIM_UNGROUNDED, result["rejectedClaims"])
        self.assertIn("p119-ungrounded", result["preservedResults"])
        self.assertIn("raise the shutter to 180 degrees", result["preservedResults"][3])
        self.assertEqual(result["preservedResults"][2]["fps"], 48.0)

    def test_unsupported_shutter_and_fps_are_rejected(self):
        shutter = {
            "text": "set the shutter to 180 degrees",
            "limitId": "mode-48",
            "recommendsFps": None,
            "recommendsShutter": 180.0,
            "observedMotionPx": 1.0,
            "claimsStableMotion": True,
            "promises": [],
        }
        shutter_result = assess(_quiet(guidance=[shutter]))
        self.assertEqual(shutter_result["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_UNSUPPORTED_SHUTTER, shutter_result["rejectedClaims"])
        self.assertEqual(shutter_result["preservedResults"][2]["shutter_angle"], 172.8)
        fps = {
            "text": "switch this mode to 24 fps",
            "limitId": "mode-48",
            "recommendsFps": 24.0,
            "recommendsShutter": None,
            "observedMotionPx": 1.0,
            "claimsStableMotion": True,
            "promises": [],
        }
        fps_result = assess(_quiet(evidenceId="p119-fps", guidance=[fps]))
        self.assertEqual(fps_result["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_UNSUPPORTED_FPS, fps_result["rejectedClaims"])
        self.assertIn("p119-fps", fps_result["preservedResults"])

    def test_forbidden_promises_are_rejected(self):
        for phrase, token in (
            (_MODULE.PROMISE_FILM_STOCK, _MODULE.CLAIM_FILM_STOCK),
            (_MODULE.PROMISE_ARRI, _MODULE.CLAIM_ARRI),
            (_MODULE.PROMISE_SENSOR_LOG, _MODULE.CLAIM_SENSOR_LOG),
        ):
            statement = {
                "text": "keep the measured shutter and fps",
                "limitId": "mode-48",
                "recommendsFps": None,
                "recommendsShutter": None,
                "observedMotionPx": 1.0,
                "claimsStableMotion": True,
                "promises": [phrase],
            }
            result = assess(_quiet(guidance=[statement]))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn(token, result["rejectedClaims"])
            self.assertIn("p119-quiet", result["preservedResults"])

    def test_false_180_claim_and_excess_motion_are_rejected(self):
        limit = _limit()
        limit["shutter_angle"] = 180.0
        false = assess(
            _quiet(
                measuredLimits=[limit],
                guidance=[
                    {
                        "text": _MODULE.HONEST_180,
                        "limitId": "mode-48",
                        "recommendsFps": None,
                        "recommendsShutter": None,
                        "observedMotionPx": 1.0,
                        "claimsStableMotion": True,
                        "promises": [],
                    }
                ],
            )
        )
        self.assertEqual(false["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_FALSE_180, false["rejectedClaims"])
        moving = {
            "text": "this motion is stable",
            "limitId": "mode-48",
            "recommendsFps": None,
            "recommendsShutter": None,
            "observedMotionPx": 9.0,
            "claimsStableMotion": True,
            "promises": [],
        }
        motion = assess(_quiet(evidenceId="p119-motion", guidance=[moving]))
        self.assertEqual(motion["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_MOTION, motion["rejectedClaims"])
        self.assertEqual(motion["preservedResults"][2]["max_stable_motion_px"], 6.0)

    def test_honest_unstable_motion_and_supported_recommendation_are_recorded(self):
        unstable = assess(
            _quiet(
                evidenceId="p119-unstable",
                guidance=[
                    {
                        "text": "observed motion is not stable at this fps",
                        "limitId": "mode-48",
                        "recommendsFps": None,
                        "recommendsShutter": None,
                        "observedMotionPx": 9.0,
                        "claimsStableMotion": False,
                        "promises": [],
                    }
                ],
            )
        )
        self.assertEqual(unstable["decision"], "recorded")
        self.assertEqual(unstable["rejectedClaims"], [])
        supported = assess(
            _quiet(
                evidenceId="p119-supported",
                guidance=[
                    {
                        "text": "use the measured shutter and fps",
                        "limitId": "mode-48",
                        "recommendsFps": 48.0,
                        "recommendsShutter": 172.8,
                        "observedMotionPx": 2.0,
                        "claimsStableMotion": True,
                        "promises": [],
                    }
                ],
            )
        )
        self.assertEqual(supported["decision"], "recorded")
        self.assertEqual(supported["preservedResults"][2]["shutter_angle"], 172.8)

    def test_mutant_hides_clipping_warnings_but_keeps_evidence(self):
        flagged = assess(document(applyMutant=True))
        self.assertEqual(flagged["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, flagged["rejectedClaims"])
        self.assertIn("p119-honest-shutter", flagged["preservedResults"])
        self.assertIn(_MODULE.HONEST_180, flagged["preservedResults"][3])
        hidden = assess(document(evidenceId="p119-hidden", clippingWarningsVisible=False))
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, hidden["rejectedClaims"])
        self.assertIn("p119-hidden", hidden["preservedResults"])

    def test_automatic_changes_camera_and_lighting_labels_are_rejected(self):
        changed = assess(_quiet(adviceChangesSettings=True))
        self.assertEqual(changed["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_SETTINGS, changed["rejectedClaims"])
        camera = assess(_quiet(evidenceId="p119-camera", changesCameraPosition=True))
        self.assertIn(_MODULE.CLAIM_CAMERA, camera["rejectedClaims"])
        lighting = assess(_quiet(evidenceId="p119-light", relabelsLighting=True))
        self.assertEqual(lighting["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_LIGHTING, lighting["rejectedClaims"])
        self.assertIn("p119-light", lighting["preservedResults"])

    def test_source_limits_must_be_explained_without_promising_restoration(self):
        unexplained = assess(
            document(
                guidance=[
                    {
                        "text": _MODULE.HONEST_180,
                        "limitId": "mode-48",
                        "recommendsFps": None,
                        "recommendsShutter": None,
                        "observedMotionPx": 1.0,
                        "claimsStableMotion": True,
                        "promises": [],
                    }
                ]
            )
        )
        self.assertEqual(unexplained["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_CLIP, unexplained["rejectedClaims"])
        self.assertIn(_MODULE.CLAIM_FOCUS, unexplained["rejectedClaims"])
        restoring = assess(
            _quiet(
                evidenceId="p119-restore",
                sourceOutOfFocus=True,
                virtualShallowFocusSelected=True,
                guidance=[
                    {
                        "text": "the out of focus source will restore to a sharp face",
                        "limitId": "mode-48",
                        "recommendsFps": None,
                        "recommendsShutter": None,
                        "observedMotionPx": 1.0,
                        "claimsStableMotion": True,
                        "promises": [],
                    }
                ],
            )
        )
        self.assertEqual(restoring["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_RESTORATION, restoring["rejectedClaims"])
        self.assertNotIn(_MODULE.CLAIM_FOCUS, restoring["rejectedClaims"])

    def test_unavailable_mode_and_wrong_binding_are_rejected(self):
        limit = _limit()
        limit["mode_available"] = False
        unavailable = assess(_quiet(measuredLimits=[limit]))
        self.assertEqual(unavailable["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_MODE_UNAVAILABLE, unavailable["rejectedClaims"])
        other = _limit()
        other["id"] = "mode-24"
        other["fps"] = 24.0
        other["shutter_angle"] = 180.0
        bound = assess(
            _quiet(
                measuredLimits=[_limit(), other],
                guidance=[
                    {
                        "text": "keep the measured shutter and fps",
                        "limitId": "mode-24",
                        "recommendsFps": None,
                        "recommendsShutter": None,
                        "observedMotionPx": 1.0,
                        "claimsStableMotion": True,
                        "promises": [],
                    }
                ],
            )
        )
        self.assertEqual(bound["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_NOT_SELECTED, bound["rejectedClaims"])

    def test_evaluate_uses_the_same_guidance_oracle(self):
        payload = document()
        payload.pop("schemaVersion")
        payload.pop("phase")
        payload.pop("implementationBaseRevision")
        payload["caseId"] = "P119"
        result = evaluate(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "P119")
        self.assertIn("p119-honest-shutter", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            evaluate({})
        bad = document()
        bad["implementationBaseRevision"] = "0" * 40
        with self.assertRaises(ValueError):
            assess(bad)
        with self.assertRaises(ValueError):
            assess(document(sourceClipped=1))
        with self.assertRaises(ValueError):
            assess(
                _quiet(
                    guidance=[
                        {
                            "text": "set the shutter to 400 degrees",
                            "limitId": "mode-48",
                            "recommendsFps": None,
                            "recommendsShutter": 400.0,
                            "observedMotionPx": 1.0,
                            "claimsStableMotion": True,
                            "promises": [],
                        }
                    ]
                )
            )
