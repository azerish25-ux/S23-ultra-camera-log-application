"""Host checks for P144. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p144_validate_recipe_fidelity_and_honesty",
    Path(__file__).resolve().parents[1] / "gates" / "p144_validate_recipe_fidelity_and_honesty.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P144_VALIDATE_RECIPE_FIDELITY_AND_HONESTY.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def recipe_with(base: dict, **overrides):
    value = json.loads(json.dumps(base))
    value.update(overrides)
    return value


def identification_with(recipe: dict, **overrides):
    value = json.loads(json.dumps(recipe))
    value["identification"].update(overrides)
    return value


def report_of(result):
    return result["preservedResults"][2]


class P144Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P144")
        self.assertEqual(_MODULE.WORKSTREAM, 18)
        self.assertEqual(_MODULE.TITLE, "Validate recipe fidelity and honesty")
        self.assertEqual(
            _MODULE.GOAL,
            "Evaluate whether recipes are coherent and enjoyable without overstating "
            "historical or physical accuracy.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Use matched owned sources, blind preference tests, parameter ablations, and expert review "
            "where possible. Score evidence completeness separately from appearance preference. "
            "A popular recipe may remain reconstructed; a well-sourced recipe may need artistic refinement.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "One visually preferred recipe with uncertain production facts and another fully sourced "
            "but less preferred interpretation.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The app reports these different qualities without promoting preference into factual certainty.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Use user star ratings as evidence that a stock identification is correct.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Recipe evaluation report and catalogue quality policy")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P143",))

    def test_fixture_records_preference_apart_from_identification(self):
        source = load_document()
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P144")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.STAR_NOTE, result["reasons"])
        report = report_of(result)
        self.assertTrue(report["separated"])
        preferred = report["preferred"]
        sourced = report["sourced"]
        self.assertEqual(set(("coherence", "enjoyment", "identification")).issubset(preferred), True)
        self.assertGreater(preferred["enjoyment"], sourced["enjoyment"])
        self.assertNotEqual(preferred["coherence"], preferred["enjoyment"])
        self.assertFalse(preferred["identification"]["correct"])
        self.assertIsNone(preferred["identification"]["source_id"])
        self.assertEqual(preferred["identification"]["evidence_kind"], "reconstruction")
        self.assertTrue(preferred["enjoyable_and_unidentified"])
        self.assertEqual(preferred["star_rating"], 5)
        self.assertFalse(preferred["historical_accuracy_claimed"])
        self.assertTrue(sourced["identification"]["correct"])
        self.assertEqual(sourced["identification"]["source_id"], _MODULE.OWNED_SOURCE_ID)
        self.assertEqual(sourced["identification"]["evidence_kind"], "source")
        self.assertTrue(sourced["historical_accuracy_claimed"])
        self.assertLess(sourced["star_rating"], preferred["star_rating"])
        self.assertFalse(report["policy"]["star_rating_identifies_stock"])

    def test_high_enjoyment_does_not_flip_identification(self):
        preferred = identification_with(
            _MODULE.preferred_recipe(), status="correct", evidence_kind="preference"
        )
        preferred["enjoyment"] = 1
        result = assess(document(preferred=preferred))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.HIGH_ENJOYMENT_DOES_NOT_CERTIFY, result["rejectedClaims"])
        self.assertIn(_MODULE.IDENTIFICATION_REQUIRES_SOURCE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.MUTANT, result["rejectedClaims"])
        kept = report_of(result)["preferred"]
        self.assertEqual(kept["enjoyment"], 1)
        self.assertFalse(kept["identification"]["correct"])
        self.assertIn(_MODULE.EVIDENCE_ID, result["preservedResults"])

    def test_star_rating_evidence_is_rejected_and_does_not_identify(self):
        preferred = identification_with(
            _MODULE.preferred_recipe(), status="correct", evidence_kind="star_rating"
        )
        result = assess(document(preferred=preferred, applyMutant=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STAR_RATING_AS_IDENTIFICATION, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn(_MODULE.HIGH_ENJOYMENT_DOES_NOT_CERTIFY, result["rejectedClaims"])
        kept = report_of(result)["preferred"]
        self.assertFalse(kept["identification"]["correct"])
        self.assertEqual(kept["star_rating"], 5)
        self.assertGreaterEqual(kept["enjoyment"], _MODULE.HIGH_ENJOYMENT)

    def test_enjoyable_unidentified_recipe_is_recorded(self):
        recipe = _MODULE.preferred_recipe()
        recipe["enjoyment"] = 0.99
        recipe["star_rating"] = 5
        result = evaluate({
            "evidenceId": "p144-enjoyable-unidentified",
            "claim": _MODULE.CLAIM,
            "caseId": "P144",
            "applyMutant": False,
            "recipe": recipe,
        })
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(report_of(result)["identification"]["correct"])
        self.assertTrue(report_of(result)["enjoyable_and_unidentified"])
        self.assertIn("p144-enjoyable-unidentified", result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])

    def test_null_enjoyment_stays_null_and_unidentified(self):
        recipe = _MODULE.preferred_recipe()
        recipe["enjoyment"] = None
        recipe["identification"]["status"] = "unidentified"
        recipe["identification"]["evidence_kind"] = "none"
        recipe["star_rating"] = None
        result = evaluate({
            "evidenceId": "p144-null-enjoyment",
            "claim": _MODULE.CLAIM,
            "caseId": "P144",
            "applyMutant": False,
            "recipe": recipe,
        })
        self.assertEqual(result["decision"], "recorded")
        self.assertIsNone(report_of(result)["enjoyment"])
        self.assertFalse(report_of(result)["identification"]["correct"])
        self.assertFalse(report_of(result)["enjoyable_and_unidentified"])

    def test_historical_accuracy_without_a_source_is_rejected(self):
        preferred = recipe_with(_MODULE.preferred_recipe(), historical_accuracy_claimed=True)
        result = assess(document(preferred=preferred))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HISTORICAL_ACCURACY_WITHOUT_SOURCE, result["rejectedClaims"])
        self.assertFalse(report_of(result)["preferred"]["identification"]["correct"])
        self.assertIn(_MODULE.EVIDENCE_ID, result["preservedResults"])

    def test_sourced_recipe_stays_correct_when_enjoyment_is_high(self):
        sourced = recipe_with(_MODULE.sourced_recipe(), enjoyment=1, star_rating=5)
        result = assess(document(sourced=sourced))
        self.assertEqual(result["decision"], "recorded")
        kept = report_of(result)["sourced"]
        self.assertTrue(kept["identification"]["correct"])
        self.assertEqual(kept["identification"]["evidence_kind"], "source")
        self.assertEqual(kept["enjoyment"], 1)
        self.assertFalse(report_of(result)["preferred"]["identification"]["correct"])

    def test_mutant_and_policy_that_trusts_stars_are_rejected(self):
        mutant = assess(document(applyMutant=True))
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, mutant["rejectedClaims"])
        self.assertIn(_MODULE.EVIDENCE_ID, mutant["preservedResults"])
        policy = _MODULE.catalogue_policy()
        policy["star_rating_identifies_stock"] = True
        refused = assess(document(policy=policy))
        self.assertEqual(refused["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, refused["rejectedClaims"])
        self.assertFalse(report_of(refused)["preferred"]["identification"]["correct"])

    def test_evaluate_document_matches_assess(self):
        source = _MODULE.fixture_document()
        self.assertEqual(evaluate(source), assess(_MODULE.fixture_document()))

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            assess(document(decision="qualified"))
        with self.assertRaises(ValueError):
            evaluate({
                "evidenceId": "p144-bad",
                "claim": _MODULE.CLAIM,
                "caseId": "P144",
                "applyMutant": False,
                "recipe": recipe_with(_MODULE.preferred_recipe(), coherence=1.2),
            })
        with self.assertRaises(ValueError):
            evaluate({
                "evidenceId": "p144-bad",
                "claim": _MODULE.CLAIM,
                "caseId": "P144",
                "applyMutant": False,
                "recipe": recipe_with(_MODULE.preferred_recipe(), enjoyment=True),
            })
        bad_kind = identification_with(_MODULE.preferred_recipe(), evidence_kind="Source")
        with self.assertRaises(ValueError):
            assess(document(preferred=bad_kind))
        with self.assertRaises(ValueError):
            assess(document(implementationBaseRevision="deadbeef"))
