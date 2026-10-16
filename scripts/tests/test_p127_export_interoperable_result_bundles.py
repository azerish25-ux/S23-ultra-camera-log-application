"""Host checks for P127. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p127_export_interoperable_result_bundles",
    Path(__file__).resolve().parents[1] / "gates" / "p127_export_interoperable_result_bundles.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SRC = "a" * 64
RECIPE = "b" * 64
RESULT = "c" * 64
PRIVATE = "/home/ada/Movies/private_take.mov"
EMAIL = "ada@example.com"


def manifest(**overrides):
    value = {
        "source_sha256": SRC,
        "recipe_version_sha256": RECIPE,
        "result_sha256": RESULT,
        "color_transfer": "logc3",
        "container": "mov",
        "non_claims": ["not a physical S23 qualification"],
    }
    value.update(overrides)
    return value


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P127",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p127-share-bundle",
        "claim": "sanitized-interoperable-export",
        "applyMutant": False,
        "export_allowed": True,
        "grade_applied": True,
        "labels": ["LogC3"],
        "filename": "share_LogC3.mov",
        "manifest": manifest(),
        "metadataTexts": [f"owner={EMAIL} source={PRIVATE} color_transfer=logc3"],
        "interpretation": {"transfer": "logc3", "note": "scene-referred LogC3 EI800 sidecar"},
        "selfDescribing": False,
        "publishPrivatePaths": False,
        "personalIdentifiers": [EMAIL],
    }
    value.update(overrides)
    return value


def payload(**overrides):
    value = document()
    value.pop("schemaVersion")
    value.pop("phase")
    value.pop("implementationBaseRevision")
    value["caseId"] = "P127"
    value.update(overrides)
    return value


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"] + result["openQuestions"])


class P127Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P127")
        self.assertEqual(_MODULE.WORKSTREAM, 16)
        self.assertEqual(_MODULE.TITLE, "Export interoperable result bundles")
        self.assertEqual(_MODULE.GOAL, "Deliver video with the metadata needed to understand and reproduce it.")
        self.assertEqual(
            _MODULE.MUTANT,
            "Publish private absolute paths or omit essential Log interpretation metadata.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Export bundle schema and privacy-preserving share tests")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P126",))
        self.assertEqual(_MODULE.REQUIRED_NON_CLAIM, "not a physical S23 qualification")
        self.assertEqual(
            _MODULE.MANIFEST_FIELDS,
            (
                "source_sha256",
                "recipe_version_sha256",
                "result_sha256",
                "color_transfer",
                "container",
                "non_claims",
            ),
        )

    def test_graded_bundle_is_recorded_and_sanitized(self):
        result = assess(document())
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P127")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p127-share-bundle", result["preservedResults"])
        self.assertIn("sanitized-interoperable-export", result["preservedResults"])
        self.assertIn("source_sha256=" + SRC, result["preservedResults"])
        self.assertIn("recipe_version_sha256=" + RECIPE, result["preservedResults"])
        self.assertIn("result_sha256=" + RESULT, result["preservedResults"])
        self.assertIn("color_transfer=logc3", result["preservedResults"])
        self.assertIn("container=mov", result["preservedResults"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        text = blob(result)
        self.assertIn("[redacted-path]", text)
        self.assertIn("[redacted-identifier]", text)
        self.assertIn("color_transfer=logc3", text)
        self.assertNotIn(PRIVATE, text)
        self.assertNotIn(EMAIL, text)
        self.assertIn("public report sanitized without dropping technical provenance", result["reasons"])

    def test_evaluate_matches_assess_on_decision(self):
        assessed = assess(document())
        evaluated = evaluate(payload())
        self.assertEqual(evaluated["decision"], assessed["decision"])
        self.assertEqual(evaluated["rejectedClaims"], assessed["rejectedClaims"])
        self.assertEqual(evaluated["caseId"], "P127")
        self.assertIn("p127-share-bundle", evaluated["preservedResults"])

    def test_pass_through_copy_is_recorded_when_ungraded_hashes_match(self):
        result = assess(document(
            grade_applied=False,
            manifest=manifest(result_sha256=SRC, color_transfer="bt709"),
            labels=["Rec.709"],
            filename="preview.mov",
            interpretation=None,
            metadataTexts=["color_transfer=bt709"],
            personalIdentifiers=[],
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("pass-through copy", result["reasons"])
        self.assertIn("pass-through copy", result["preservedResults"])

    def test_identical_hashes_with_grade_are_rejected(self):
        result = assess(document(
            manifest=manifest(result_sha256=SRC, color_transfer="bt709"),
            labels=["Rec.709"],
            filename="graded.mov",
            interpretation=None,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GRADED_SAME_HASH, result["rejectedClaims"])
        self.assertIn("identical hashes", " ".join(result["reasons"]))
        self.assertIn("p127-share-bundle", result["preservedResults"])

    def test_ungraded_hash_change_is_rejected(self):
        result = assess(document(
            grade_applied=False,
            manifest=manifest(color_transfer="bt709"),
            labels=["Rec.709"],
            filename="copy.mov",
            interpretation=None,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNGRADED_CHANGED, result["rejectedClaims"])

    def test_missing_source_blocks_an_allowed_export(self):
        for source in (None, ""):
            result = assess(document(
                manifest=manifest(source_sha256=source, color_transfer="bt709"),
                labels=["Rec.709"],
                filename="blocked.mov",
                interpretation=None,
                metadataTexts=[],
                personalIdentifiers=[],
            ))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn(_MODULE.MISSING_SOURCE, result["rejectedClaims"])
            self.assertIn("missing source_sha256 blocks export", result["reasons"])
        omitted = manifest(color_transfer="bt709")
        del omitted["source_sha256"]
        result = assess(document(
            manifest=omitted,
            labels=["Rec.709"],
            filename="blocked.mov",
            interpretation=None,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_SOURCE, result["rejectedClaims"])

    def test_missing_source_is_withheld_when_export_is_not_allowed(self):
        result = assess(document(
            export_allowed=False,
            manifest=manifest(source_sha256=None, color_transfer="bt709"),
            labels=["Rec.709"],
            filename="held.mov",
            interpretation=None,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("missing source_sha256 blocks export", result["reasons"])
        self.assertIn("export withheld", result["reasons"])

    def test_display_transfer_relabelled_as_log_is_rejected(self):
        cases = [
            ("bt709", ["LogC3"], "delivery.mov"),
            ("hlg", ["HLG"], "shot_Log.mov"),
            ("bt709", ["Rec.709"], "master_logc3.mov"),
            ("hlg", ["look LOGC3"], "out.mov"),
        ]
        for color, labels, filename in cases:
            result = assess(document(
                manifest=manifest(color_transfer=color),
                labels=labels,
                filename=filename,
                interpretation=None,
                metadataTexts=[],
                personalIdentifiers=[],
            ))
            self.assertEqual(result["decision"], "rejected", filename)
            self.assertIn(_MODULE.RELABEL, result["rejectedClaims"])
            self.assertIn("relabel rejected", " ".join(result["reasons"]))

    def test_logical_filename_is_not_a_log_relabel(self):
        result = assess(document(
            manifest=manifest(color_transfer="bt709"),
            labels=["logical-look"],
            filename="catalog.mov",
            interpretation=None,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(_MODULE.mentions_log("logical-look"))
        self.assertFalse(_MODULE.mentions_log("catalog.mov"))
        self.assertTrue(_MODULE.mentions_log("Log"))
        self.assertTrue(_MODULE.mentions_log("logc3"))

    def test_missing_required_non_claim_is_rejected(self):
        result = assess(document(
            manifest=manifest(non_claims=["host fixture only"]),
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_NON_CLAIM, result["rejectedClaims"])
        self.assertIn("not a physical S23 qualification", " ".join(result["reasons"]))

    def test_non_claim_literal_inside_a_longer_string_is_accepted(self):
        result = assess(document(
            manifest=manifest(non_claims=["record is not a physical S23 qualification and not cinema equivalence"]),
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_hashes_and_shapes_raise(self):
        with self.assertRaises(ValueError):
            assess(document(manifest=manifest(source_sha256="A" * 64)))
        with self.assertRaises(ValueError):
            assess(document(manifest=manifest(result_sha256="ab" * 31)))
        with self.assertRaises(ValueError):
            assess(document(manifest=manifest(non_claims="not a physical S23 qualification")))
        with self.assertRaises(ValueError):
            assess(document(export_allowed=1))
        with self.assertRaises(ValueError):
            assess(document(grade_applied="true"))
        with self.assertRaises(ValueError):
            assess(document(manifest=manifest(color_transfer="rec709")))
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            evaluate({})

    def test_mutant_is_rejected_and_paths_stay_redacted(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn("p127-share-bundle", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        text = blob(result)
        self.assertNotIn(PRIVATE, text)
        self.assertNotIn(EMAIL, text)
        self.assertIn("source_sha256=" + SRC, result["preservedResults"])

    def test_publishing_private_paths_is_rejected_without_echoing_them(self):
        result = assess(document(publishPrivatePaths=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PRIVATE_PATH, result["rejectedClaims"])
        text = blob(result)
        self.assertNotIn(PRIVATE, text)
        self.assertNotIn(EMAIL, text)
        self.assertIn("[redacted-path]", text)
        self.assertIn("interpretation=scene-referred LogC3 EI800 sidecar", result["preservedResults"])

    def test_log_master_without_interpretation_is_not_self_describing(self):
        silent = assess(document(
            interpretation=None,
            selfDescribing=True,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(silent["decision"], "rejected")
        self.assertIn(_MODULE.LOG_SELF_DESCRIBING, silent["rejectedClaims"])
        blocked = assess(document(
            interpretation=None,
            selfDescribing=False,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(blocked["decision"], "rejected")
        self.assertIn(_MODULE.LOG_EXPORT_BLOCKED, blocked["rejectedClaims"])
        warned = assess(document(
            export_allowed=False,
            interpretation=None,
            selfDescribing=False,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(warned["decision"], "recorded")
        self.assertIn("warning: LogC3 is not universally self-describing", warned["reasons"])
        self.assertIn("required interpretation information is missing for LogC3", warned["reasons"])

    def test_windows_and_file_urls_are_redacted(self):
        result = evaluate(payload(
            metadataTexts=["clip=C:\\Users\\ada\\clip.mov ref=file:///home/ada/clip.mov"],
            personalIdentifiers=[],
        ))
        text = blob(result)
        self.assertNotIn("C:\\Users\\ada", text)
        self.assertNotIn("file:///home/ada", text)
        self.assertIn("[redacted-path]", text)
        self.assertEqual(result["decision"], "recorded")

    def test_published_fixture_sanitizes_without_losing_provenance(self):
        fixture = json.loads(
            (ROOT / "docs" / "P127_EXPORT_INTEROPERABLE_RESULT_BUNDLES.json").read_text()
        )
        result = assess(fixture)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p127-share-bundle", result["preservedResults"])
        text = blob(result)
        self.assertNotIn("/home/ada/Movies/private_take.mov", text)
        self.assertNotIn("ada@example.com", text)
        self.assertIn("source_sha256=", text)
        self.assertIn("not a physical S23 qualification", text)
        self.assertIn("[redacted-path]", text)

    def test_handoff_points_at_p128(self):
        handoff = json.loads((ROOT / "docs" / "evidence" / "P127-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P127")
        self.assertEqual(handoff["commit"], None)
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(handoff["nextPhase"], "P128")
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p127*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        for path in handoff["changedFiles"]:
            self.assertTrue((ROOT / path).is_file(), path)
            self.assertTrue("P127" in path or "p127" in path)
