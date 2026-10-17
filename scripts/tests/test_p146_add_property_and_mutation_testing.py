"""Host checks for P146. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p146_add_property_and_mutation_testing",
    Path(__file__).resolve().parents[1] / "gates" / "p146_add_property_and_mutation_testing.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P146_ADD_PROPERTY_AND_MUTATION_TESTING.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def catalogue_setting(mutant_id: str, **overrides) -> list:
    catalogue = _MODULE.fixture_catalogue()
    for mutant in catalogue:
        if mutant["id"] == mutant_id:
            mutant.update(overrides)
    return catalogue


class P146Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P146")
        self.assertEqual(_MODULE.WORKSTREAM, 19)
        self.assertEqual(_MODULE.TITLE, "Add property and mutation testing")
        self.assertEqual(
            _MODULE.GOAL,
            "Prove that tests can detect plausible defects rather than merely execute lines.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Generate valid and invalid numeric domains, temporal event sequences, geometry "
            "combinations, and malformed records. Introduce selected mutants such as range "
            "confusion, timestamp reuse, CFA swaps, and missing hash checks. Require critical "
            "mutants to be killed by the intended tests.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A mutation replacing exact timestamp pairing with nearest-neighbor matching.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The metadata association test fails for the deliberately close-but-wrong timestamp fixture.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Run only happy-path examples with conveniently identical metadata.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Property generators and critical mutation catalogue")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P145",))
        self.assertIn("happy-path-only", _MODULE.MUTATION_RULE)
        self.assertIn("expected_detection", _MODULE.MUTATION_RULE)
        self.assertIn("commutative sum", _MODULE.MUTATION_RULE)
        self.assertIn("Identical metadata", _MODULE.MUTATION_RULE)

    def test_fixture_kills_changed_mutants_and_keeps_the_sum(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P146")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.MUTATION_RULE, " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        self.assertEqual(snapshot["commutativeSum"], 10)
        self.assertEqual(snapshot["shuffledSum"], 10)
        self.assertEqual(snapshot["reportedSum"], 10)
        self.assertFalse(snapshot["metadataIdentical"])
        self.assertTrue(snapshot["nearestNeighborKilled"])
        self.assertFalse(snapshot["propertyFailed"])
        self.assertEqual(snapshot["survivedMutants"], [])
        self.assertEqual(
            snapshot["changedFields"]["timestamp-nearest-neighbor"],
            ["metadataTimestampNs", "pairing"],
        )
        self.assertEqual(snapshot["changedFields"]["range-confusion"], ["code", "range"])
        self.assertEqual(snapshot["changedFields"]["cfa-swap"], ["cfa"])
        self.assertEqual(snapshot["changedFields"]["missing-hash"], ["hashChecked"])
        self.assertEqual(snapshot["changedFields"]["timestamp-reuse"], ["timestampNs"])
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_happy_path_catalogue_is_rejected(self):
        result = assess(document(catalogue=_MODULE.happy_path_catalogue()))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.HAPPY_PATH_ONLY, result["rejectedClaims"])
        self.assertIn(_MODULE.NEAREST_NEIGHBOR_NOT_KILLED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.MUTANT_NOT_DETECTED, result["rejectedClaims"])
        self.assertIn("p146-property-mutation", result["preservedResults"])
        self.assertIn("no mutant has a changed field", " ".join(result["reasons"]))
        self.assertTrue(result["preservedResults"][1]["changedFields"])
        self.assertEqual(
            result["preservedResults"][1]["changedFields"]["cfa-swap"],
            [],
        )

    def test_undetected_mutant_is_rejected(self):
        result = assess(document(catalogue=catalogue_setting("cfa-swap", detected=False)))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT_NOT_DETECTED, result["rejectedClaims"])
        self.assertIn("cfa-swap", result["preservedResults"][1]["survivedMutants"])
        self.assertTrue(result["preservedResults"][1]["nearestNeighborKilled"])
        self.assertNotIn(_MODULE.HAPPY_PATH_ONLY, result["rejectedClaims"])
        self.assertIn("p146-property-mutation", result["preservedResults"])

    def test_nearest_neighbor_survivor_fails_the_oracle(self):
        result = assess(
            document(catalogue=catalogue_setting("timestamp-nearest-neighbor", detected=False))
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT_NOT_DETECTED, result["rejectedClaims"])
        self.assertIn(_MODULE.NEAREST_NEIGHBOR_NOT_KILLED, result["rejectedClaims"])
        self.assertIn(_MODULE.ORACLE, result["reasons"])
        self.assertFalse(result["preservedResults"][1]["nearestNeighborKilled"])

    def test_missing_nearest_neighbor_fixture_is_rejected(self):
        catalogue = [
            mutant for mutant in _MODULE.fixture_catalogue() if mutant["id"] != "timestamp-nearest-neighbor"
        ]
        result = assess(document(catalogue=catalogue))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEAREST_NEIGHBOR_NOT_KILLED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.HAPPY_PATH_ONLY, result["rejectedClaims"])

    def test_declared_changed_field_without_original_can_kill_the_fixture(self):
        catalogue = [{
            "id": "timestamp-nearest-neighbor",
            "input": {
                "pairing": "nearest-neighbor",
                "frameTimestampNs": 10,
                "metadataTimestampNs": 12,
            },
            "changedField": "pairing",
            "expected_detection": True,
            "detected": True,
        }]
        result = assess(document(catalogue=catalogue))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["changedFields"]["timestamp-nearest-neighbor"], ["pairing"])

    def test_commutative_sum_failure_rejects_the_implementation_claim(self):
        result = assess(document(reportedSum=1, reportedShuffledSum=4))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.COMMUTATIVE_SUM_FAILED, result["rejectedClaims"])
        self.assertIn(_MODULE.CLAIM, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][1]["propertyFailed"])
        self.assertIn(_MODULE.CLAIM, result["preservedResults"])
        self.assertIn("implementation claim rejected", " ".join(result["reasons"]))
        shifted = assess(document(shuffled=[1, 2, 3, 5], reportedSum=10, reportedShuffledSum=11))
        self.assertEqual(shifted["decision"], "rejected")
        self.assertIn(_MODULE.COMMUTATIVE_SUM_FAILED, shifted["rejectedClaims"])
        self.assertIn(_MODULE.CLAIM, shifted["rejectedClaims"])

    def test_identical_metadata_property_suite_is_rejected(self):
        result = assess(document(propertySuite=_MODULE.identical_property_suite()))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.IDENTICAL_METADATA, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][1]["metadataIdentical"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertNotIn(_MODULE.COMMUTATIVE_SUM_FAILED, result["rejectedClaims"])

    def test_apply_mutant_rejects_identical_metadata_wording(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.IDENTICAL_METADATA, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertIn("p146-property-mutation", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_generators_cover_distinct_domains_and_reject_nonfinite_samples(self):
        generated = _MODULE.property_generators()
        domains = [item["domain"] for item in generated]
        self.assertEqual(domains, ["numeric", "temporal", "geometry", "malformed"])
        self.assertFalse(_MODULE.metadata_identical(_MODULE.fixture_suite()))
        self.assertTrue(_MODULE.metadata_identical(_MODULE.identical_property_suite()))
        self.assertEqual(_MODULE.commutative_sum([4, 1, 3, 2]), _MODULE.commutative_sum([1, 2, 3, 4]))
        with self.assertRaises(ValueError):
            assess(document(samples=[1, float("nan"), 3]))
        with self.assertRaises(ValueError):
            assess(document(samples=[1, float("inf")]))

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P147"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            document(propertySuite=[]),
            document(reportedSum=float("nan")),
            document(catalogue=[{
                "id": "broken",
                "input": {"pairing": "nearest-neighbor"},
                "original": {"pairing": "exact"},
                "expected_detection": "yes",
                "detected": True,
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

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P146-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P146")
        self.assertEqual(handoff["nextPhase"], "P147")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p146*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P146_ADD_PROPERTY_AND_MUTATION_TESTING.md").read_text(encoding="utf-8")
        self.assertIn("Property generators and critical mutation catalogue", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("happy-path", note)
        self.assertIn("commutative sum", note)
        self.assertIn("identical metadata", note)
        self.assertIn("expected_detection", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("never `qualified` or `allowed`", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p146_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p146_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P146-0{index}")
            self.assertEqual(module.CASE["phase"], "P146")
            self.assertEqual(module.CASE["workstream"], 19)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
