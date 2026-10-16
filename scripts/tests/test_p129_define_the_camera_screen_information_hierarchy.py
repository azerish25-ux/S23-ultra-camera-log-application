"""Host checks for P129. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p129_define_the_camera_screen_information_hierarchy",
    Path(__file__).resolve().parents[1]
    / "gates"
    / "p129_define_the_camera_screen_information_hierarchy.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _control(ident, label):
    return {"id": ident, "label": label}


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P129",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p129-landscape-hierarchy",
        "claim": "camera-screen-hierarchy-host-fixture",
        "applyMutant": False,
        "record_in_scroll_only": False,
        "warnings_visible": True,
        "viewfinder_replaced": False,
        "usability_study_pass": False,
        "slots": {
            "capture": [
                _control("record", "Record"),
                _control("stop", "Stop"),
                _control("source-mode", "Source mode"),
                _control("exposure", "Exposure"),
                _control("audio", "Audio"),
            ],
            "monitoring": [_control("microphone-meters", "Microphone meters")],
            "processing": [_control("manual-controls", "Manual controls")],
        },
        "warnings": [{"kind": "storage", "text": "Storage warning"}],
    }
    value.update(overrides)
    return value


def flat_payload(**overrides):
    value = {
        "caseId": "P129",
        "evidenceId": "p129-flat",
        "claim": "flat-screen",
        "capture": ["record", "stop"],
        "monitoring": [],
        "processing": [],
        "warnings": [],
        "record_in_scroll_only": False,
        "warnings_visible": True,
        "viewfinder_replaced": False,
        "usability_study_pass": False,
        "applyMutant": False,
    }
    value.update(overrides)
    return value


class P129Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p129-landscape-hierarchy"):
        self.assertEqual(tuple(result), KEYS)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn(_MODULE.SLOT_RULES, " ".join(result["reasons"]))
        self.assertTrue(result["reasons"])

    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P129")
        self.assertEqual(_MODULE.WORKSTREAM, 17)
        self.assertEqual(_MODULE.DEPENDENCIES, ("P017", "P024", "P121"))
        self.assertEqual(_MODULE.TITLE, "Define the camera screen information hierarchy")
        self.assertEqual(
            _MODULE.GOAL,
            "Keep recording, source mode, exposure, audio, and warnings visible without overcrowding the viewfinder.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Place Stop inside a scrollable control list that moves during recording.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "Record and Stop remain reachable, warnings remain readable, and the viewfinder is not accidentally replaced by settings.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Camera screen specification and layout interaction tests")
        self.assertEqual(
            _MODULE.FIXTURE,
            "Landscape mode with large text, a storage warning, microphone meters, and the manual controls panel open.",
        )

    def test_clean_hierarchy_is_recorded_not_qualified(self):
        result = assess(document())
        self.assert_contract(result)
        self.assertEqual(result["caseId"], "P129")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("capture=record,stop,source-mode,exposure,audio", result["preservedResults"])
        self.assertIn("monitoring=microphone-meters", result["preservedResults"])
        self.assertIn("processing=manual-controls", result["preservedResults"])
        self.assertIn("warnings=storage", result["preservedResults"])
        self.assertIn("record_in_scroll_only=false", result["preservedResults"])
        self.assertIn("warnings_visible=true", result["preservedResults"])
        self.assertIn("severe warnings visible: storage", result["reasons"])
        self.assertIn("camera-screen-hierarchy-host-fixture", result["preservedResults"])

    def test_published_fixture_is_recorded(self):
        payload = json.loads(
            (ROOT / "docs" / "P129_DEFINE_THE_CAMERA_SCREEN_INFORMATION_HIERARCHY.json").read_text()
        )
        result = assess(payload)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(evaluate(payload), result)

    def test_optional_slots_may_be_empty(self):
        result = evaluate(flat_payload())
        self.assert_contract(result, "p129-flat")
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("monitoring=none", result["preservedResults"])
        self.assertIn("processing=none", result["preservedResults"])
        self.assertIn("warnings=none", result["preservedResults"])

    def test_record_in_scroll_only_is_rejected_and_evidence_remains(self):
        result = assess(document(record_in_scroll_only=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RECORD_IN_SCROLL_ONLY, result["rejectedClaims"])
        self.assertIn("p129-landscape-hierarchy", result["preservedResults"])

    def test_stop_missing_from_capture_is_rejected(self):
        payload = document()
        payload["slots"]["capture"] = [
            item for item in payload["slots"]["capture"] if item["id"] != "stop"
        ]
        payload["slots"]["processing"] = [
            _control("stop", "Stop"),
            _control("manual-controls", "Manual controls"),
        ]
        result = assess(payload)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RECORD_OR_STOP_NOT_IN_CAPTURE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.SHARED_CONTROL_IDENTITY, result["rejectedClaims"])

    def test_shared_control_identity_is_rejected(self):
        payload = document()
        payload["slots"]["processing"] = [
            _control("manual-controls", "Manual controls"),
            _control("exposure", "Exposure"),
        ]
        result = assess(payload)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SHARED_CONTROL_IDENTITY, result["rejectedClaims"])
        self.assertIn("exposure", " ".join(result["reasons"]))
        self.assertIn("p129-landscape-hierarchy", result["preservedResults"])

    def test_hidden_severe_warnings_are_rejected(self):
        for kind in ("storage", "thermal", "permission"):
            result = assess(document(
                warnings=[{"kind": kind, "text": kind}],
                warnings_visible=False,
            ))
            self.assertEqual(result["decision"], "rejected", kind)
            self.assertIn(_MODULE.SEVERE_WARNING_HIDDEN, result["rejectedClaims"])
            self.assertIn("p129-landscape-hierarchy", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_hidden_nonsevere_warning_can_be_recorded(self):
        result = assess(document(
            warnings=[{"kind": "audio", "text": "Audio meter"}],
            warnings_visible=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn("p129-landscape-hierarchy", result["preservedResults"])

    def test_usability_study_pass_is_rejected_not_qualified(self):
        result = assess(document(usability_study_pass=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.USABILITY_STUDY_CLAIMED, result["rejectedClaims"])
        self.assertNotEqual(result["decision"], "qualified")

    def test_viewfinder_replaced_by_settings_is_rejected(self):
        result = assess(document(viewfinder_replaced=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.VIEWFINDER_REPLACED, result["rejectedClaims"])

    def test_missing_permission_alias_is_severe(self):
        result = evaluate(flat_payload(
            warnings=["missing-permission"],
            warnings_visible=False,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SEVERE_WARNING_HIDDEN, result["rejectedClaims"])
        self.assertIn("warnings=permission", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(warnings_visible="yes"))
        with self.assertRaises(ValueError):
            evaluate(flat_payload(decision="qualified"))
        with self.assertRaises(ValueError):
            _MODULE.seal_result(
                "P129",
                "qualified",
                ["x"],
                ["x"],
                ["p129-landscape-hierarchy"],
                ["physical S23 measurement was not run"],
                "p129-landscape-hierarchy",
            )

    def test_duplicate_control_id_raises(self):
        payload = document()
        payload["slots"]["capture"].append(_control("record", "Record again"))
        with self.assertRaises(ValueError):
            assess(payload)

    def test_handoff_points_at_p130(self):
        handoff = json.loads((ROOT / "docs" / "evidence" / "P129-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P129")
        self.assertEqual(handoff["commit"], None)
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(handoff["nextPhase"], "P130")
        self.assertEqual(handoff["caseIds"], [f"TC-P129-0{index}" for index in range(1, 9)])
