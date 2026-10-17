"""Host checks for P134. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p134_design_transparent_progress_and_failure_states",
    Path(__file__).resolve().parents[1]
    / "gates"
    / "p134_design_transparent_progress_and_failure_states.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (
            _ROOT / "docs" / "P134_DESIGN_TRANSPARENT_PROGRESS_AND_FAILURE_STATES.json"
        ).read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def with_progress(**overrides):
    value = document()
    progress = _MODULE.fixture_progress(**overrides)
    value["progress"] = progress
    return value


def light(**overrides):
    progress = overrides.pop("progress", None)
    payload = {
        "evidenceId": "p134-eval",
        "repeat": "encoder drain",
        "progress": _MODULE.fixture_progress() if progress is None else progress,
    }
    if progress is None and overrides:
        payload["progress"] = _MODULE.fixture_progress(**overrides)
    return payload


def reading_of(result):
    return result["preservedResults"][1]


class P134Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p134-progress-failure"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P134")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn(_MODULE.RULE, result["reasons"])
        self.assertTrue(result["reasons"])

    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P134")
        self.assertEqual(_MODULE.WORKSTREAM, 17)
        self.assertEqual(_MODULE.TITLE, "Design transparent progress and failure states")
        self.assertEqual(
            _MODULE.GOAL,
            "Tell users what is happening without fabricated percentages or vague success banners.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Progress should identify capture, inference, rendering, verification, or publication. "
            "Use indeterminate states when remaining work is unknown. Errors distinguish unsupported "
            "mode, unavailable model, source corruption, output failure, and retained recoverable footage.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A render reaches its final frame but still requires full decode verification and "
            "gallery publication.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The UI does not show completed until acceptance and publication policy are satisfied.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Show one hundred percent success immediately after the last frame is submitted to the encoder.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Progress semantics and failure-state screenshots/tests")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P133",))

    def test_progress_reading_is_indeterminate_or_the_frame_ratio(self):
        unknown = _MODULE.progress_reading(0, 0, False)
        self.assertEqual(unknown["state"], "indeterminate")
        self.assertIsNone(unknown["fraction"])
        self.assertFalse(unknown["allows_one"])
        self.assertIsNone(_MODULE.progress_reading(0, 0, True)["fraction"])

        partial = _MODULE.progress_reading(3, 12, False)
        self.assertEqual(partial["state"], "fraction")
        self.assertEqual(partial["fraction"], 3 / 12)
        self.assertNotEqual(partial["fraction"], 1.0)
        self.assertFalse(partial["allows_one"])

        withheld = _MODULE.progress_reading(12, 12, False)
        self.assertEqual(withheld["state"], "indeterminate")
        self.assertIsNone(withheld["fraction"])
        self.assertTrue(withheld["every_frame_accounted"])
        self.assertFalse(withheld["drain_complete"])
        self.assertNotEqual(withheld["fraction"], 1.0)

        done = _MODULE.progress_reading(12, 12, True)
        self.assertEqual(done["fraction"], 1.0)
        self.assertTrue(done["allows_one"])
        self.assertEqual(_MODULE.spoken_progress(withheld), "indeterminate")
        self.assertEqual(_MODULE.spoken_progress(partial), "0.25")

    def test_fixture_withholds_completion_after_the_final_frame(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn("ratio withheld", " ".join(result["reasons"]))
        record = reading_of(result)
        self.assertEqual(record["state"], "indeterminate")
        self.assertIsNone(record["fraction"])
        self.assertNotEqual(record["fraction"], 1.0)
        self.assertEqual(record["accounted_frames"], 12)
        self.assertEqual(record["expected_frames"], 12)
        self.assertFalse(record["drain_complete"])
        self.assertIsNone(record["displayed_percent"])
        self.assertIsNone(record["success"])
        self.assertFalse(record["acceptance_satisfied"])
        self.assertEqual(record["stage"], "verification")

    def test_partial_ratio_is_recorded_and_is_not_one(self):
        result = assess(with_progress(
            stage="rendering",
            accounted_frames=3,
            expected_frames=12,
            drain_complete=False,
            displayed_percent=25,
        ))
        self.assertEqual(result["decision"], "recorded")
        record = reading_of(result)
        self.assertEqual(record["state"], "fraction")
        self.assertEqual(record["fraction"], 0.25)
        self.assertFalse(record["allows_one"])
        self.assertNotEqual(record["fraction"], 1.0)

    def test_hundred_percent_before_drain_is_rejected(self):
        result = assess(with_progress(displayed_percent=100, success=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HUNDRED_BEFORE_DRAIN, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.PREMATURE_COMPLETE, result["rejectedClaims"])
        self.assertIn("showing 100 percent when drain_complete is false is rejected", result["reasons"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertIsNone(reading_of(result)["fraction"])
        self.assertNotEqual(reading_of(result)["fraction"], 1.0)
        self.assertIn("p134-progress-failure", result["preservedResults"])

    def test_zero_expected_frames_stays_indeterminate(self):
        quiet = assess(with_progress(
            stage="capture",
            accounted_frames=0,
            expected_frames=0,
            drain_complete=False,
            displayed_percent=None,
        ))
        self.assertEqual(quiet["decision"], "recorded")
        self.assertEqual(reading_of(quiet)["state"], "indeterminate")
        self.assertIsNone(reading_of(quiet)["fraction"])
        self.assertIn("expected_frames is 0; progress is indeterminate", quiet["reasons"])
        invented = assess(with_progress(
            stage="capture",
            accounted_frames=0,
            expected_frames=0,
            displayed_percent=0,
        ))
        self.assertEqual(invented["decision"], "rejected")
        self.assertIn(_MODULE.INVENTED_ZERO, invented["rejectedClaims"])
        self.assertIsNone(reading_of(invented)["fraction"])

    def test_failure_requires_a_reason_and_success_false(self):
        honest = assess(with_progress(
            stage="rendering",
            accounted_frames=3,
            expected_frames=12,
            displayed_percent=25,
            success=False,
            failure_reason="encoder output failed",
            failure_kind="output-failure",
        ))
        self.assertEqual(honest["decision"], "recorded")
        self.assertEqual(reading_of(honest)["success"], False)
        self.assertEqual(reading_of(honest)["failure_reason"], "encoder output failed")
        self.assertIn("failure success=false reason=encoder output failed", honest["reasons"])
        for progress in (
            _MODULE.fixture_progress(success=False, failure_reason=None, failure_kind="output-failure"),
            _MODULE.fixture_progress(success=False, failure_reason="encoder output failed", failure_kind=None),
            _MODULE.fixture_progress(success=False, failure_reason="  ", failure_kind="output-failure"),
        ):
            with self.assertRaises(ValueError) as caught:
                assess(document(progress=progress))
            self.assertIn("a failure must include a non-empty reason and success false", str(caught.exception))

    def test_success_banner_with_a_failure_reason_is_rejected(self):
        result = assess(with_progress(
            stage="publication",
            drain_complete=True,
            displayed_percent=100,
            success=True,
            failure_reason="source file is corrupt",
            failure_kind="source-corruption",
            verification_complete=True,
            publication_complete=True,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.SUCCESS_WITH_REASON, result["rejectedClaims"])
        self.assertIn("a success banner with a failure reason is rejected", result["reasons"])
        self.assertEqual(reading_of(result)["fraction"], 1.0)
        self.assertIn("p134-progress-failure", result["preservedResults"])

    def test_completion_waits_for_verification_and_publication(self):
        early = assess(with_progress(
            stage="publication",
            drain_complete=True,
            displayed_percent=100,
            success=True,
            verification_complete=False,
            publication_complete=False,
        ))
        self.assertEqual(early["decision"], "rejected")
        self.assertIn(_MODULE.PREMATURE_COMPLETE, early["rejectedClaims"])
        self.assertEqual(reading_of(early)["fraction"], 1.0)
        self.assertFalse(reading_of(early)["acceptance_satisfied"])
        done = assess(with_progress(
            stage="publication",
            drain_complete=True,
            displayed_percent=100,
            success=True,
            verification_complete=True,
            publication_complete=True,
        ))
        self.assertEqual(done["decision"], "recorded")
        self.assertNotIn(done["decision"], {"qualified", "allowed"})
        self.assertEqual(done["rejectedClaims"], [])
        self.assertTrue(reading_of(done)["acceptance_satisfied"])
        self.assertEqual(reading_of(done)["fraction"], 1.0)

    def test_mutant_flag_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertIn("p134-progress-failure", result["preservedResults"])
        self.assertIsNone(reading_of(result)["fraction"])

    def test_dropped_recoverable_footage_is_rejected(self):
        result = assess(with_progress(
            success=False,
            failure_reason="thermal warning; footage retained",
            failure_kind="retained-recoverable-footage",
            footage_retained=False,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FOOTAGE_DROPPED, result["rejectedClaims"])

    def test_evaluate_uses_the_same_contract(self):
        result = evaluate(light())
        self.assert_contract(result, "p134-eval")
        self.assertEqual(result["decision"], "recorded")
        self.assertIsNone(reading_of(result)["fraction"])
        rejected = evaluate(light(
            displayed_percent=100,
            success=True,
        ))
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn(_MODULE.HUNDRED_BEFORE_DRAIN, rejected["rejectedClaims"])
        self.assertIn("p134-eval", rejected["preservedResults"])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P135"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            with_progress(accounted_frames=13),
            with_progress(accounted_frames=1, expected_frames=0),
            with_progress(stage="done"),
            with_progress(displayed_percent=101),
            with_progress(failure_kind="qualified"),
            with_progress(success="yes"),
            with_progress(drain_complete="false"),
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    assess(payload)
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            _MODULE.progress_reading(True, 4, False)
        with self.assertRaises(ValueError):
            _MODULE.progress_reading(-1, 4, False)

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P134-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P134")
        self.assertEqual(handoff["nextPhase"], "P135")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p134*.py' -v",
        )
        note = (_ROOT / "docs" / "P134_DESIGN_TRANSPARENT_PROGRESS_AND_FAILURE_STATES.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Progress semantics and failure-state screenshots/tests", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("accounted_frames/expected_frames", note)
        self.assertIn("drain_complete", note)
        self.assertIn("indeterminate", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p134_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p134_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P134-0{index}")
            self.assertEqual(module.CASE["phase"], "P134")
            self.assertEqual(module.CASE["workstream"], 17)
            with self.assertRaises(ValueError):
                module.evaluate({})
