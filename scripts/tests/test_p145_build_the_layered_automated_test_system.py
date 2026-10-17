"""Host checks for P145. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p145_build_the_layered_automated_test_system",
    Path(__file__).resolve().parents[1] / "gates" / "p145_build_the_layered_automated_test_system.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P145_BUILD_THE_LAYERED_AUTOMATED_TEST_SYSTEM.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def summary_of(result):
    return result["preservedResults"][1]


class P145Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P145")
        self.assertEqual(_MODULE.WORKSTREAM, 19)
        self.assertEqual(_MODULE.TITLE, "Build the layered automated test system")
        self.assertEqual(
            _MODULE.GOAL,
            "Separate host arithmetic, JVM policies, Android integration, GPU parity, and physical acceptance.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Run fast deterministic contracts on every change, then focused integration suites and "
            "scheduled device experiments. Preserve failing evidence and classify unavailable hardware "
            "explicitly. Tests must call production interfaces or declared independent references, not "
            "duplicate trivial implementations.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A green host suite alongside an unavailable physical ten-bit codec test and a failing GPU color test.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The report keeps the GPU failure and unavailable device gate visible and does not declare "
            "the release fully qualified.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Count skipped hardware tests as passing tests in the release summary.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Layered CI plan and machine-readable evidence aggregation")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P004", "P032", "P064", "P128", "P136", "P144"))
        self.assertEqual(_MODULE.LAYERS, ("host", "jvm", "android", "gpu", "physical"))

    def test_fixture_records_each_layer_without_qualifying(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P145")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn("gpu failure visible: gpu-color", result["reasons"])
        self.assertIn("unavailable device gate visible: physical-ten-bit-codec", result["reasons"])
        summary = summary_of(result)
        self.assertEqual(set(summary["layers"]), set(_MODULE.LAYERS))
        self.assertEqual(summary["layers"]["gpu"]["failedIds"], ["gpu-color"])
        self.assertEqual(summary["layers"]["gpu"]["status"], "failed")
        self.assertEqual(summary["layers"]["physical"]["status"], "unavailable")
        self.assertEqual(summary["layers"]["physical"]["passed"], 0)
        self.assertEqual(summary["layers"]["physical"]["skippedIds"], ["physical-ten-bit-codec"])
        self.assertEqual(summary["layers"]["host"]["passed"], 2)
        self.assertFalse(summary["qualified"])
        self.assertFalse(summary["skippedIncludedInPassed"])

    def test_total_passed_is_the_sum_of_passed_and_excludes_skipped(self):
        result = assess(document())
        summary = summary_of(result)
        passed_sum = sum(summary["layers"][name]["passed"] for name in _MODULE.LAYERS)
        skipped_sum = sum(summary["layers"][name]["skipped"] for name in _MODULE.LAYERS)
        self.assertEqual(summary["totalPassed"], passed_sum)
        self.assertEqual(summary["totalPassed"], 5)
        self.assertEqual(summary["totalFailed"], 1)
        self.assertEqual(skipped_sum, 1)
        self.assertEqual(summary["totalSkipped"], 1)
        self.assertEqual(summary["releasePassed"], 5)
        self.assertNotEqual(summary["totalPassed"], passed_sum + skipped_sum)
        self.assertIn("total passed 5 excludes skipped 1", result["reasons"])

    def test_evaluate_matches_the_fixture_counts(self):
        source = _MODULE.fixture_document()
        result = evaluate({
            "evidenceId": source["evidenceId"],
            "repeat": "fixture",
            "claim": source["claim"],
            "applyMutant": False,
            "declaresQualified": False,
            "layers": source["layers"],
            "releasePassed": source["releasePassed"],
            "releaseSummary": source["releaseSummary"],
        })
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "P145")
        self.assertEqual(summary_of(result)["totalPassed"], 5)
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_release_passed_that_includes_skipped_is_rejected(self):
        result = assess(document(releasePassed=6))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RELEASE_PASSED_INCLUDES_SKIPPED, result["rejectedClaims"])
        self.assertIn("p145-layered-ci", result["preservedResults"])
        self.assertEqual(summary_of(result)["totalPassed"], 5)
        self.assertEqual(summary_of(result)["releasePassed"], 5)
        self.assertEqual(summary_of(result)["callerReleasePassed"], 6)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_skipped_added_into_passed_is_rejected(self):
        layers = _MODULE.fixture_layers()
        layers["physical"] = {
            "tests": [{"id": "physical-ten-bit-codec", "outcome": "skipped"}],
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        }
        source = document(layers=layers)
        result = assess(source)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SKIPPED_ADDED_INTO_PASSED, result["rejectedClaims"])
        physical = summary_of(result)["layers"]["physical"]
        self.assertEqual(physical["passed"], 0)
        self.assertEqual(physical["skipped"], 1)
        self.assertEqual(summary_of(result)["totalPassed"], 5)

    def test_unavailable_hardware_marked_passed_is_rejected(self):
        layers = _MODULE.fixture_layers()
        layers["physical"] = [{"id": "physical-ten-bit-codec", "outcome": "passed", "unavailable": True}]
        fields = _MODULE.layer_fields(layers)
        result = assess(document(**fields))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SKIPPED_ADDED_INTO_PASSED, result["rejectedClaims"])
        self.assertEqual(summary_of(result)["layers"]["physical"]["skipped"], 1)
        self.assertEqual(summary_of(result)["layers"]["physical"]["passed"], 0)
        self.assertEqual(summary_of(result)["totalPassed"], 5)

    def test_missing_physical_layer_is_not_run_not_passed(self):
        layers = _MODULE.fixture_layers()
        del layers["physical"]
        fields = _MODULE.layer_fields(layers)
        self.assertEqual(fields["releaseSummary"]["physical"]["status"], "not-run")
        self.assertEqual(fields["releaseSummary"]["physical"]["passed"], 0)
        self.assertEqual(fields["releasePassed"], 5)
        result = assess(document(**fields))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(summary_of(result)["layers"]["physical"]["status"], "not-run")
        self.assertNotEqual(summary_of(result)["layers"]["physical"]["status"], "passed")
        self.assertIn("physical layer not run", result["reasons"])
        self.assertIn("unavailable device gate visible: physical not-run", result["reasons"])
        self.assertEqual(set(summary_of(result)["layers"]), set(_MODULE.LAYERS))

    def test_counting_missing_physical_as_passed_is_rejected(self):
        layers = _MODULE.fixture_layers()
        del layers["physical"]
        fields = _MODULE.layer_fields(layers)
        fields["releaseSummary"]["physical"]["status"] = "passed"
        fields["releaseSummary"]["physical"]["passed"] = 1
        fields["releasePassed"] = 6
        result = assess(document(**fields))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_PHYSICAL_COUNTED_AS_PASSED, result["rejectedClaims"])
        self.assertEqual(summary_of(result)["layers"]["physical"]["status"], "not-run")
        self.assertEqual(summary_of(result)["layers"]["physical"]["passed"], 0)
        self.assertEqual(summary_of(result)["totalPassed"], 5)

    def test_release_summary_must_list_each_layer(self):
        source = document()
        del source["releaseSummary"]["physical"]
        hidden = assess(source)
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn(_MODULE.RELEASE_SUMMARY_MISSING_LAYER, hidden["rejectedClaims"])
        self.assertEqual(set(summary_of(hidden)["layers"]), set(_MODULE.LAYERS))
        collapsed = document(releaseSummary={"passed": 6, "failed": 0, "skipped": 0})
        collapsed_result = assess(collapsed)
        self.assertEqual(collapsed_result["decision"], "rejected")
        self.assertIn(_MODULE.RELEASE_SUMMARY_NOT_LAYERED, collapsed_result["rejectedClaims"])
        self.assertIn("gpu-color", summary_of(collapsed_result)["layers"]["gpu"]["failedIds"])

    def test_hiding_the_gpu_failure_is_rejected(self):
        source = document()
        source["releaseSummary"]["gpu"] = {
            "passed": 2,
            "failed": 0,
            "skipped": 0,
            "status": "passed",
        }
        result = assess(source)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GPU_FAILURE_HIDDEN, result["rejectedClaims"])
        self.assertIn("gpu-color", summary_of(result)["layers"]["gpu"]["failedIds"])

    def test_mutant_flag_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.COUNT_SKIPPED_HARDWARE_AS_PASSING, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, " ".join(result["reasons"]))
        self.assertIn("p145-layered-ci", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_all_green_layers_are_still_not_qualified(self):
        layers = {name: [{"id": name + "-ok", "outcome": "passed"}] for name in _MODULE.LAYERS}
        fields = _MODULE.layer_fields(layers)
        result = assess(document(**fields))
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(summary_of(result)["qualified"])
        self.assertEqual(summary_of(result)["totalPassed"], 5)
        self.assertEqual(summary_of(result)["totalSkipped"], 0)
        self.assertIn("physical S23 not run", result["openQuestions"])
        qualified = assess(document(**fields, declaresQualified=True))
        self.assertEqual(qualified["decision"], "rejected")
        self.assertIn(_MODULE.RELEASE_FULLY_QUALIFIED, qualified["rejectedClaims"])
        self.assertNotEqual(qualified["decision"], "qualified")
        self.assertFalse(summary_of(qualified)["qualified"])

    def test_host_skip_is_not_a_pass_either(self):
        layers = {
            "host": [
                {"id": "host-ok", "outcome": "passed"},
                {"id": "host-skip", "outcome": "skipped"},
            ],
            "jvm": [{"id": "jvm-ok", "outcome": "failed"}],
            "android": [],
            "gpu": [{"id": "gpu-skip", "outcome": "skipped"}],
        }
        fields = _MODULE.layer_fields(layers)
        self.assertEqual(fields["releasePassed"], 1)
        self.assertEqual(fields["releaseSummary"]["physical"]["status"], "not-run")
        self.assertEqual(fields["releaseSummary"]["gpu"]["status"], "unavailable")
        result = assess(document(**fields))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(summary_of(result)["totalPassed"], 1)
        self.assertEqual(summary_of(result)["totalSkipped"], 2)
        self.assertNotEqual(summary_of(result)["totalPassed"], 3)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess([])
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            assess(document(phase="P144"))
        with self.assertRaises(ValueError):
            assess(document(implementationBaseRevision="0" * 40))
        with self.assertRaises(ValueError):
            assess(document(releasePassed=True))
        layers = _MODULE.fixture_layers()
        layers["gpu"][0]["outcome"] = "skip"
        with self.assertRaises(ValueError):
            assess(document(**_MODULE.layer_fields(layers)))
        with self.assertRaises(ValueError):
            assess(document(layers={"cloud": []}))
        with self.assertRaises(ValueError):
            assess(document(declaresQualified="yes"))
