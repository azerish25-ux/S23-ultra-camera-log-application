"""Host checks for P154. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p154_survey_public_firmware_and_hal_information",
    Path(__file__).resolve().parents[1] / "gates" / "p154_survey_public_firmware_and_hal_information.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
CASE_NAMES = {
    1: "Wrong bottleneck attribution",
    2: "Incomplete public source",
    3: "Unexplored reversible alternative",
    4: "Missing explicit modification authorization",
    5: "Advertised unlock without delivery",
    6: "Computational capture overclaim",
    7: "Advanced model cost regression",
    8: "Unreproducible research closure",
}


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P154_SURVEY_PUBLIC_FIRMWARE_AND_HAL_INFORMATION.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


class P154Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P154")
        self.assertEqual(_MODULE.WORKSTREAM, 20)
        self.assertEqual(_MODULE.TITLE, "Survey public firmware and HAL information")
        self.assertEqual(_MODULE.GOAL, "Research the device architecture without modifying the user’s phone.")
        self.assertEqual(
            _MODULE.METHOD,
            "Inspect official architecture documentation, available source releases, public logs, "
            "and lawful device diagnostics. Record exact model and firmware applicability. Separate "
            "kernel source availability from access to proprietary camera processing components.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A public source package that lacks the proprietary imaging component needed for the proposed change.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The report records the missing component rather than claiming the source package is a "
            "complete camera firmware implementation.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Assume publishing a kernel source tree exposes every camera algorithm and sensor mode.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Non-destructive architecture research report")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P153",))
        self.assertIn("phone_modified", _MODULE.SURVEY_RULE)
        self.assertIn("claims_all_modes", _MODULE.SURVEY_RULE)
        self.assertIn("not public", _MODULE.SURVEY_RULE)
        self.assertIn("unverified", _MODULE.SURVEY_RULE)
        self.assertEqual(
            _MODULE.kernel_tree_does_not_prove(),
            (
                "every camera algorithm",
                "every sensor mode",
                "proprietary camera processing components",
                "behavior on the user's phone",
            ),
        )

    def test_fixture_records_public_sources_and_the_missing_component(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        self.assertFalse(source["phone_modified"])
        self.assertFalse(source["claims_all_modes"])
        self.assertFalse(source["claimsCompleteFirmware"])
        self.assertEqual(source["notesStatus"], _MODULE.UNVERIFIED_NOTES)
        self.assertIn(_MODULE.PROPRIETARY_COMPONENT, source["missingComponents"])
        for item in source["sources"]:
            self.assertEqual(set(item), {"url", "public", "documents"})
            self.assertTrue(item["public"])
            self.assertTrue(item["url"].startswith("https://"))
            self.assertTrue(item["documents"])
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P154")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.SURVEY_RULE, " ".join(result["reasons"]))
        self.assertIn("every camera algorithm", " ".join(result["reasons"]))
        self.assertIn("every sensor mode", " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        self.assertEqual(snapshot["kernelTreeDoesNotProve"], list(_MODULE.KERNEL_TREE_DOES_NOT_PROVE))
        self.assertFalse(snapshot["phone_modified"])
        self.assertFalse(snapshot["claims_all_modes"])
        self.assertFalse(snapshot["assumesEveryCameraMode"])
        self.assertTrue(snapshot["proprietaryImagingRecordedMissing"])
        self.assertTrue(snapshot["architectureNotesUnverified"])
        self.assertEqual(snapshot["nonPublicEvidence"], [])
        self.assertEqual(snapshot["sources"][0]["url"], "https://opensource.samsung.com/")
        self.assertIn("kernel", snapshot["sources"][0]["documents"])
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_phone_modified_is_rejected(self):
        result = assess(document(phone_modified=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.PHONE_MODIFIED, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][1]["phone_modified"])
        self.assertIn("p154-firmware-hal-survey", result["preservedResults"])
        self.assertIn("phone_modified must be false", " ".join(result["reasons"]))

    def test_claims_all_modes_is_rejected(self):
        result = assess(document(claims_all_modes=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CLAIMS_ALL_MODES, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][1]["claims_all_modes"])
        self.assertTrue(result["preservedResults"][1]["assumesEveryCameraMode"])
        self.assertIn("claims_all_modes true", " ".join(result["reasons"]))
        self.assertIn("every camera mode", " ".join(result["reasons"]))
        self.assertNotIn(_MODULE.PHONE_MODIFIED, result["rejectedClaims"])
        self.assertIn("p154-firmware-hal-survey", result["preservedResults"])

    def test_apply_mutant_rejects_the_kernel_tree_assumption(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CLAIMS_ALL_MODES, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertFalse(result["preservedResults"][1]["claims_all_modes"])
        self.assertTrue(result["preservedResults"][1]["assumesEveryCameraMode"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_non_public_source_cannot_be_evidence(self):
        private = _MODULE.private_source()
        sources = _MODULE.fixture_sources() + [private]
        cited = document(sources=sources, usedAsEvidence=[private["url"]])
        result = assess(cited)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], [_MODULE.NON_PUBLIC_EVIDENCE])
        self.assertEqual(result["preservedResults"][1]["nonPublicEvidence"], [private["url"]])
        self.assertFalse(result["preservedResults"][1]["sources"][-1]["public"])
        self.assertIn("cannot be used as evidence", " ".join(result["reasons"]))
        self.assertIn(private["url"], result["preservedResults"][1]["sources"][-1]["url"])
        held = assess(document(sources=sources))
        self.assertEqual(held["decision"], "recorded")
        self.assertEqual(held["rejectedClaims"], [])
        self.assertIn(private["url"], held["preservedResults"][1]["privateSources"])
        self.assertEqual(held["preservedResults"][1]["nonPublicEvidence"], [])

    def test_notes_must_stay_unverified_against_the_phone(self):
        result = assess(document(notesStatus="verified-on-user-phone"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOTES_NOT_UNVERIFIED, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["architectureNotesUnverified"])
        self.assertEqual(result["preservedResults"][1]["notesStatus"], "verified-on-user-phone")
        self.assertIn("unverified against the user's phone", " ".join(result["reasons"]))
        self.assertIn("p154-firmware-hal-survey", result["preservedResults"])

    def test_missing_component_must_be_recorded_instead_of_a_complete_claim(self):
        missing = assess(document(missingComponents=["public-hal-headers"]))
        self.assertEqual(missing["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_COMPONENT_UNRECORDED, missing["rejectedClaims"])
        self.assertFalse(missing["preservedResults"][1]["proprietaryImagingRecordedMissing"])
        self.assertIn(_MODULE.ORACLE, missing["reasons"])
        complete = assess(document(claimsCompleteFirmware=True))
        self.assertEqual(complete["decision"], "rejected")
        self.assertIn(_MODULE.COMPLETE_FIRMWARE_CLAIM, complete["rejectedClaims"])
        self.assertTrue(complete["preservedResults"][1]["proprietaryImagingRecordedMissing"])
        self.assertTrue(complete["preservedResults"][1]["claimsCompleteFirmware"])
        self.assertIn("not a complete", " ".join(complete["reasons"]))

    def test_unknown_evidence_url_raises(self):
        with self.assertRaises(ValueError):
            assess(document(usedAsEvidence=["https://example.invalid/not-in-the-survey"]))

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P155"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            document(sources=[]),
            document(phone_modified="false"),
            document(claims_all_modes=1),
            document(notesStatus=""),
            document(architectureNotes=""),
            document(missingComponents="proprietary-imaging-component"),
            document(sources=[{
                "url": "not-a-url",
                "public": True,
                "documents": "kernel interfaces",
            }]),
            document(sources=[{
                "url": "https://example.invalid/kernel",
                "public": "yes",
                "documents": "kernel interfaces",
            }]),
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
            evaluate(_MODULE.core_payload(decision="qualified"))

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P154-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P154")
        self.assertEqual(handoff["title"], "Survey public firmware and HAL information")
        self.assertEqual(handoff["deliverable"], "Non-destructive architecture research report")
        self.assertEqual(handoff["nextPhase"], "P155")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p154*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertEqual(
            handoff["caseIds"],
            [f"TC-P154-0{index}" for index in range(1, 9)],
        )
        for relative in handoff["changedFiles"]:
            self.assertTrue((_ROOT / relative).is_file(), relative)
        note = (_ROOT / "docs" / "P154_SURVEY_PUBLIC_FIRMWARE_AND_HAL_INFORMATION.md").read_text(encoding="utf-8")
        self.assertIn("Non-destructive architecture research report", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("phone_modified", note)
        self.assertIn("claims_all_modes", note)
        self.assertIn("cannot be used as evidence", note)
        self.assertIn("unverified", note)
        self.assertIn("every camera algorithm", note)
        self.assertIn("every sensor mode", note)
        self.assertIn("proprietary", note)
        self.assertIn("never `qualified` or `allowed`", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p154_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p154_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P154-0{index}")
            self.assertEqual(module.CASE["phase"], "P154")
            self.assertEqual(module.CASE["workstream"], 20)
            self.assertEqual(module.CASE["name"], CASE_NAMES[index])
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
