"""Host checks for P156. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p156_prepare_a_separate_firmware_risk_gate",
    Path(__file__).resolve().parents[1] / "gates" / "p156_prepare_a_separate_firmware_risk_gate.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P156_PREPARE_A_SEPARATE_FIRMWARE_RISK_GATE.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


class P156Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P156")
        self.assertEqual(_MODULE.WORKSTREAM, 20)
        self.assertEqual(_MODULE.TITLE, "Prepare a separate firmware risk gate")
        self.assertEqual(
            _MODULE.GOAL,
            "Require explicit authorization and a device-specific safety plan before irreversible changes.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Document model variant, bootloader state, verified backups, recovery images, rollback limits, "
            "security consequences, and potential permanent state changes. A general request to build an app "
            "does not authorize flashing. Keep ordinary development operational without firmware changes.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A proposed flash with an unverified image and no confirmed recovery route for the exact device variant.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The gate remains closed and the directive continues with non-destructive app work.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Proceed because another phone with a similar name accepted the image.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Firmware authorization checklist and stop conditions")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P155",))
        self.assertIn("device_serial", _MODULE.AUTHORIZATION_RULE)
        self.assertIn("image_digest", _MODULE.AUTHORIZATION_RULE)
        self.assertIn("user_authorized", _MODULE.AUTHORIZATION_RULE)
        self.assertIn("stop_conditions", _MODULE.AUTHORIZATION_RULE)
        self.assertIn("similar_name_only", _MODULE.AUTHORIZATION_RULE)
        self.assertIn("recorded as blocked", _MODULE.AUTHORIZATION_RULE)
        self.assertIn("does not authorize flashing", _MODULE.AUTHORIZATION_RULE)

    def test_fixture_stays_closed_and_is_recorded_as_blocked(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P156")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.AUTHORIZATION_RULE, " ".join(result["reasons"]))
        self.assertIn("recorded as blocked", " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        self.assertEqual(snapshot["deviceSerial"], _MODULE.DEVICE_SERIAL)
        self.assertEqual(snapshot["imageDigest"], _MODULE.IMAGE_DIGEST)
        self.assertFalse(snapshot["userAuthorized"])
        self.assertTrue(snapshot["blocked"])
        self.assertFalse(snapshot["checklistComplete"])
        self.assertFalse(snapshot["flashAuthorized"])
        self.assertFalse(snapshot["proceed"])
        self.assertTrue(snapshot["gateClosed"])
        self.assertEqual(snapshot["status"], "blocked")
        self.assertEqual(snapshot["missingStopConditions"], [])
        self.assertTrue(snapshot["similarNameExample"]["namesSimilar"])
        self.assertTrue(snapshot["similarNameExample"]["serialsDiffer"])
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_similar_name_only_is_rejected(self):
        result = assess(document(similar_name_only=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.SIMILAR_NAME_ONLY, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertFalse(result["preservedResults"][1]["proceed"])
        self.assertFalse(result["preservedResults"][1]["flashAuthorized"])
        self.assertTrue(result["preservedResults"][1]["gateClosed"])
        self.assertIn("p156-firmware-risk-gate", result["preservedResults"])

    def test_apply_mutant_rejects_the_similar_name_proceed(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SIMILAR_NAME_ONLY, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][1]["similarNameOnly"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])

    def test_user_authorized_false_is_recorded_as_blocked(self):
        result = evaluate(_MODULE.core_payload(user_authorized=False))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][1]["blocked"])
        self.assertEqual(result["preservedResults"][1]["status"], "blocked")
        self.assertFalse(result["preservedResults"][1]["proceed"])
        self.assertIn("recorded as blocked", " ".join(result["reasons"]))

    def test_missing_stop_conditions_are_rejected(self):
        empty = assess(document(stop_conditions=[]))
        self.assertEqual(empty["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_STOP_CONDITIONS, empty["rejectedClaims"])
        self.assertIn("unverified-image", empty["preservedResults"][1]["missingStopConditions"])
        self.assertIn("missing stop conditions", " ".join(empty["reasons"]))
        partial = assess(document(stop_conditions=[_MODULE.STOP_PERMANENT_STATE]))
        self.assertEqual(partial["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_STOP_CONDITIONS, partial["rejectedClaims"])
        self.assertIn(_MODULE.STOP_NO_RECOVERY, partial["preservedResults"][1]["missingStopConditions"])
        self.assertIn("p156-firmware-risk-gate", partial["preservedResults"])

    def test_complete_checklist_is_recorded_and_still_does_not_flash(self):
        result = assess(_MODULE.document_from_core(_MODULE.complete_checklist_payload()))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        snapshot = result["preservedResults"][1]
        self.assertTrue(snapshot["checklistComplete"])
        self.assertFalse(snapshot["blocked"])
        self.assertFalse(snapshot["flashAuthorized"])
        self.assertFalse(snapshot["proceed"])
        self.assertTrue(snapshot["gateClosed"])
        self.assertEqual(snapshot["status"], "checklist-complete")
        self.assertIn("checklist complete; flashing remains unauthorized", result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_claims_proceed_is_refused_even_when_the_checklist_is_complete(self):
        result = assess(_MODULE.document_from_core(_MODULE.complete_checklist_payload(claims_proceed=True)))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PROCEED_REFUSED, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["checklistComplete"])
        self.assertFalse(result["preservedResults"][1]["flashAuthorized"])
        self.assertFalse(result["preservedResults"][1]["proceed"])
        self.assertIn("this gate does not authorize flashing", result["reasons"])

    def test_general_app_request_does_not_authorize_flashing(self):
        result = assess(document(
            user_authorized=True,
            general_app_request=True,
            device_specific_authorization=False,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GENERAL_APP_REQUEST, result["rejectedClaims"])
        self.assertIn("A general request to build an app does not authorize flashing.", result["reasons"])
        self.assertFalse(result["preservedResults"][1]["flashAuthorized"])

    def test_authorization_must_name_the_device(self):
        result = assess(document(
            user_authorized=True,
            general_app_request=False,
            device_specific_authorization=False,
            stop_conditions=[
                _MODULE.STOP_PERMANENT_STATE,
                _MODULE.STOP_UNVERIFIED_IMAGE,
                _MODULE.STOP_NO_RECOVERY,
            ],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOT_DEVICE_SPECIFIC, result["rejectedClaims"])

    def test_similar_names_do_not_match_a_different_family(self):
        self.assertTrue(_MODULE.similar_device_names("Galaxy S23", "Galaxy S23 Ultra"))
        self.assertTrue(_MODULE.similar_device_names("Galaxy-S23", "galaxy s23"))
        self.assertFalse(_MODULE.similar_device_names("Galaxy S23", "Pixel 8"))
        self.assertFalse(_MODULE.similar_device_names("Galaxy S23", _MODULE.DIFFERENT_DEVICE_NAME))
        self.assertTrue(_MODULE.similar_device_names(_MODULE.SIMILAR_ACCEPTED_NAME, _MODULE.SIMILAR_PROPOSED_NAME))

    def test_partial_safety_plan_stays_recorded_and_closed(self):
        result = assess(document(verified_backups=True))
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][1]["checklistComplete"])
        self.assertEqual(result["preservedResults"][1]["status"], "blocked")
        self.assertTrue(result["preservedResults"][1]["gateClosed"])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P157"),
            document(implementationBaseRevision="deadbeef"),
            document(user_authorized="yes"),
            document(similar_name_only=1),
            document(device_serial="Galaxy S23"),
            document(image_digest="not-a-digest"),
            document(stop_conditions="unverified-image"),
            document(stop_conditions=["unverified-image", "unverified-image"]),
            document(extra=True),
            document(device_specific_authorization=True),
            document(recovery_confirmed=True, recovery_image="unconfirmed"),
            document(image_verified="false"),
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    assess(payload)
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(_MODULE.core_payload(image_digest="ABCD"))

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P156-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P156")
        self.assertEqual(handoff["nextPhase"], "P157")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p156*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P156_PREPARE_A_SEPARATE_FIRMWARE_RISK_GATE.md").read_text(encoding="utf-8")
        self.assertIn("Firmware authorization checklist and stop conditions", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("similar name", note)
        self.assertIn("stop conditions", note)
        self.assertIn("user_authorized", note)
        self.assertIn("does not authorize flashing", note)
        self.assertIn("recorded as blocked", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("never `qualified` or `allowed`", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p156_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p156_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P156-0{index}")
            self.assertEqual(module.CASE["phase"], "P156")
            self.assertEqual(module.CASE["workstream"], 20)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
