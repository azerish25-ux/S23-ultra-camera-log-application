"""Host checks for P152. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p152_run_the_production_readiness_review",
    Path(__file__).resolve().parents[1] / "gates" / "p152_run_the_production_readiness_review.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P152_RUN_THE_PRODUCTION_READINESS_REVIEW.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


class P152Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P152")
        self.assertEqual(_MODULE.WORKSTREAM, 19)
        self.assertEqual(_MODULE.TITLE, "Run the production readiness review")
        self.assertEqual(
            _MODULE.GOAL,
            "Make a deliberate release decision based on critical risks and complete workflows.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Review footage retention, crash recovery, color signalling, temporal artifacts, "
            "licensing, privacy, accessibility, and update safety. Resolve or explicitly defer "
            "noncritical issues. A critical data-loss or misleading-capture defect blocks release "
            "regardless of visual quality.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A visually excellent build that occasionally deletes the only staging copy after a failed publication.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The release is blocked until preservation is fixed and regression evidence exists.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Waive a critical data-loss issue because promotional footage looks convincing.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Production readiness dossier and signed-off decision record")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P151",))
        self.assertIn("release_decision must be hold", _MODULE.RELEASE_RULE)
        self.assertIn("looks_convincing", _MODULE.RELEASE_RULE)
        self.assertIn("cites the risk ids", _MODULE.RELEASE_RULE)
        self.assertIn("Promotional footage is not evidence", _MODULE.RELEASE_RULE)
        self.assertIn("never qualified", _MODULE.RELEASE_RULE)

    def test_fixed_preservation_go_is_recorded(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P152")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.RELEASE_RULE, " ".join(result["reasons"]))
        self.assertIn("release go recorded", " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        self.assertEqual(snapshot["release_decision"], "go")
        self.assertEqual(snapshot["openCriticalIds"], [])
        self.assertEqual(snapshot["missingCitations"], [])
        self.assertTrue(snapshot["preservationFixed"])
        self.assertEqual(snapshot["regressionEvidenceIds"], ["regression-staging-copy"])
        self.assertEqual(snapshot["promotionalFootageIds"], [])
        self.assertEqual(snapshot["waivedDataLossIds"], [])
        self.assertEqual(snapshot["visualQuality"], "excellent")
        self.assertFalse(snapshot["mutantApplied"])
        self.assertEqual(snapshot["dataLoss"][0]["status"], "closed")
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_open_critical_go_is_rejected_and_hold_is_recorded(self):
        risks = _MODULE.replace_risk(
            "staging-copy-deleted",
            status="open",
            reason="sole staging copy deleted after failed publication",
        )
        refused = assess(document(risks=risks, release_decision="go"))
        self.assertEqual(refused["decision"], "rejected")
        self.assertNotIn(refused["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.OPEN_CRITICAL_REQUIRES_HOLD, refused["rejectedClaims"])
        self.assertIn(_MODULE.CRITICAL_DEFECT_BLOCKS, refused["rejectedClaims"])
        self.assertIn(_MODULE.PRESERVATION_NOT_FIXED, refused["rejectedClaims"])
        self.assertIn(_MODULE.VISUAL_QUALITY_CANNOT_WAIVE, refused["rejectedClaims"])
        self.assertIn("staging-copy-deleted", refused["preservedResults"][1]["openCriticalIds"])
        self.assertFalse(refused["preservedResults"][1]["preservationFixed"])
        self.assertIn("p152-production-readiness", refused["preservedResults"])
        self.assertIn("release_decision must be hold", " ".join(refused["reasons"]))

        held = assess(document(risks=risks, release_decision="hold"))
        self.assertEqual(held["decision"], "recorded")
        self.assertEqual(held["rejectedClaims"], [])
        self.assertEqual(held["preservedResults"][1]["release_decision"], "hold")
        self.assertIn("release hold recorded", " ".join(held["reasons"]))
        self.assertFalse(held["preservedResults"][1]["preservationFixed"])

    def test_critical_data_loss_waiver_with_convincing_or_empty_reason_is_rejected(self):
        convincing = _MODULE.replace_risk(
            "staging-copy-deleted",
            status="accepted",
            reason="looks_convincing",
        )
        result = assess(document(risks=convincing, release_decision="hold"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DATA_LOSS_WAIVER_REJECTED, result["rejectedClaims"])
        self.assertIn("staging-copy-deleted", result["preservedResults"][1]["waivedDataLossIds"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

        empty = _MODULE.replace_risk(
            "staging-copy-deleted",
            status="accepted",
            reason="",
        )
        empty_result = assess(document(risks=empty, release_decision="go"))
        self.assertEqual(empty_result["decision"], "rejected")
        self.assertIn(_MODULE.DATA_LOSS_WAIVER_REJECTED, empty_result["rejectedClaims"])
        self.assertIn(_MODULE.CRITICAL_DEFECT_BLOCKS, empty_result["rejectedClaims"])
        self.assertIn(_MODULE.PRESERVATION_NOT_FIXED, empty_result["rejectedClaims"])
        self.assertIn(_MODULE.VISUAL_QUALITY_CANNOT_WAIVE, empty_result["rejectedClaims"])

    def test_polite_acceptance_still_cannot_go(self):
        risks = _MODULE.replace_risk(
            "staging-copy-deleted",
            status="accepted",
            reason="tracked for a later maintenance window",
        )
        going = assess(document(risks=risks, release_decision="go"))
        self.assertEqual(going["decision"], "rejected")
        self.assertIn(_MODULE.CRITICAL_DEFECT_BLOCKS, going["rejectedClaims"])
        self.assertIn(_MODULE.PRESERVATION_NOT_FIXED, going["rejectedClaims"])
        self.assertNotIn(_MODULE.DATA_LOSS_WAIVER_REJECTED, going["rejectedClaims"])
        holding = assess(document(risks=risks, release_decision="hold"))
        self.assertEqual(holding["decision"], "recorded")
        self.assertEqual(holding["rejectedClaims"], [])

    def test_go_without_cited_risk_ids_is_rejected(self):
        cited = _MODULE.cited_for(_MODULE.fixture_risks())[:-1]
        result = assess(document(citedRiskIds=cited))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RISK_IDS_NOT_CITED, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["missingCitations"], ["signed-update"])
        self.assertIn("p152-production-readiness", result["preservedResults"])
        self.assertTrue(result["preservedResults"][1]["preservationFixed"])

    def test_promotional_footage_is_not_evidence(self):
        promo_only = [{"id": "promo-reel", "kind": "promotional-footage"}]
        only = assess(document(evidence=promo_only))
        self.assertEqual(only["decision"], "rejected")
        self.assertIn(_MODULE.PROMOTIONAL_FOOTAGE, only["rejectedClaims"])
        self.assertIn(_MODULE.PRESERVATION_NOT_FIXED, only["rejectedClaims"])
        self.assertEqual(only["preservedResults"][1]["regressionEvidenceIds"], [])
        self.assertEqual(only["preservedResults"][1]["promotionalFootageIds"], ["promo-reel"])
        self.assertFalse(only["preservedResults"][1]["preservationFixed"])

        mixed = _MODULE.fixture_evidence() + [{"id": "promo-reel", "kind": "promotional-footage"}]
        both = assess(document(evidence=mixed))
        self.assertEqual(both["decision"], "rejected")
        self.assertIn(_MODULE.PROMOTIONAL_FOOTAGE, both["rejectedClaims"])
        self.assertEqual(both["preservedResults"][1]["regressionEvidenceIds"], ["regression-staging-copy"])
        self.assertTrue(both["preservedResults"][1]["preservationFixed"])
        self.assertIn("promotional footage is not evidence", " ".join(both["reasons"]))

    def test_apply_mutant_rejects_the_waiver_without_rewriting_the_dossier(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DATA_LOSS_WAIVER_REJECTED, result["rejectedClaims"])
        self.assertIn(_MODULE.PROMOTIONAL_FOOTAGE, result["rejectedClaims"])
        self.assertIn(_MODULE.VISUAL_QUALITY_CANNOT_WAIVE, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertTrue(result["preservedResults"][1]["mutantApplied"])
        self.assertIn("p152-production-readiness", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_missing_area_open_noncritical_and_bad_deferral_are_rejected(self):
        risks = [risk for risk in _MODULE.fixture_risks() if risk["id"] != "license-attribution"]
        cited = [risk_id for risk_id in _MODULE.cited_for(_MODULE.fixture_risks()) if risk_id != "license-attribution"]
        missing = assess(document(risks=risks, citedRiskIds=cited))
        self.assertEqual(missing["decision"], "rejected")
        self.assertIn(_MODULE.REVIEW_AREA_MISSING, missing["rejectedClaims"])
        self.assertIn("licensing", missing["preservedResults"][1]["missingAreas"])

        opened = _MODULE.replace_risk("temporal-cadence", status="open", reason="still investigating cadence")
        unresolved = assess(document(risks=opened))
        self.assertEqual(unresolved["decision"], "rejected")
        self.assertIn(_MODULE.NONCRITICAL_OPEN, unresolved["rejectedClaims"])

        deferred = _MODULE.replace_risk("crash-checkpoint", reason="looks_convincing")
        bad = assess(document(risks=deferred))
        self.assertEqual(bad["decision"], "rejected")
        self.assertIn(_MODULE.DEFERRAL_NOT_EXPLICIT, bad["rejectedClaims"])
        self.assertNotIn(_MODULE.DATA_LOSS_WAIVER_REJECTED, bad["rejectedClaims"])

    def test_downgraded_data_loss_and_open_misleading_capture_block_go(self):
        downgraded = _MODULE.replace_risk(
            "staging-copy-deleted",
            severity="major",
            category="footage-retention",
        )
        result = assess(document(risks=downgraded))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DATA_LOSS_RISK_MISSING, result["rejectedClaims"])
        self.assertIn(_MODULE.PRESERVATION_NOT_FIXED, result["rejectedClaims"])

        misleading = _MODULE.replace_risk(
            "color-range",
            severity="critical",
            status="open",
            category="misleading-capture",
            reason="range tag still advertises the wrong capture",
        )
        going = assess(document(risks=misleading, release_decision="go"))
        self.assertEqual(going["decision"], "rejected")
        self.assertIn(_MODULE.OPEN_CRITICAL_REQUIRES_HOLD, going["rejectedClaims"])
        self.assertIn(_MODULE.CRITICAL_DEFECT_BLOCKS, going["rejectedClaims"])
        holding = assess(document(risks=misleading, release_decision="hold"))
        self.assertEqual(holding["decision"], "recorded")
        self.assertIn("color-range", holding["preservedResults"][1]["openCriticalIds"])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P153"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            document(release_decision="qualified"),
            document(release_decision="allowed"),
            document(visualQuality=""),
            document(risks=[]),
            document(citedRiskIds=["not-a-risk"]),
            document(evidence=[{"id": "clip", "kind": "promotional"}]),
            document(risks=_MODULE.replace_risk("focus-order", severity="severe")),
            document(risks=_MODULE.replace_risk("focus-order", status="waived")),
            document(risks=_MODULE.replace_risk("focus-order", reason=" padded ")),
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
            evaluate(_MODULE.core_payload(applyNegative=True))

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P152-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P152")
        self.assertEqual(handoff["nextPhase"], "P153")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p152*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P152_RUN_THE_PRODUCTION_READINESS_REVIEW.md").read_text(encoding="utf-8")
        self.assertIn("Production readiness dossier and signed-off decision record", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("release_decision must be hold", note)
        self.assertIn("looks_convincing", note)
        self.assertIn("cites the risk ids", note)
        self.assertIn("Promotional footage is not evidence", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("never `qualified` or `allowed`", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p152_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p152_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P152-0{index}")
            self.assertEqual(module.CASE["phase"], "P152")
            self.assertEqual(module.CASE["workstream"], 19)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
