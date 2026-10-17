"""Host checks for P138. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p138_build_the_first_sourced_recipe_family",
    Path(__file__).resolve().parents[1] / "gates" / "p138_build_the_first_sourced_recipe_family.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P138_BUILD_THE_FIRST_SOURCED_RECIPE_FAMILY.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def family_record(result):
    return result["preservedResults"][1]


class P138Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P138")
        self.assertEqual(_MODULE.WORKSTREAM, 18)
        self.assertEqual(_MODULE.TITLE, "Build the first sourced recipe family")
        self.assertEqual(
            _MODULE.GOAL,
            "Demonstrate the database with a small, well-supported set rather than hundreds of names.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Use primary production accounts where available and separate daylight, low-light, monochrome, "
            "and format variants. Record the exact scope of each source. Do not extend a statement about "
            "a whole production into an unsupported claim about every shot.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A production account documenting several stocks used under different shooting conditions.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The database creates separate supported variants and clearly marks any scene-specific reconstruction.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Assign one stock and one lens to every scene because the film title matches.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Initial recipe family with source-to-field traceability")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P137",))
        self.assertEqual(_MODULE.DECLARED_MAXIMUM, 12)
        self.assertIn("{field, source_id}", _MODULE.TRACE_RULE)
        self.assertIn("empty traces", _MODULE.TRACE_RULE)
        self.assertIn("without", _MODULE.TRACE_RULE)
        self.assertIn("null", _MODULE.TRACE_RULE)

    def test_fixture_records_separate_sourced_variants(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        self.assertEqual(source["max_entries"], 12)
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P138")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.TRACE_RULE, " ".join(result["reasons"]))
        record = family_record(result)
        self.assertEqual(record["maximum"], 12)
        self.assertFalse(record["withoutSources"])
        by_id = {entry["recipe_id"]: entry for entry in record["entries"]}
        self.assertEqual(by_id["daylight-5219"]["stock"], "5219")
        self.assertIsNone(by_id["daylight-5219"]["lens"])
        self.assertEqual(by_id["daylight-5219"]["traces"], [{"field": "stock", "source_id": "prod-acct-daylight"}])
        self.assertEqual(by_id["low-light-5219"]["lens"], "Cooke S4 35mm")
        self.assertIsNone(by_id["scene-12"]["stock"])
        self.assertIsNone(by_id["scene-12"]["lens"])
        self.assertEqual(by_id["scene-12"]["traces"], [])
        self.assertTrue(by_id["scene-12"]["reconstruction"])
        self.assertFalse(by_id["scene-12"]["documented"])
        variants = [entry["variant"] for entry in record["entries"]]
        self.assertEqual(variants, ["daylight", "low-light", "monochrome", "format", "scene"])

    def test_title_match_with_empty_traces_is_rejected(self):
        family = [
            _MODULE.make_entry(
                f"scene-{index}",
                stock="5219",
                lens="Cooke S4 35mm",
                traces=[],
                scope="title-match",
                documented=True,
            )
            for index in (1, 2, 3)
        ]
        result = assess(document(family=family))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.TITLE_MATCH, result["rejectedClaims"])
        self.assertIn(_MODULE.UNSOURCED_STOCK, result["rejectedClaims"])
        self.assertIn(_MODULE.UNSOURCED_LENS, result["rejectedClaims"])
        self.assertIn(_MODULE.WHOLE_FILM, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertIn("p138-recipe-family", result["preservedResults"])
        self.assertEqual(family_record(result)["entries"][0]["traces"], [])

    def test_same_stock_and_lens_with_traces_are_recorded(self):
        family = [
            _MODULE.make_entry(
                "day-a",
                stock="5219",
                lens="Cooke S4 35mm",
                traces=[_MODULE.trace("stock", "acct-day"), _MODULE.trace("lens", "acct-day")],
                variant="daylight",
                scope="daylight exteriors",
                documented=True,
            ),
            _MODULE.make_entry(
                "night-b",
                stock="5219",
                lens="Cooke S4 35mm",
                traces=[_MODULE.trace("stock", "acct-night"), _MODULE.trace("lens", "acct-night")],
                variant="low-light",
                scope="night interiors",
                documented=True,
            ),
        ]
        result = assess(document(family=family))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(_MODULE.TITLE_MATCH, result["rejectedClaims"])

    def test_unsourced_stock_alone_is_rejected_and_lens_stays_null(self):
        family = [
            _MODULE.make_entry(
                "partial",
                stock="5219",
                lens=None,
                traces=[],
                variant="daylight",
                scope="daylight exteriors",
                documented=True,
            )
        ]
        result = evaluate({
            "evidenceId": "p138-partial",
            "repeat": "stock",
            "family": family,
            "max_entries": 12,
            "applyMutant": False,
        })
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNSOURCED_STOCK, result["rejectedClaims"])
        self.assertNotIn(_MODULE.TITLE_MATCH, result["rejectedClaims"])
        self.assertIsNone(family_record(result)["entries"][0]["lens"])
        self.assertIn("p138-partial", result["preservedResults"])

    def test_oversized_family_without_sources_is_rejected(self):
        family = [
            _MODULE.make_entry(f"title-only-{index}", scope=f"title only {index}")
            for index in range(13)
        ]
        result = assess(document(family=family, max_entries=100))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OVERSIZE, result["rejectedClaims"])
        self.assertTrue(family_record(result)["withoutSources"])
        self.assertEqual(family_record(result)["maximum"], 12)
        self.assertIsNone(family_record(result)["entries"][0]["stock"])
        self.assertIsNone(family_record(result)["entries"][0]["lens"])

    def test_sourced_family_above_twelve_is_not_a_size_rejection(self):
        family = [
            _MODULE.make_entry(
                f"sourced-{index}",
                stock="5219",
                traces=[_MODULE.trace("stock", f"acct-{index}")],
                variant="daylight",
                scope=f"daylight setup {index}",
                documented=True,
            )
            for index in range(13)
        ]
        result = assess(document(family=family))
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(_MODULE.OVERSIZE, result["rejectedClaims"])
        self.assertEqual(family_record(result)["maximum"], 12)

    def test_tighter_maximum_rejects_an_unsourced_family(self):
        family = [
            _MODULE.make_entry("one", scope="note one"),
            _MODULE.make_entry("two", scope="note two"),
            _MODULE.make_entry("three", scope="note three"),
        ]
        result = assess(document(family=family, max_entries=2))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OVERSIZE, result["rejectedClaims"])
        self.assertEqual(family_record(result)["maximum"], 2)

    def test_invented_unknown_is_rejected_and_published_as_null(self):
        family = [
            _MODULE.make_entry(
                "guessed",
                stock="unknown",
                lens="N/A",
                traces=[_MODULE.trace("stock", "acct"), _MODULE.trace("lens", "acct")],
                variant="daylight",
                scope="daylight exteriors",
                documented=True,
            )
        ]
        result = assess(document(family=family))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.INVENTED, result["rejectedClaims"])
        entry = family_record(result)["entries"][0]
        self.assertIsNone(entry["stock"])
        self.assertIsNone(entry["lens"])

    def test_empty_source_id_raises(self):
        family = [
            _MODULE.make_entry(
                "blank",
                stock="5219",
                traces=[{"field": "stock", "source_id": "  "}],
                variant="daylight",
                scope="daylight exteriors",
                documented=True,
            )
        ]
        with self.assertRaises(ValueError):
            assess(document(family=family))
        with self.assertRaises(ValueError):
            assess(document(evidenceId=""))
        with self.assertRaises(ValueError):
            assess([])
        with self.assertRaises(ValueError):
            evaluate({})

    def test_mutant_flag_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.TITLE_MATCH, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertIn("p138-recipe-family", result["preservedResults"])
        self.assertIn("sourced-recipe-family-host-reference", result["preservedResults"])
        self.assertEqual(family_record(result)["entries"][0]["stock"], "5219")

    def test_trace_for_null_lens_is_rejected(self):
        family = [
            _MODULE.make_entry(
                "dangling",
                stock="5219",
                traces=[
                    _MODULE.trace("stock", "acct"),
                    _MODULE.trace("lens", "acct"),
                ],
                variant="daylight",
                scope="daylight exteriors",
                documented=True,
            )
        ]
        result = assess(document(family=family))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.TRACE_NULL, result["rejectedClaims"])
        self.assertIsNone(family_record(result)["entries"][0]["lens"])

    def test_reconstruction_cannot_invent_a_lens(self):
        family = [
            _MODULE.make_entry(
                "scene-9",
                lens="invented",
                traces=[_MODULE.trace("lens", "user-note")],
                reconstruction=True,
                documented=True,
            )
        ]
        result = assess(document(family=family))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RECON_FACT, result["rejectedClaims"])
        self.assertIn(_MODULE.RECON_DOC, result["rejectedClaims"])
        self.assertIn(_MODULE.INVENTED, result["rejectedClaims"])
        self.assertIsNone(family_record(result)["entries"][0]["lens"])
