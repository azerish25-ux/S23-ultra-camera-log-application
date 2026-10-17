"""Host checks for P147. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p147_secure_media_and_profile_import_boundaries",
    Path(__file__).resolve().parents[1] / "gates" / "p147_secure_media_and_profile_import_boundaries.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P147_SECURE_MEDIA_AND_PROFILE_IMPORT_BOUNDARIES.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def replace_import(import_id: str, **overrides) -> list:
    rows = _MODULE.fixture_imports()
    found = False
    for row in rows:
        if row["id"] == import_id:
            row.update(overrides)
            found = True
    if not found:
        raise AssertionError(import_id)
    return rows


def replace_corpus(corpus_id: str, **overrides) -> list:
    rows = _MODULE.fixture_corpus()
    found = False
    for row in rows:
        if row["id"] == corpus_id:
            row.update(overrides)
            found = True
    if not found:
        raise AssertionError(corpus_id)
    return rows


class P147Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P147")
        self.assertEqual(_MODULE.WORKSTREAM, 19)
        self.assertEqual(_MODULE.TITLE, "Secure media and profile import boundaries")
        self.assertEqual(
            _MODULE.GOAL,
            "Treat external files, archives, LUTs, models, and profiles as hostile until validated.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Bound lengths, dimensions, nesting, decompression, and allocation before use. "
            "Validate paths and hashes, restrict URI grants, and keep native parsers current. "
            "Reject nonfinite matrices and dangerous archive paths. Fuzz parsers with retained "
            "minimal reproducers.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A profile containing NaN, a huge declared image dimension, and an archive path attempting parent traversal.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "All inputs fail safely without excessive allocation, file escape, or source corruption.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Trust extension names and allocate according to unvalidated headers.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Import threat model and parser fuzz corpus")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P146",))
        self.assertEqual(_MODULE.SIZE_TOLERANCE, 0)
        self.assertEqual(_MODULE.IMPORT_KINDS, ("media", "archive", "lut", "model", "profile"))
        self.assertIn("magic disagrees", _MODULE.IMPORT_RULE)
        self.assertIn("header_validated false", _MODULE.IMPORT_RULE)
        self.assertIn("within 0", _MODULE.IMPORT_RULE)
        self.assertIn("../", _MODULE.IMPORT_RULE)
        self.assertIn("recorded", _MODULE.IMPORT_RULE)
        self.assertNotIn("applyNegative", _MODULE.IMPORT_RULE)

    def test_fixture_records_validated_imports_and_rejects_the_corpus(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P147")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn(_MODULE.IMPORT_RULE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        self.assertEqual(snapshot["sizeTolerance"], 0)
        self.assertEqual(snapshot["validatedCount"], 5)
        self.assertEqual(snapshot["rejectedCorpusCount"], 4)
        self.assertEqual(snapshot["importDecisions"]["media-dng"], "recorded")
        self.assertEqual(snapshot["importDecisions"]["archive-zip"], "recorded")
        self.assertEqual(snapshot["importDecisions"]["lut-cube"], "recorded")
        self.assertEqual(snapshot["importDecisions"]["model-onnx"], "recorded")
        self.assertEqual(snapshot["importDecisions"]["profile-json"], "recorded")
        self.assertEqual(snapshot["importFaults"]["profile-json"], [])
        self.assertEqual(snapshot["corpusDecisions"]["nan-profile"], "rejected")
        self.assertIn(_MODULE.NONFINITE, snapshot["corpusFaults"]["nan-profile"])
        self.assertIn(_MODULE.EXCESSIVE_DIMENSION, snapshot["corpusFaults"]["huge-dimension"])
        self.assertIn(_MODULE.PATH_TRAVERSAL, snapshot["corpusFaults"]["archive-traversal"])
        mutant = snapshot["corpusFaults"]["trust-extension-unvalidated-header"]
        self.assertIn(_MODULE.TRUSTED_EXTENSION, mutant)
        self.assertIn(_MODULE.UNVALIDATED_HEADER, mutant)
        self.assertIn(_MODULE.SIZE_MISMATCH, mutant)
        self.assertNotIn(_MODULE.EXCESSIVE_ALLOCATION, mutant)
        self.assertNotIn(_MODULE.FILE_ESCAPE, mutant)
        self.assertNotIn(_MODULE.SOURCE_CORRUPTION, mutant)
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_magic_disagreement_is_rejected(self):
        result = assess(document(imports=replace_import("lut-cube", magic="PK", trust_extension=True)))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.TRUSTED_EXTENSION, result["rejectedClaims"])
        self.assertIn("p147-secure-import", result["preservedResults"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertIn("trusting the extension while magic disagrees", " ".join(result["reasons"]))
        bare = assess(document(imports=replace_import("media-dng", magic="PK")))
        self.assertIn(_MODULE.TRUSTED_EXTENSION, bare["rejectedClaims"])
        self.assertEqual(bare["preservedResults"][1]["importDecisions"]["media-dng"], "rejected")

    def test_unvalidated_header_allocation_is_rejected(self):
        result = assess(document(imports=replace_import("model-onnx", header_validated=False, allocated=0)))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNVALIDATED_HEADER, result["rejectedClaims"])
        self.assertIn("header_validated false", " ".join(result["reasons"]))
        self.assertEqual(result["preservedResults"][1]["importDecisions"]["model-onnx"], "rejected")

    def test_size_must_match_within_zero(self):
        self.assertTrue(_MODULE.sizes_match(1024, 1024))
        self.assertFalse(_MODULE.sizes_match(1024, 1025))
        self.assertFalse(_MODULE.sizes_match(1024, 1023))
        matched = assess(document(imports=replace_import("media-dng", declared_size=2048, actual_size=2048)))
        self.assertEqual(matched["decision"], "recorded")
        off_by_one = assess(document(imports=replace_import("media-dng", actual_size=1025)))
        self.assertEqual(off_by_one["decision"], "rejected")
        self.assertEqual(
            off_by_one["preservedResults"][1]["importFaults"]["media-dng"],
            [_MODULE.SIZE_MISMATCH],
        )
        self.assertIn("within 0", " ".join(off_by_one["reasons"]))

    def test_archive_parent_traversal_is_rejected(self):
        traversed = assess(document(imports=replace_import("archive-zip", paths=["../escape"])))
        self.assertEqual(traversed["decision"], "rejected")
        self.assertIn(_MODULE.PATH_TRAVERSAL, traversed["rejectedClaims"])
        nested = assess(document(imports=replace_import("archive-zip", paths=["luts/../../secret.cube"])))
        self.assertIn(_MODULE.PATH_TRAVERSAL, nested["rejectedClaims"])
        windows = assess(document(imports=replace_import("media-dng", paths=["..\\escape.dng"])))
        self.assertIn(_MODULE.PATH_TRAVERSAL, windows["rejectedClaims"])
        self.assertTrue(_MODULE.path_traverses("../escape"))
        self.assertFalse(_MODULE.path_traverses("imports/archive-zip.zip"))

    def test_nonfinite_profile_and_huge_dimension_fail_safely(self):
        values = _MODULE.identity_matrix()
        values[0] = float("nan")
        nan_result = assess(document(imports=replace_import("profile-json", values=values)))
        self.assertEqual(nan_result["decision"], "rejected")
        self.assertIn(_MODULE.NONFINITE, nan_result["rejectedClaims"])
        huge = assess(document(imports=replace_import(
            "media-dng",
            width=_MODULE.MAX_DIMENSION + 1,
            height=_MODULE.MAX_DIMENSION + 1,
            allocated=0,
        )))
        self.assertEqual(huge["decision"], "rejected")
        self.assertIn(_MODULE.EXCESSIVE_DIMENSION, huge["rejectedClaims"])
        self.assertNotIn(_MODULE.EXCESSIVE_ALLOCATION, huge["rejectedClaims"])

    def test_corpus_that_escapes_or_is_not_hostile_is_rejected(self):
        escaped = assess(document(corpus=replace_corpus("archive-traversal", escaped=True, source_corrupted=True)))
        self.assertEqual(escaped["decision"], "rejected")
        self.assertIn(_MODULE.FILE_ESCAPE, escaped["rejectedClaims"])
        self.assertIn(_MODULE.SOURCE_CORRUPTION, escaped["rejectedClaims"])
        self.assertIn(_MODULE.CORPUS_UNSAFE, escaped["rejectedClaims"])
        benign = assess(document(corpus=_MODULE.fixture_imports()))
        self.assertEqual(benign["decision"], "rejected")
        self.assertIn(_MODULE.CORPUS_NOT_HOSTILE, benign["rejectedClaims"])
        self.assertIn(_MODULE.FIXTURE_INCOMPLETE, benign["rejectedClaims"])

    def test_missing_kind_and_incomplete_fixture_are_rejected(self):
        imports = [row for row in _MODULE.fixture_imports() if row["kind"] != "profile"]
        result = assess(document(imports=imports))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.KIND_GAP, result["rejectedClaims"])
        corpus = [row for row in _MODULE.fixture_corpus() if row["id"] != "nan-profile"]
        incomplete = assess(document(corpus=corpus))
        self.assertIn(_MODULE.FIXTURE_INCOMPLETE, incomplete["rejectedClaims"])

    def test_minimal_validated_import_is_recorded_and_disagreement_is_not(self):
        recorded = _MODULE.parse_import({
            "kind": "media",
            "declared_size": 10,
            "actual_size": 10,
            "extension": "dng",
            "magic": "dng",
            "header_validated": True,
            "paths": ["clip.dng"],
        }, "minimal")
        self.assertEqual(recorded["decision"], "recorded")
        self.assertEqual(recorded["faults"], [])
        rejected = _MODULE.parse_import({
            "kind": "archive",
            "declared_size": 10,
            "actual_size": 11,
            "extension": "zip",
            "magic": "dng",
            "header_validated": False,
            "paths": ["../clip.zip"],
        }, "hostile")
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn(_MODULE.TRUSTED_EXTENSION, rejected["faults"])
        self.assertIn(_MODULE.UNVALIDATED_HEADER, rejected["faults"])
        self.assertIn(_MODULE.SIZE_MISMATCH, rejected["faults"])
        self.assertIn(_MODULE.PATH_TRAVERSAL, rejected["faults"])

    def test_zip_signature_matches_without_trusting_the_extension_name(self):
        self.assertFalse(_MODULE.magic_disagrees("zip", "PK"))
        self.assertFalse(_MODULE.magic_disagrees("zip", "zip"))
        self.assertTrue(_MODULE.magic_disagrees("cube", "PK"))
        self.assertEqual(_MODULE.EXTENSION_MAGIC["zip"], "PK")

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P148"),
            document(implementationBaseRevision="deadbeef"),
            document(extra=True),
            document(imports=[]),
            document(corpus=[]),
            document(imports=replace_import("media-dng", declared_size=True)),
            document(imports=replace_import("media-dng", header_validated="yes")),
            document(imports=replace_import("media-dng", kind="video")),
            document(imports=replace_import("media-dng", applyNegative=True)),
            document(imports=replace_import("media-dng", allocated=-1)),
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
            evaluate({"applyNegative": True})

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P147-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P147")
        self.assertEqual(handoff["nextPhase"], "P148")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p147*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P147_SECURE_MEDIA_AND_PROFILE_IMPORT_BOUNDARIES.md").read_text(encoding="utf-8")
        self.assertIn("Import threat model and parser fuzz corpus", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("magic disagrees", note)
        self.assertIn("header_validated", note)
        self.assertIn("within 0", note)
        self.assertIn("../", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("never `qualified` or `allowed`", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p147_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p147_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P147-0{index}")
            self.assertEqual(module.CASE["phase"], "P147")
            self.assertEqual(module.CASE["workstream"], 19)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
