"""Host checks for P137. Not a physical S23 probe."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p137_define_the_movie_evidence_schema",
    Path(__file__).resolve().parents[1] / "gates" / "p137_define_the_movie_evidence_schema.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
FIXTURE_COUNTS = {"fact": 7, "reconstruction": 3, "unknown": 2}


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P137_DEFINE_THE_MOVIE_EVIDENCE_SCHEMA.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def detail(result):
    return result["preservedResults"][1]


class P137Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p137-movie-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn(_MODULE.PHYSICAL_NOTE, result["openQuestions"])
        self.assertIn("physical S23", " ".join(result["openQuestions"]))
        self.assertTrue(result["reasons"])
        counts = detail(result)["stateCounts"]
        self.assertEqual(tuple(counts), _MODULE.STATES)

    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P137")
        self.assertEqual(_MODULE.WORKSTREAM, 18)
        self.assertEqual(_MODULE.TITLE, "Define the movie evidence schema")
        self.assertEqual(
            _MODULE.GOAL,
            "Represent production facts, reconstruction choices, and unknowns as different data types.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Store movie, scene family, acquisition format, stock, camera and lens facts, "
            "processing notes, release reference, citations, confidence, and our recipe parameters. "
            "Every documented or contradicted claim needs a source; unknown values remain null rather than guessed.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A film with documented stock choices but no verified lens information for the selected scene.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The recipe can use a clearly reconstructed virtual lens while retaining the "
            "production lens field as unknown.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Fill missing lens fields with plausible cinema equipment and mark them documented.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Movie-claim schema and evidence-state tests")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P007", "P073", "P089", "P121"))
        self.assertEqual(_MODULE.STATES, ("fact", "reconstruction", "unknown"))

    def test_fixture_json_matches_the_gate(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        self.assertEqual(source["implementationBaseRevision"], _MODULE.BASE_REVISION)
        self.assertEqual(source["phase"], "P137")
        self.assertFalse(source["applyMutant"])

    def test_fixture_records_unknown_lens_and_reconstructed_virtual_lens(self):
        source = load_document()
        result = assess(source)
        self.assert_contract(result)
        self.assertEqual(result["caseId"], "P137")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        record = detail(result)
        self.assertEqual(record["stateCounts"], FIXTURE_COUNTS)
        self.assertEqual(record["productionLens"]["state"], "unknown")
        self.assertIsNone(record["productionLens"]["value"])
        self.assertIsNone(record["productionLens"]["source_id"])
        self.assertEqual(record["virtualLens"]["state"], "reconstruction")
        self.assertEqual(record["virtualLens"]["value"], "virtual-spherical-50mm")
        self.assertEqual(record["stock"]["state"], "fact")
        self.assertEqual(record["stock"]["value"], "Eastman 5293")
        self.assertEqual(record["stock"]["source_id"], "src-northwater-stock")
        self.assertIn("stateCounts fact=7 reconstruction=3 unknown=2", result["reasons"])

    def test_documented_lens_guess_is_rejected_and_lens_stays_unknown(self):
        result = assess(document(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GUESSED_LENS_DOCUMENTED, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, " ".join(result["reasons"]))
        record = detail(result)
        self.assertEqual(record["productionLens"]["state"], "unknown")
        self.assertIsNone(record["productionLens"]["value"])
        self.assertEqual(record["productionLens"]["submittedState"], "documented")
        self.assertEqual(record["productionLens"]["submittedValue"], _MODULE.GUESSED_LENS)
        self.assertEqual(record["virtualLens"]["state"], "reconstruction")
        self.assertEqual(record["stateCounts"], FIXTURE_COUNTS)
        self.assertNotIn("documented", record["stateCounts"])

    def test_fact_lens_guess_is_rejected(self):
        record = _MODULE.fixture_record()
        for field in record["fields"]:
            if field["name"] == "lens":
                field.update({
                    "state": "fact",
                    "value": _MODULE.GUESSED_LENS,
                    "source_id": "src-guess",
                    "guessed": True,
                    "priorState": "unknown",
                })
        result = evaluate({
            "caseId": "P137",
            "evidenceId": "p137-guess-fact",
            "claim": "guessed-fact",
            "record": record,
        })
        self.assert_contract(result, "p137-guess-fact")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GUESSED_LENS_FACT, result["rejectedClaims"])
        self.assertEqual(detail(result)["productionLens"]["state"], "unknown")
        self.assertIsNone(detail(result)["productionLens"]["value"])
        self.assertEqual(detail(result)["stateCounts"]["fact"], 7)

    def test_reconstruction_is_not_relabelled_fact(self):
        record = _MODULE.fixture_record()
        for field in record["fields"]:
            if field["name"] == "virtual_lens":
                field.update({
                    "state": "fact",
                    "value": "virtual-spherical-50mm",
                    "source_id": "src-relabel",
                    "priorState": "reconstruction",
                })
        result = evaluate({
            "caseId": "P137",
            "evidenceId": "p137-relabel",
            "claim": "relabel",
            "record": record,
        })
        self.assert_contract(result, "p137-relabel")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RELABELLED_FACT, result["rejectedClaims"])
        virtual = detail(result)["virtualLens"]
        self.assertEqual(virtual["state"], "reconstruction")
        self.assertEqual(virtual["value"], "virtual-spherical-50mm")
        self.assertIsNone(virtual["source_id"])
        self.assertEqual(detail(result)["stateCounts"], FIXTURE_COUNTS)
        self.assertEqual(detail(result)["productionLens"]["state"], "unknown")

    def test_mixed_states_are_rejected_and_counts_remain(self):
        record = _MODULE.fixture_record()
        for field in record["fields"]:
            if field["name"] == "lens":
                field.update({
                    "state": "fact|unknown",
                    "value": _MODULE.GUESSED_LENS,
                    "source_id": "src-guess",
                })
        result = evaluate({
            "caseId": "P137",
            "evidenceId": "p137-mixed",
            "claim": "mixed",
            "record": record,
        })
        self.assert_contract(result, "p137-mixed")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MIXED_STATE, result["rejectedClaims"])
        self.assertIsNone(detail(result)["productionLens"]["state"])
        self.assertEqual(detail(result)["stateCounts"]["fact"], 7)
        self.assertEqual(detail(result)["stateCounts"]["reconstruction"], 3)
        self.assertEqual(detail(result)["stateCounts"]["unknown"], 1)
        self.assertEqual(tuple(detail(result)["stateCounts"]), ("fact", "reconstruction", "unknown"))

    def test_labelled_reconstruction_lens_is_not_a_fact(self):
        record = _MODULE.fixture_record()
        for field in record["fields"]:
            if field["name"] == "lens":
                field.update({
                    "state": "reconstruction",
                    "value": "virtual-spherical-50mm",
                    "source_id": None,
                })
        result = evaluate({
            "caseId": "P137",
            "evidenceId": "p137-labelled",
            "claim": "labelled-reconstruction",
            "record": record,
        })
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(detail(result)["productionLens"]["state"], "reconstruction")
        self.assertNotIn(_MODULE.GUESSED_LENS_FACT, result["rejectedClaims"])

    def test_verified_sourced_lens_can_be_fact(self):
        record = _MODULE.fixture_record()
        record["lensVerified"] = True
        for field in record["fields"]:
            if field["name"] == "lens":
                field.update({
                    "state": "fact",
                    "value": "Cooke S4/i 50mm",
                    "source_id": "src-northwater-lens",
                })
        result = evaluate({
            "caseId": "P137",
            "evidenceId": "p137-verified-lens",
            "claim": "verified-lens",
            "record": record,
        })
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(detail(result)["productionLens"]["state"], "fact")
        self.assertEqual(detail(result)["productionLens"]["source_id"], "src-northwater-lens")
        self.assertEqual(detail(result)["stateCounts"]["fact"], 8)
        self.assertEqual(detail(result)["stateCounts"]["unknown"], 1)

    def test_unknown_value_and_fact_without_source_raise(self):
        unknown = _MODULE.fixture_record()
        for field in unknown["fields"]:
            if field["name"] == "lens":
                field["value"] = _MODULE.GUESSED_LENS
        with self.assertRaises(ValueError):
            evaluate({
                "caseId": "P137",
                "evidenceId": "p137-bad-unknown",
                "claim": "bad",
                "record": unknown,
            })
        missing_source = _MODULE.fixture_record()
        for field in missing_source["fields"]:
            if field["name"] == "stock":
                field["source_id"] = None
        with self.assertRaises(ValueError):
            assess(document(record=missing_source))

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            assess(document(phase="P138"))
        with self.assertRaises(ValueError):
            evaluate({
                "caseId": "P137",
                "evidenceId": "p137",
                "claim": "bad",
                "record": _MODULE.fixture_record(),
                "decision": "qualified",
            })

    def test_duplicate_conflicting_states_are_mixed(self):
        record = _MODULE.fixture_record()
        record["fields"].append(_MODULE.make_field("lens", "fact", _MODULE.GUESSED_LENS, "src-guess"))
        result = evaluate({
            "caseId": "P137",
            "evidenceId": "p137-duplicate",
            "claim": "duplicate",
            "record": record,
        })
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MIXED_STATE, result["rejectedClaims"])
        self.assertIn("p137-duplicate", result["preservedResults"])
        self.assertEqual(tuple(detail(result)["stateCounts"]), _MODULE.STATES)
        copy.deepcopy(result)
