"""Host checks for P159. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p159_explore_higher_quality_computational_optics",
    Path(__file__).resolve().parents[1] / "gates" / "p159_explore_higher_quality_computational_optics.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P159_EXPLORE_HIGHER_QUALITY_COMPUTATIONAL_OPTICS.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def within_budget(**overrides):
    base = {
        "memoryBytes": 400,
        "memoryBudgetBytes": 512,
        "deferredTimeMs": 300,
        "deferredBudgetMs": 400,
        "licenseDeclared": True,
        "converted": True,
        "difficultScenesValidated": True,
        "namedLimit": "deferred-render-ms",
    }
    base.update(overrides)
    return _MODULE.fixture_candidate(**base)


class P159Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P159")
        self.assertEqual(_MODULE.WORKSTREAM, 20)
        self.assertEqual(_MODULE.TITLE, "Explore higher-quality computational optics")
        self.assertEqual(
            _MODULE.GOAL,
            "Investigate richer depth, multi-view cues, or research models only after the "
            "baseline product is stable.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Compare real synchronized inputs where available, improved temporal models, and "
            "calibrated geometry under explicit resource and privacy limits. Keep the original "
            "on-device workflow usable. New models require licensing, conversion, and "
            "difficult-scene validation again.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A larger temporal model improving some boundaries but causing memory pressure and "
            "unacceptable deferred rendering time.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The decision reports the quality-cost tradeoff rather than replacing the stable "
            "path automatically.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Adopt a larger model solely because its benchmark ranking is higher.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Advanced optics research comparison and adoption gate")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P158",))
        self.assertIn("candidate_error is not lower than baseline_error", _MODULE.ADOPTION_RULE)
        self.assertIn("only rank is cited", _MODULE.ADOPTION_RULE)
        self.assertIn("measured error improvement", _MODULE.ADOPTION_RULE)
        self.assertIn("named limit", _MODULE.ADOPTION_RULE)
        self.assertIn("Larger model size alone is not a reason", _MODULE.ADOPTION_RULE)
        self.assertIn("never qualified", _MODULE.ADOPTION_RULE)
        self.assertIn("Baseline product stability must be noted", _MODULE.ADOPTION_RULE)
        self.assertIn("baseline_stable is false", _MODULE.ADOPTION_RULE)

    def test_fixture_reports_the_tradeoff_and_retains_the_baseline(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P159")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn("oracle: " + _MODULE.ORACLE, result["reasons"])
        self.assertIn("adoption rule: " + _MODULE.ADOPTION_RULE, result["reasons"])
        self.assertIn("stable path retained", " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        row = snapshot["candidates"][0]
        self.assertEqual(row["name"], "larger-temporal-model")
        self.assertEqual(row["benchmark_rank"], 1)
        self.assertEqual(row["baseline_error"], 42)
        self.assertEqual(row["candidate_error"], 31)
        self.assertTrue(row["errorImproved"])
        self.assertTrue(row["rankBetter"])
        self.assertTrue(row["modelLarger"])
        self.assertFalse(row["adopted"])
        self.assertTrue(row["memoryPressure"])
        self.assertTrue(row["deferredUnacceptable"])
        self.assertTrue(row["costExceeded"])
        self.assertEqual(row["namedLimit"], "deferred-render-ms")
        self.assertTrue(snapshot["baseline_stable"])
        self.assertEqual(snapshot["stabilityNoted"], "baseline product stable")
        self.assertTrue(snapshot["qualityCostTradeoffReported"])
        self.assertFalse(snapshot["automaticReplacement"])
        self.assertFalse(snapshot["adoptionRejected"])
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_rank_without_lower_error_is_rejected(self):
        candidate = within_budget(
            adopted=True,
            candidate_error=_MODULE.FIXTURE_BASELINE_ERROR,
            citedReasons=["boundary-error", "memory-pressure"],
        )
        result = assess(document(candidates=[candidate]))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], [_MODULE.RANK_ONLY_ADOPTION])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("p159-computational-optics", result["preservedResults"])
        self.assertIn("candidate_error is not lower than baseline_error", " ".join(result["reasons"]))
        self.assertFalse(result["preservedResults"][1]["candidates"][0]["errorImproved"])
        self.assertTrue(result["preservedResults"][1]["candidates"][0]["adopted"])

    def test_only_rank_citation_is_rejected_even_when_error_improves(self):
        candidate = within_budget(adopted=True, citedReasons=["benchmark_rank"])
        result = assess(document(candidates=[candidate]))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], [_MODULE.ONLY_RANK_CITED])
        self.assertTrue(result["preservedResults"][1]["candidates"][0]["errorImproved"])
        self.assertTrue(result["preservedResults"][1]["candidates"][0]["onlyRankCited"])
        self.assertIn("only rank is cited", result["reasons"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        leaderboard = within_budget(adopted=False, citedReasons=["leaderboard"])
        cited = assess(document(candidates=[leaderboard]))
        self.assertEqual(cited["decision"], "rejected")
        self.assertIn(_MODULE.ONLY_RANK_CITED, cited["rejectedClaims"])

    def test_adoption_requires_a_named_limit_and_revalidation(self):
        missing_limit = _MODULE.adopting_candidate(namedLimit=None)
        result = assess(document(candidates=[missing_limit]))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], [_MODULE.MISSING_NAMED_LIMIT])
        self.assertIn("named limit", " ".join(result["reasons"]))
        unlicensed = _MODULE.adopting_candidate(licenseDeclared=False)
        licensed = assess(document(candidates=[unlicensed]))
        self.assertEqual(licensed["rejectedClaims"], [_MODULE.REVALIDATION_INCOMPLETE])
        unconverted = assess(document(candidates=[_MODULE.adopting_candidate(converted=False)]))
        self.assertIn(_MODULE.REVALIDATION_INCOMPLETE, unconverted["rejectedClaims"])
        unvalidated = assess(
            document(candidates=[_MODULE.adopting_candidate(difficultScenesValidated=False)])
        )
        self.assertIn(_MODULE.REVALIDATION_INCOMPLETE, unvalidated["rejectedClaims"])

    def test_larger_model_size_alone_is_not_a_reason(self):
        size_only = within_budget(adopted=True, citedReasons=["model-size"])
        result = assess(document(candidates=[size_only]))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], [_MODULE.SIZE_ALONE])
        self.assertTrue(result["preservedResults"][1]["candidates"][0]["errorImproved"])
        self.assertTrue(result["preservedResults"][1]["candidates"][0]["modelLarger"])
        self.assertIn("Larger model size alone is not a reason", result["reasons"])
        refused = assess(document(candidates=[within_budget(adopted=False, citedReasons=["size"])]))
        self.assertIn(_MODULE.SIZE_ALONE, refused["rejectedClaims"])
        accepted = assess(document(candidates=[_MODULE.adopting_candidate()]))
        self.assertEqual(accepted["decision"], "recorded")
        self.assertTrue(accepted["preservedResults"][1]["candidates"][0]["modelLarger"])
        self.assertTrue(accepted["preservedResults"][1]["candidates"][0]["adopted"])
        self.assertNotIn(_MODULE.SIZE_ALONE, accepted["rejectedClaims"])

    def test_unstable_or_unnoted_baseline_rejects_adoption(self):
        unstable = assess(document(
            baseline_stable=False,
            stabilityNoted=_MODULE.UNSTABLE_NOTE,
            candidates=[_MODULE.adopting_candidate()],
        ))
        self.assertEqual(unstable["decision"], "rejected")
        self.assertIn(_MODULE.BASELINE_UNSTABLE, unstable["rejectedClaims"])
        self.assertNotIn(_MODULE.BASELINE_NOT_NOTED, unstable["rejectedClaims"])
        self.assertFalse(unstable["preservedResults"][1]["baseline_stable"])
        self.assertTrue(unstable["preservedResults"][1]["adoptionRejected"])
        self.assertIn("baseline_stable is false; adoption is rejected", unstable["reasons"])
        unnoted = assess(document(stabilityNoted="looks fine"))
        self.assertEqual(unnoted["decision"], "rejected")
        self.assertEqual(unnoted["rejectedClaims"], [_MODULE.BASELINE_NOT_NOTED])
        self.assertIn("Baseline product stability must be noted", unnoted["reasons"])
        mismatched = assess(document(baseline_stable=False, stabilityNoted=_MODULE.STABLE_NOTE))
        self.assertIn(_MODULE.BASELINE_UNSTABLE, mismatched["rejectedClaims"])
        self.assertIn(_MODULE.BASELINE_NOT_NOTED, mismatched["rejectedClaims"])

    def test_cost_regression_does_not_replace_the_stable_path(self):
        candidate = _MODULE.fixture_candidate(
            adopted=True,
            licenseDeclared=True,
            converted=True,
            difficultScenesValidated=True,
        )
        result = assess(document(candidates=[candidate]))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], [_MODULE.COST_TRADEOFF_IGNORED])
        self.assertTrue(result["preservedResults"][1]["automaticReplacement"])
        self.assertFalse(result["preservedResults"][1]["qualityCostTradeoffReported"])
        self.assertTrue(result["preservedResults"][1]["candidates"][0]["errorImproved"])
        self.assertIn(_MODULE.ORACLE, result["reasons"])
        self.assertIn("memory pressure 900>512", " ".join(result["reasons"]))
        self.assertIn("unacceptable deferred rendering 2400ms>400ms", " ".join(result["reasons"]))

    def test_apply_mutant_rejects_rank_only_adoption(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], [_MODULE.RANK_ONLY_ADOPTION, _MODULE.ONLY_RANK_CITED])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertIn("p159-computational-optics", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_measurement_compares_rank_error_and_cost(self):
        measured = _MODULE.measure_candidate(_MODULE.fixture_candidate(), _MODULE.FIXTURE_BASELINE_RANK)
        self.assertTrue(measured["errorImproved"])
        self.assertTrue(measured["rankBetter"])
        self.assertTrue(measured["costExceeded"])
        self.assertEqual(_MODULE.candidate_blockers(measured), [])
        worse = _MODULE.measure_candidate(
            within_budget(adopted=True, candidate_error=50, benchmark_rank=1),
            4,
        )
        self.assertFalse(worse["errorImproved"])
        self.assertTrue(worse["rankBetter"])
        self.assertEqual(_MODULE.candidate_blockers(worse), [_MODULE.RANK_ONLY_ADOPTION])
        tied = _MODULE.measure_candidate(within_budget(adopted=True, candidate_error=42), 4)
        self.assertFalse(tied["errorImproved"])
        self.assertIn(_MODULE.RANK_ONLY_ADOPTION, _MODULE.candidate_blockers(tied))

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P160"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(baseline_stable="yes"),
            document(extra=True),
            document(candidates=[]),
            document(candidates=[_MODULE.fixture_candidate(candidate_error=float("nan"))]),
            document(candidates=[_MODULE.fixture_candidate(adopted="yes")]),
            document(candidates=[_MODULE.fixture_candidate(benchmark_rank=0)]),
            document(candidates=[_MODULE.fixture_candidate(citedReasons=["benchmark_rank", "benchmark_rank"])]),
            document(candidates=[_MODULE.fixture_candidate(namedLimit="vibes")]),
            document(stabilityNoted=""),
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
            evaluate(_MODULE.core_payload(candidates=[_MODULE.fixture_candidate(name="")]))

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P159-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P159")
        self.assertEqual(handoff["nextPhase"], "P160")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p159*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P159_EXPLORE_HIGHER_QUALITY_COMPUTATIONAL_OPTICS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Advanced optics research comparison and adoption gate", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("candidate_error is not lower than baseline_error", note)
        self.assertIn("only rank is cited", note)
        self.assertIn("named limit", note)
        self.assertIn("Larger model size alone is not a reason", note)
        self.assertIn("baseline_stable", note)
        self.assertIn("never `qualified` or `allowed`", note)
        self.assertIn("quality-cost tradeoff", note)
        self.assertIn("memory pressure", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p159_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p159_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P159-0{index}")
            self.assertEqual(module.CASE["phase"], "P159")
            self.assertEqual(module.CASE["workstream"], 20)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
