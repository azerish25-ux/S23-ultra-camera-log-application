"""Host checks for P148. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p148_verify_offline_privacy_and_permissions",
    Path(__file__).resolve().parents[1] / "gates" / "p148_verify_offline_privacy_and_permissions.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P148_VERIFY_OFFLINE_PRIVACY_AND_PERMISSIONS.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


class P148Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P148")
        self.assertEqual(_MODULE.WORKSTREAM, 19)
        self.assertEqual(_MODULE.TITLE, "Verify offline privacy and permissions")
        self.assertEqual(
            _MODULE.GOAL,
            "Make local processing and minimum permission use observable properties.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Audit network traffic, permission prompts, logging, crash reports, and exported "
            "metadata. The default render path must not upload frames, depth maps, faces, or "
            "audio. Optional content downloads are explicit and separable from operation after "
            "installation.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "Airplane-mode capture and development with all model assets installed, plus a "
            "diagnostic export.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The workflow succeeds locally and the report omits personal paths and unnecessary "
            "identifiers.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Send image thumbnails to analytics while describing the app as entirely offline.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Privacy test report and permission inventory")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P147",))
        self.assertIn("used but not required", _MODULE.PRIVACY_RULE)
        self.assertIn("Network endpoints must be empty", _MODULE.PRIVACY_RULE)
        self.assertIn("analytics_payload nonempty", _MODULE.PRIVACY_RULE)
        self.assertIn("offline_claim is true", _MODULE.PRIVACY_RULE)
        self.assertIn("Camera and microphone may be required only when capture needs them", _MODULE.PRIVACY_RULE)
        self.assertIn("recorded as a warning, not hidden", _MODULE.PRIVACY_RULE)
        self.assertIn("never qualified", _MODULE.PRIVACY_RULE)

    def test_fixture_records_an_offline_minimum_permission_inventory(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P148")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn(_MODULE.PRIVACY_RULE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        self.assertEqual(snapshot["offline_claim"], True)
        self.assertEqual(snapshot["network_endpoints"], [])
        self.assertFalse(snapshot["analyticsNonempty"])
        self.assertEqual(snapshot["warnings"], [])
        self.assertFalse(snapshot["warningsHidden"])
        self.assertEqual(snapshot["usedNotRequired"], [])
        self.assertEqual(snapshot["requiredWithoutCaptureNeed"], [])
        self.assertEqual(snapshot["personalMarkers"], [])
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_permission_used_but_not_required_is_rejected(self):
        result = assess(document(permissions=[
            {"name": "camera", "required": True, "used": True},
            {"name": "microphone", "required": True, "used": True},
            {"name": "location", "required": False, "used": True},
        ]))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.USED_NOT_REQUIRED, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["usedNotRequired"], ["location"])
        self.assertIn("p148-offline-privacy", result["preservedResults"])
        self.assertIn("used but not required: location", " ".join(result["reasons"]))

    def test_offline_claim_rejects_network_endpoints(self):
        result = assess(document(network_endpoints=["https://cdn.example/models"]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OFFLINE_ENDPOINTS, result["rejectedClaims"])
        self.assertEqual(
            result["preservedResults"][1]["network_endpoints"],
            ["https://cdn.example/models"],
        )
        self.assertIn("network endpoints must be empty", " ".join(result["reasons"]))

    def test_analytics_payload_while_offline_is_rejected(self):
        result = assess(document(analytics_payload=["thumb-001"]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.THUMBNAIL_OFFLINE, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][1]["analyticsNonempty"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertIn("p148-offline-privacy", result["preservedResults"])

    def test_apply_mutant_sends_thumbnails_while_claiming_offline(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.THUMBNAIL_OFFLINE, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertTrue(result["preservedResults"][1]["analyticsNonempty"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_camera_and_microphone_required_only_when_capture_needs_them(self):
        camera = assess(document(
            permissions=[{"name": "camera", "required": True, "used": True}],
            capture_needs_camera=False,
            capture_needs_microphone=False,
        ))
        self.assertEqual(camera["decision"], "rejected")
        self.assertIn(_MODULE.CAPTURE_PERMISSION, camera["rejectedClaims"])
        self.assertEqual(camera["preservedResults"][1]["requiredWithoutCaptureNeed"], ["camera"])
        microphone = assess(document(
            permissions=[
                {"name": "camera", "required": True, "used": True},
                {"name": "android.permission.RECORD_AUDIO", "required": True, "used": True},
            ],
            capture_needs_microphone=False,
        ))
        self.assertEqual(microphone["decision"], "rejected")
        self.assertIn(_MODULE.CAPTURE_PERMISSION, microphone["rejectedClaims"])
        self.assertEqual(
            microphone["preservedResults"][1]["requiredWithoutCaptureNeed"],
            ["android.permission.RECORD_AUDIO"],
        )
        allowed = assess(document(
            permissions=[
                {"name": "android.permission.CAMERA", "required": True, "used": True},
                {"name": "microphone", "required": True, "used": True},
            ],
        ))
        self.assertEqual(allowed["decision"], "recorded")

    def test_unused_required_permission_is_a_visible_warning_not_a_rejection(self):
        permissions = [
            {"name": "camera", "required": True, "used": False},
            {"name": "microphone", "required": True, "used": True},
        ]
        result = assess(document(
            permissions=permissions,
            visible_warnings=["unused-required:camera"],
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"][1]["warnings"], ["unused-required:camera"])
        self.assertFalse(result["preservedResults"][1]["warningsHidden"])
        self.assertIn("warning: unused-required:camera", result["reasons"])
        self.assertIn("p148-offline-privacy", result["preservedResults"])

    def test_hiding_an_unused_required_warning_is_rejected_but_the_warning_remains(self):
        permissions = [
            {"name": "camera", "required": True, "used": False},
            {"name": "microphone", "required": True, "used": True},
        ]
        omitted = assess(document(permissions=permissions, visible_warnings=[]))
        self.assertEqual(omitted["decision"], "rejected")
        self.assertIn(_MODULE.WARNINGS_HIDDEN, omitted["rejectedClaims"])
        self.assertEqual(omitted["preservedResults"][1]["warnings"], ["unused-required:camera"])
        self.assertTrue(omitted["preservedResults"][1]["warningsHidden"])
        self.assertIn("warning: unused-required:camera", omitted["reasons"])
        suppressed = assess(document(
            permissions=permissions,
            visible_warnings=["unused-required:camera"],
            hide_warnings=True,
        ))
        self.assertEqual(suppressed["decision"], "rejected")
        self.assertIn(_MODULE.WARNINGS_HIDDEN, suppressed["rejectedClaims"])
        self.assertEqual(suppressed["preservedResults"][1]["warnings"], ["unused-required:camera"])

    def test_private_uploads_personal_paths_and_network_operation_are_rejected(self):
        uploaded = assess(document(uploads=["frames", "depth maps"]))
        self.assertEqual(uploaded["decision"], "rejected")
        self.assertIn(_MODULE.PRIVATE_UPLOAD, uploaded["rejectedClaims"])
        self.assertEqual(uploaded["preservedResults"][1]["forbiddenUploads"], ["frames", "depth maps"])
        personal = assess(document(
            diagnostic_export="export path /home/alice serial=ABC android_id=99",
        ))
        self.assertEqual(personal["decision"], "rejected")
        self.assertIn(_MODULE.PERSONAL_MARKER, personal["rejectedClaims"])
        self.assertIn("/home/", personal["preservedResults"][1]["personalMarkers"])
        self.assertIn("serial=", personal["preservedResults"][1]["personalMarkers"])
        dependent = assess(document(operation_requires_network=True))
        self.assertEqual(dependent["decision"], "rejected")
        self.assertIn(_MODULE.OPERATION_NETWORK, dependent["rejectedClaims"])

    def test_optional_downloads_are_explicit_and_separable_from_an_offline_claim(self):
        separable = assess(document(
            offline_claim=False,
            network_endpoints=["https://cdn.example/optional-model"],
            optional_downloads_explicit=True,
        ))
        self.assertEqual(separable["decision"], "recorded")
        self.assertEqual(separable["rejectedClaims"], [])
        self.assertNotIn(_MODULE.OFFLINE_ENDPOINTS, separable["rejectedClaims"])
        implicit = assess(document(
            offline_claim=False,
            network_endpoints=["https://cdn.example/optional-model"],
            optional_downloads_explicit=False,
        ))
        self.assertEqual(implicit["decision"], "rejected")
        self.assertIn(_MODULE.IMPLICIT_DOWNLOAD, implicit["rejectedClaims"])
        mixed = assess(document(
            offline_claim=True,
            network_endpoints=["https://cdn.example/optional-model"],
            optional_downloads_explicit=True,
        ))
        self.assertEqual(mixed["decision"], "rejected")
        self.assertIn(_MODULE.OFFLINE_ENDPOINTS, mixed["rejectedClaims"])

    def test_thumbnail_upload_label_while_offline_is_rejected(self):
        result = assess(document(uploads=["thumbnails"]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.THUMBNAIL_OFFLINE, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][1]["analyticsNonempty"])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P149"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            document(offline_claim="yes"),
            document(permissions=[{"name": "camera", "required": True}]),
            document(permissions=[{"name": "camera", "required": 1, "used": True}]),
            document(permissions=[
                {"name": "camera", "required": True, "used": True},
                {"name": "camera", "required": True, "used": False},
            ]),
            document(network_endpoints=[""]),
            document(analytics_payload="thumb"),
            document(diagnostic_export=""),
            document(visible_warnings=[""]),
            document(hide_warnings=0),
            document(uploads=[" frames"]),
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
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P148-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P148")
        self.assertEqual(handoff["nextPhase"], "P149")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p148*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P148_VERIFY_OFFLINE_PRIVACY_AND_PERMISSIONS.md").read_text(encoding="utf-8")
        self.assertIn("Privacy test report and permission inventory", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("analytics_payload", note)
        self.assertIn("offline_claim", note)
        self.assertIn("used but not required", note)
        self.assertIn("network endpoints", note)
        self.assertIn("warning", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("never `qualified` or `allowed`", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p148_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p148_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P148-0{index}")
            self.assertEqual(module.CASE["phase"], "P148")
            self.assertEqual(module.CASE["workstream"], 19)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
