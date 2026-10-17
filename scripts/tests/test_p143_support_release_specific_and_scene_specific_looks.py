"""Host checks for P143. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p143_support_release_specific_and_scene_specific_looks",
    Path(__file__).resolve().parents[1]
    / "gates"
    / "p143_support_release_specific_and_scene_specific_looks.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (
            _ROOT / "docs" / "P143_SUPPORT_RELEASE_SPECIFIC_AND_SCENE_SPECIFIC_LOOKS.json"
        ).read_text(encoding="utf-8")
    )


def catalogue(result):
    return result["preservedResults"][1]


def contrasts(result):
    return {
        entry["release_id"]: entry["parameters"]["contrast"]
        for entry in catalogue(result)["entries"]
        if entry["scene_id"] is None
    }


class P143Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p143-release-looks"):
        self.assertEqual(tuple(result), KEYS)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))

    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P143")
        self.assertEqual(_MODULE.WORKSTREAM, 18)
        self.assertEqual(_MODULE.TITLE, "Support release-specific and scene-specific looks")
        self.assertEqual(
            _MODULE.GOAL,
            "Avoid treating every distribution version of a film as one fixed color target.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Record reference edition, format, display assumptions, and scene family when known. "
            "Permit several interpretations under one movie title. A missing edition remains unknown; "
            "the app must not infer a theatrical print response from an arbitrary screenshot.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "Two legally obtained references from different releases with visibly different "
            "contrast and color treatment.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The database preserves separate recipe targets and identifies which reference supports each.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Average all references into one supposedly definitive movie look.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Release-aware catalogue and ambiguity tests")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P142",))

    def test_fixture_keeps_two_releases_distinct(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assert_contract(result)
        self.assertEqual(result["caseId"], "P143")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = catalogue(result)
        self.assertEqual(
            record["acceptedKeys"],
            [
                "reference-film|digital-sdr|",
                "reference-film|theatrical-35mm|",
            ],
        )
        self.assertEqual(record["distinctReleaseIds"]["reference-film"], ["digital-sdr", "theatrical-35mm"])
        self.assertEqual(contrasts(result), {"digital-sdr": 0.5, "theatrical-35mm": 1.5})
        self.assertNotIn(1.0, contrasts(result).values())
        self.assertIn(
            "two releases of the same film remain distinct entries for reference-film: digital-sdr, theatrical-35mm",
            result["reasons"],
        )
        by_key = {entry["key"]: entry for entry in record["entries"]}
        self.assertEqual(by_key["reference-film|theatrical-35mm|"]["reference_id"], "owned-theatrical-reference")
        self.assertEqual(by_key["reference-film|digital-sdr|"]["reference_id"], "owned-digital-reference")
        self.assertEqual(by_key["reference-film|theatrical-35mm|"]["parameters"]["red"], 1.25)
        self.assertEqual(by_key["reference-film|digital-sdr|"]["parameters"]["blue"], 1.25)

    def test_evaluate_matches_assess_for_the_document(self):
        result = evaluate(_MODULE.fixture_document())
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "P143")
        self.assertEqual(catalogue(result)["acceptedKeys"], catalogue(assess(_MODULE.fixture_document()))["acceptedKeys"])

    def test_minimal_evaluate_keeps_releases_distinct(self):
        result = evaluate({
            "evidenceId": "p143-minimal",
            "caseId": "P143",
            "looks": [
                {"film_id": "reference-film", "release_id": "theatrical", "parameters": {"contrast": 1.5}},
                {"film_id": "reference-film", "release_id": "digital", "parameters": {"contrast": 0.5}},
            ],
        })
        self.assert_contract(result, "p143-minimal")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(
            catalogue(result)["distinctReleaseIds"]["reference-film"],
            ["digital", "theatrical"],
        )
        self.assertEqual(len(catalogue(result)["entries"]), 2)

    def test_averaged_true_is_rejected(self):
        looks = _MODULE.fixture_looks()
        looks.append(_MODULE.make_look(
            release_id="all",
            reference_id="averaged-reference",
            averaged=True,
            definitive=True,
            parameters={"contrast": 1.0, "red": 1.0, "green": 0.875, "blue": 0.875},
        ))
        result = assess(_MODULE.copy_document(looks=looks))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.AVERAGED_LOOK, result["rejectedClaims"])
        self.assertIn(_MODULE.RELEASE_ID_ALL, result["rejectedClaims"])
        self.assertIn(_MODULE.DEFINITIVE_LOOK, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertNotIn("reference-film|all|", catalogue(result)["acceptedKeys"])
        self.assertEqual(contrasts(result)["theatrical-35mm"], 1.5)
        self.assertEqual(contrasts(result)["digital-sdr"], 0.5)

    def test_release_id_all_without_the_averaged_flag_is_rejected(self):
        result = evaluate({
            "evidenceId": "p143-all",
            "looks": [
                {"film_id": "reference-film", "release_id": "ALL", "averaged": False, "parameters": {"contrast": 1}},
            ],
        })
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RELEASE_ID_ALL, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertEqual(catalogue(result)["acceptedKeys"], [])
        self.assertEqual(catalogue(result)["submitted"][0]["release_id"], "ALL")

    def test_missing_release_id_is_rejected(self):
        result = evaluate({
            "evidenceId": "p143-missing-release",
            "looks": [{"film_id": "reference-film", "parameters": {"contrast": 1}}],
        })
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_RELEASE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn("p143-missing-release", result["preservedResults"])
        self.assertIsNone(catalogue(result)["submitted"][0]["release_id"])

    def test_ambiguous_release_stays_listed(self):
        looks = _MODULE.fixture_looks() + [_MODULE.unidentified_look()]
        result = assess(_MODULE.copy_document(looks=looks))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = catalogue(result)
        self.assertIn("unidentified", record["distinctReleaseIds"]["reference-film"])
        self.assertEqual(record["ambiguousReleaseIds"]["reference-film"], ["unidentified"])
        self.assertIn("reference-film|unidentified|", record["acceptedKeys"])
        unidentified = next(entry for entry in record["entries"] if entry["release_id"] == "unidentified")
        self.assertEqual(unidentified["edition"], "unknown")
        self.assertTrue(unidentified["ambiguous"])
        self.assertIn("ambiguous releases stay listed: reference-film:unidentified", result["reasons"])

    def test_dropping_ambiguous_releases_is_rejected_and_they_remain(self):
        looks = _MODULE.fixture_looks() + [_MODULE.unidentified_look()]
        result = assess(_MODULE.copy_document(looks=looks, dropAmbiguous=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.AMBIGUOUS_DROPPED, result["rejectedClaims"])
        self.assertIn("reference-film|unidentified|", catalogue(result)["acceptedKeys"])
        self.assertEqual(len(catalogue(result)["distinctReleaseIds"]["reference-film"]), 3)

    def test_scene_look_names_its_release_and_does_not_replace_it(self):
        looks = _MODULE.fixture_looks() + [_MODULE.scene_look()]
        result = assess(_MODULE.copy_document(looks=looks))
        self.assertEqual(result["decision"], "recorded")
        record = catalogue(result)
        self.assertIn("reference-film|theatrical-35mm|", record["acceptedKeys"])
        self.assertIn("reference-film|theatrical-35mm|night-interior", record["acceptedKeys"])
        by_key = {entry["key"]: entry for entry in record["entries"]}
        self.assertEqual(by_key["reference-film|theatrical-35mm|"]["scope"], "release")
        self.assertEqual(by_key["reference-film|theatrical-35mm|"]["parameters"]["contrast"], 1.5)
        self.assertEqual(by_key["reference-film|theatrical-35mm|night-interior"]["scope"], "scene")
        self.assertEqual(by_key["reference-film|theatrical-35mm|night-interior"]["parameters"]["contrast"], 1.75)
        self.assertIn("digital-sdr", record["distinctReleaseIds"]["reference-film"])
        self.assertIn(
            "scene look night-interior names release theatrical-35mm and does not replace the release-level look",
            result["reasons"],
        )

    def test_scene_look_without_a_release_level_entry_is_rejected(self):
        result = evaluate({
            "evidenceId": "p143-scene-only",
            "looks": [_MODULE.scene_look()],
        })
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SCENE_REPLACES_RELEASE, result["rejectedClaims"])
        self.assertIn("reference-film|theatrical-35mm|night-interior", catalogue(result)["acceptedKeys"])
        self.assertNotIn("reference-film|theatrical-35mm|", catalogue(result)["acceptedKeys"])

    def test_scene_look_missing_release_id_is_rejected(self):
        result = evaluate({
            "evidenceId": "p143-scene-missing",
            "looks": [_MODULE.scene_look(release_id=None)],
        })
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_RELEASE, result["rejectedClaims"])
        self.assertIn(_MODULE.SCENE_MISSING_RELEASE, result["rejectedClaims"])
        self.assertEqual(catalogue(result)["acceptedKeys"], [])

    def test_scene_flag_that_replaces_the_release_look_is_rejected(self):
        looks = _MODULE.fixture_looks() + [_MODULE.scene_look(replaces_release_look=True)]
        result = assess(_MODULE.copy_document(looks=looks))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SCENE_REPLACES_RELEASE, result["rejectedClaims"])
        self.assertIn("reference-film|theatrical-35mm|", catalogue(result)["acceptedKeys"])
        self.assertEqual(contrasts(result)["theatrical-35mm"], 1.5)

    def test_screenshot_inference_stays_unknown(self):
        inferred = _MODULE.make_look(inferred_from_screenshot=True, edition="theatrical-print")
        result = assess(_MODULE.copy_document(looks=[inferred, _MODULE.digital_look()]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SCREENSHOT_INFERENCE, result["rejectedClaims"])
        theatrical = next(entry for entry in catalogue(result)["entries"] if entry["release_id"] == "theatrical-35mm")
        self.assertEqual(theatrical["edition"], "unknown")
        self.assertEqual(theatrical["format"], "unknown")
        self.assertEqual(theatrical["display_assumptions"], "unknown")

    def test_concealing_an_ambiguous_release_is_rejected_and_it_stays_listed(self):
        hidden = _MODULE.unidentified_look(ambiguous=False)
        result = assess(_MODULE.copy_document(looks=[_MODULE.make_look(), hidden]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.AMBIGUITY_CONCEALED, result["rejectedClaims"])
        self.assertIn("unidentified", catalogue(result)["ambiguousReleaseIds"]["reference-film"])

    def test_conflicting_parameters_are_not_averaged(self):
        first = _MODULE.make_look(reference_id="ref-a", parameters={"contrast": 1.5})
        second = _MODULE.make_look(reference_id="ref-b", parameters={"contrast": 0.5})
        result = assess(_MODULE.copy_document(looks=[first, second, _MODULE.digital_look()]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CONFLICTING_PARAMS, result["rejectedClaims"])
        self.assertNotIn("reference-film|theatrical-35mm|", catalogue(result)["acceptedKeys"])
        self.assertIn("reference-film|digital-sdr|", catalogue(result)["acceptedKeys"])
        conflict = catalogue(result)["conflicts"][0]
        self.assertEqual([item["contrast"] for item in conflict["parameterSets"]], [1.5, 0.5])
        self.assertNotIn(1.0, [item["contrast"] for item in conflict["parameterSets"]])

    def test_collapsed_release_ids_are_rejected(self):
        collapsed = _MODULE.make_look(
            release_id="combined",
            collapsed_release_ids=["theatrical-35mm", "digital-sdr"],
            parameters={"contrast": 1.0},
        )
        result = assess(_MODULE.copy_document(looks=[collapsed]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RELEASES_COLLAPSED, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertEqual(catalogue(result)["acceptedKeys"], [])
        self.assertEqual(
            catalogue(result)["submitted"][0]["collapsed_release_ids"],
            ["theatrical-35mm", "digital-sdr"],
        )

    def test_apply_mutant_is_rejected_and_evidence_remains(self):
        result = assess(_MODULE.copy_document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn("p143-release-looks", result["preservedResults"])
        self.assertEqual(len(catalogue(result)["acceptedKeys"]), 2)

    def test_two_films_do_not_share_a_look(self):
        other = _MODULE.make_look(film_id="other-film", release_id="theatrical-35mm")
        result = assess(_MODULE.copy_document(looks=_MODULE.fixture_looks() + [other]))
        self.assertEqual(result["decision"], "recorded")
        distinct = catalogue(result)["distinctReleaseIds"]
        self.assertEqual(distinct["reference-film"], ["digital-sdr", "theatrical-35mm"])
        self.assertEqual(distinct["other-film"], ["theatrical-35mm"])

    def test_identical_duplicate_keys_stay_one_entry(self):
        looks = [_MODULE.make_look(), _MODULE.make_look(), _MODULE.digital_look()]
        result = assess(_MODULE.copy_document(looks=looks))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(catalogue(result)["acceptedKeys"].count("reference-film|theatrical-35mm|"), 1)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess([])
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate({"evidenceId": "p143", "looks": []})
        with self.assertRaises(ValueError):
            evaluate({"evidenceId": "p143", "looks": [{"release_id": "theatrical"}]})
        with self.assertRaises(ValueError):
            assess(_MODULE.copy_document(applyMutant="yes"))
        with self.assertRaises(ValueError):
            evaluate({
                "evidenceId": "p143",
                "looks": [{"film_id": "reference-film", "release_id": "theatrical", "parameters": {"contrast": float("nan")}}],
            })
