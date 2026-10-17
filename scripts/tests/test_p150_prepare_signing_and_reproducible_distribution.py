"""Host checks for P150. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p150_prepare_signing_and_reproducible_distribution",
    Path(__file__).resolve().parents[1] / "gates" / "p150_prepare_signing_and_reproducible_distribution.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P150_PREPARE_SIGNING_AND_REPRODUCIBLE_DISTRIBUTION.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


class P150Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P150")
        self.assertEqual(_MODULE.WORKSTREAM, 19)
        self.assertEqual(_MODULE.TITLE, "Prepare signing and reproducible distribution")
        self.assertEqual(
            _MODULE.GOAL,
            "Separate debug convenience from a maintainable release and update process.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Use owner-controlled signing, pinned dependencies, reproducible source records, "
            "and explicit version migration tests. Keep secrets outside the repository. "
            "Verify installation and update without losing private sources, profiles, recipes, "
            "or recovery records.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "An update from an earlier signed release containing private RAW sources and a pending render job.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The update preserves compatible data and handles migration explicitly; "
            "signing mismatch is not solved by silently uninstalling user data.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Recommend uninstalling the previous app without warning about private footage loss.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Release signing plan and update preservation tests")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P149",))
        self.assertIn("warns_footage_loss false while recommends_uninstall true", _MODULE.UPDATE_RULE)
        self.assertIn("Debug signing must not be labelled a production update", _MODULE.UPDATE_RULE)
        self.assertIn("signing none", _MODULE.UPDATE_RULE)
        self.assertIn("same source revision", _MODULE.UPDATE_RULE)
        self.assertIn("Private footage preservation false on an update", _MODULE.UPDATE_RULE)
        self.assertEqual(_MODULE.DECISIONS, frozenset({"recorded", "rejected"}))
        self.assertNotIn("applyNegative", _MODULE.CORE_KEYS)

    def test_fixture_records_an_owner_controlled_update(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P150")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.UPDATE_RULE, " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        self.assertEqual(snapshot["build_type"], "release")
        self.assertEqual(snapshot["signing"], "upload")
        self.assertTrue(snapshot["update_preserves_private_footage"])
        self.assertTrue(snapshot["same_source_revision"])
        self.assertTrue(snapshot["owner_controlled_signing"])
        self.assertFalse(snapshot["uninstall_without_warning"])
        self.assertFalse(snapshot["release_not_reproducible"])
        self.assertFalse(snapshot["private_footage_lost"])
        self.assertEqual(snapshot["source_revision"], _MODULE.BASE_REVISION)
        self.assertEqual(snapshot["recorded_source_revision"], _MODULE.BASE_REVISION)
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_uninstall_without_footage_warning_is_rejected(self):
        result = assess(document(
            recommends_uninstall=True,
            warns_footage_loss=False,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.UNINSTALL_WITHOUT_WARNING, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertTrue(result["preservedResults"][1]["uninstall_without_warning"])
        self.assertIn("p150-signing-distribution", result["preservedResults"])
        warned = assess(document(recommends_uninstall=True, warns_footage_loss=True))
        self.assertEqual(warned["decision"], "recorded")
        self.assertNotIn(_MODULE.UNINSTALL_WITHOUT_WARNING, warned["rejectedClaims"])

    def test_apply_mutant_rejects_the_uninstall_recommendation(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNINSTALL_WITHOUT_WARNING, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertIn("p150-signing-distribution", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["preservedResults"][1]["uninstall_without_warning"])

    def test_debug_signing_must_not_be_a_production_update(self):
        result = assess(document(
            build_type="release",
            signing="debug",
            labelled_production_update=True,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DEBUG_SIGNING_AS_PRODUCTION, result["rejectedClaims"])
        self.assertIn("Debug signing must not be labelled a production update.", result["reasons"])
        self.assertTrue(result["preservedResults"][1]["debug_signing_as_production"])
        honest = assess(document(
            build_type="debug",
            signing="debug",
            labelled_production_update=False,
            is_update=False,
        ))
        self.assertEqual(honest["decision"], "recorded")
        self.assertFalse(honest["preservedResults"][1]["debug_signing_as_production"])
        self.assertIn("debug convenience", " ".join(honest["reasons"]))

    def test_release_with_signing_none_is_not_reproducible(self):
        result = assess(document(signing="none", labelled_production_update=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RELEASE_NOT_REPRODUCIBLE, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][1]["release_not_reproducible"])
        self.assertIn("not reproducible for users", " ".join(result["reasons"]))
        debug_none = assess(document(
            build_type="debug",
            signing="none",
            labelled_production_update=False,
            is_update=False,
        ))
        self.assertEqual(debug_none["decision"], "recorded")
        self.assertNotIn(_MODULE.RELEASE_NOT_REPRODUCIBLE, debug_none["rejectedClaims"])

    def test_same_source_revision_must_be_recorded(self):
        other = "cafebabe" * 5
        matched = assess(document(source_revision=other, recorded_source_revision=other))
        self.assertEqual(matched["decision"], "recorded")
        self.assertTrue(matched["preservedResults"][1]["same_source_revision"])
        self.assertEqual(matched["preservedResults"][1]["recorded_source_revision"], other)
        drifted = assess(document(recorded_source_revision="not-the-source-revision"))
        self.assertEqual(drifted["decision"], "rejected")
        self.assertIn(_MODULE.SOURCE_REVISION_NOT_RECORDED, drifted["rejectedClaims"])
        self.assertFalse(drifted["preservedResults"][1]["same_source_revision"])
        self.assertIn("same source revision", " ".join(drifted["reasons"]))

    def test_private_footage_preservation_false_on_an_update_is_rejected(self):
        result = assess(document(update_preserves_private_footage=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PRIVATE_FOOTAGE_LOST, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][1]["private_footage_lost"])
        self.assertIn("Private footage preservation false on an update is rejected.", result["reasons"])
        fresh = assess(document(is_update=False, update_preserves_private_footage=False))
        self.assertEqual(fresh["decision"], "recorded")
        self.assertNotIn(_MODULE.PRIVATE_FOOTAGE_LOST, fresh["rejectedClaims"])

    def test_faults_stack_without_qualifying(self):
        result = evaluate(_MODULE.uninstall_without_warning_plan(
            signing="none",
            labelled_production_update=False,
            recorded_source_revision="other-revision",
            update_preserves_private_footage=False,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            [
                _MODULE.UNINSTALL_WITHOUT_WARNING,
                _MODULE.RELEASE_NOT_REPRODUCIBLE,
                _MODULE.SOURCE_REVISION_NOT_RECORDED,
                _MODULE.PRIVATE_FOOTAGE_LOST,
            ],
        )
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("p150-signing-distribution", result["preservedResults"])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P151"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            document(build_type="beta"),
            document(signing="release"),
            document(update_preserves_private_footage=1),
            document(warns_footage_loss="false"),
            document(recommends_uninstall=0),
            document(labelled_production_update="yes"),
            document(is_update="true"),
            document(source_revision="  "),
            document(recorded_source_revision=""),
            document(build_type="Release"),
            document(signing="None"),
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
            evaluate(_MODULE.core_payload(signing="upload-key"))

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P150-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P150")
        self.assertEqual(handoff["nextPhase"], "P151")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p150*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P150_PREPARE_SIGNING_AND_REPRODUCIBLE_DISTRIBUTION.md").read_text(encoding="utf-8")
        self.assertIn("Release signing plan and update preservation tests", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("warns_footage_loss", note)
        self.assertIn("recommends_uninstall", note)
        self.assertIn("not reproducible", note)
        self.assertIn("same source revision", note)
        self.assertIn("private footage", note)
        self.assertIn("Debug signing", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("never `qualified` or `allowed`", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p150_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p150_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P150-0{index}")
            self.assertEqual(module.CASE["phase"], "P150")
            self.assertEqual(module.CASE["workstream"], 19)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
