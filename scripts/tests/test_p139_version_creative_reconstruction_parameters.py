"""Host checks for P139. Not a physical S23 probe."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p139_version_creative_reconstruction_parameters",
    Path(__file__).resolve().parents[1] / "gates" / "p139_version_creative_reconstruction_parameters.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
FACT_CANONICAL = (
    '{"camera":"Arricam ST","cinematographer":"sourced-production-account",'
    '"documentedAperture":"T2.8","documentedPrintContrast":"normal","lens":null,'
    '"process":"standard-print","releaseVersion":"theatrical-35mm",'
    '"stock":"Kodak Vision3 250D","title":"Night Ferry"}'
)


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def evaluate_payload(**overrides):
    facts = _MODULE.sample_facts()
    base = {
        "caseId": "TC-P139-03",
        "evidenceId": "p139-eval",
        "claim": _MODULE.CLAIM,
        "applyMutant": False,
        "mutated_facts": False,
        "productionFacts": facts,
        "fact_hash": _MODULE.hash_facts(facts),
        "prior_canonical": _MODULE.canonical_json(facts),
        "bound_object_id": None,
        "reconstructions": _MODULE.reconstructions_for(facts),
    }
    base.update(overrides)
    return base


class P139Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P139")
        self.assertEqual(_MODULE.WORKSTREAM, 18)
        self.assertEqual(_MODULE.DEPENDENCIES, ("P138",))
        self.assertEqual(_MODULE.TITLE, "Version creative reconstruction parameters")
        self.assertEqual(
            _MODULE.GOAL,
            "Make our interpretation editable without modifying the underlying production facts.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Keep a recipe graph linked to, but distinct from, evidence records. Version exposure, "
            "stock model, virtual lens, grain, halation, print response, and grade independently. "
            "A user adaptation becomes a derivative recipe with its own name and provenance.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A user changes the virtual aperture and print contrast of a movie-inspired recipe.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The original documented facts remain unchanged and the edited appearance is stored as a user reconstruction.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Overwrite the cinematographer\u2019s documented settings with the user\u2019s creative changes.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Reconstruction versioning and immutable fact tests")

    def test_fact_hash_is_sha256_of_canonical_json(self):
        facts = _MODULE.sample_facts()
        self.assertEqual(_MODULE.canonical_json(facts), FACT_CANONICAL)
        digest = hashlib.sha256(FACT_CANONICAL.encode("utf-8")).hexdigest()
        self.assertEqual(_MODULE.hash_facts(facts), digest)
        parent = _MODULE.creative_edit(
            facts,
            None,
            "rr-1",
            _MODULE.PARENT_NAME,
            _MODULE.PARENT_PROVENANCE,
            _MODULE.parent_parameters(),
        )
        before = _MODULE.canonical_json(facts)
        before_parent = _MODULE.canonical_json(parent)
        child = _MODULE.creative_edit(
            facts,
            parent,
            "rr-2",
            _MODULE.CHILD_NAME,
            _MODULE.CHILD_PROVENANCE,
            _MODULE.child_parameters(),
        )
        self.assertEqual(_MODULE.canonical_json(facts), before)
        self.assertEqual(_MODULE.canonical_json(parent), before_parent)
        self.assertIsNone(parent["parent_id"])
        self.assertEqual(child["parent_id"], parent["id"])
        self.assertEqual(child["fact_hash"], parent["fact_hash"])
        self.assertEqual(child["fact_hash"], digest)
        self.assertNotEqual(child["parameter_hash"], parent["parameter_hash"])
        self.assertEqual(child["label"], "user-reconstruction")
        preimage = _MODULE.parameter_preimage(parent["id"], digest, child["parameters"])
        self.assertEqual(child["parameter_hash"], hashlib.sha256(preimage.encode("utf-8")).hexdigest())
        self.assertIn('"parent":"rr-1"', preimage)
        self.assertNotIn("documentedAperture", preimage)

    def test_fixture_records_a_user_reconstruction_without_changing_facts(self):
        source = json.loads(
            (ROOT / "docs" / "P139_VERSION_CREATIVE_RECONSTRUCTION_PARAMETERS.json").read_text(encoding="utf-8")
        )
        before = json.dumps(source["productionFacts"], sort_keys=True)
        result = assess(source)
        self.assertEqual(json.dumps(source["productionFacts"], sort_keys=True), before)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P139")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("rr-1 parent=null", result["reasons"])
        self.assertIn("rr-2 parent=rr-1", result["reasons"])
        self.assertIn("rr-2 changed=virtualAperture,printContrast", result["reasons"])
        self.assertIn("fact hash unchanged", result["reasons"])
        self.assertIn("fact_hash=" + source["fact_hash"], result["preservedResults"])
        self.assertEqual(source["reconstructions"][0]["fact_hash"], source["reconstructions"][1]["fact_hash"])
        self.assertEqual(source["fact_hash"], hashlib.sha256(FACT_CANONICAL.encode("utf-8")).hexdigest())

    def test_evaluate_records_the_same_edit(self):
        result = evaluate(evaluate_payload())
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "TC-P139-03")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p139-eval", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_same_object_mutation_is_rejected(self):
        facts = _MODULE.sample_facts()
        bound = _MODULE.bind_facts(facts)
        self.assertEqual(bound["object_id"], id(facts))
        facts["documentedAperture"] = "T8"
        result = evaluate(
            evaluate_payload(
                productionFacts=facts,
                fact_hash=_MODULE.hash_facts(facts),
                prior_canonical=bound["canonical"],
                bound_object_id=bound["object_id"],
                reconstructions=_MODULE.sample_reconstructions(),
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SAME_OBJECT_MUTATED, result["rejectedClaims"])
        self.assertIn(_MODULE.FACT_HASH_CHANGED, result["rejectedClaims"])
        self.assertIn(_MODULE.DOCUMENTED_KEY_OVERWRITTEN, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn("p139-eval", result["preservedResults"])
        self.assertIn("fact_hash=" + bound["fact_hash"], result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_fact_hash_change_on_a_copy_is_rejected_without_identity(self):
        original = _MODULE.sample_facts()
        prior = _MODULE.canonical_json(original)
        edited = copy.deepcopy(original)
        edited["stock"] = "Guessed stock"
        result = assess(
            document(
                productionFacts=edited,
                fact_hash=_MODULE.hash_facts(edited),
                prior_canonical=prior,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FACT_HASH_CHANGED, result["rejectedClaims"])
        self.assertIn(_MODULE.DOCUMENTED_KEY_OVERWRITTEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.SAME_OBJECT_MUTATED, result["rejectedClaims"])
        self.assertIn("p139-reconstruction-versions", result["preservedResults"])

    def test_mutated_facts_flag_is_rejected_when_bytes_match(self):
        result = assess(document(mutated_facts=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], [_MODULE.MUTATED_FACTS])
        self.assertIn("p139-reconstruction-versions", result["preservedResults"])
        self.assertIn("fact hash unchanged", " ".join(result["reasons"]))

    def test_missing_parent_is_rejected_and_first_parent_may_be_null(self):
        alone = _MODULE.sample_reconstructions()[:1]
        recorded = assess(document(reconstructions=alone))
        self.assertEqual(recorded["decision"], "recorded")
        self.assertIn("rr-1 parent=null", recorded["reasons"])
        versions = _MODULE.sample_reconstructions()
        versions[1]["parent_id"] = "missing-parent"
        versions[1]["parameter_hash"] = _MODULE.compute_parameter_hash(
            "missing-parent",
            versions[1]["fact_hash"],
            versions[1]["parameters"],
        )
        rejected = assess(document(reconstructions=versions))
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_PARENT, rejected["rejectedClaims"])
        self.assertIn("p139-reconstruction-versions", rejected["preservedResults"])
        later_null = _MODULE.sample_reconstructions()
        later_null[1]["parent_id"] = None
        later_null[1]["parameter_hash"] = _MODULE.compute_parameter_hash(
            None,
            later_null[1]["fact_hash"],
            later_null[1]["parameters"],
        )
        null_parent = assess(document(reconstructions=later_null))
        self.assertEqual(null_parent["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_PARENT, null_parent["rejectedClaims"])

    def test_parameter_hash_mismatch_and_mutant_keep_the_fact_hash(self):
        versions = _MODULE.sample_reconstructions()
        versions[1]["parameter_hash"] = "ab" * 32
        mismatched = assess(document(reconstructions=versions))
        self.assertEqual(mismatched["decision"], "rejected")
        self.assertIn(_MODULE.PARAMETER_HASH_MISMATCH, mismatched["rejectedClaims"])
        self.assertIn("fact_hash=" + _MODULE.hash_facts(_MODULE.sample_facts()), mismatched["preservedResults"])
        mutant = assess(document(applyMutant=True))
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, mutant["rejectedClaims"])
        self.assertIn("p139-reconstruction-versions", mutant["preservedResults"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(evaluate_payload(fact_hash="AB" * 32))
        with self.assertRaises(ValueError):
            _MODULE.make_reconstruction(
                "rr-1",
                "movie-inspired",
                "catalogue-recipe",
                None,
                "ab" * 32,
                {"exposure": float("nan")},
                "creative-reconstruction",
            )

    def test_handoff_points_at_p140(self):
        handoff = json.loads((ROOT / "docs" / "evidence" / "P139-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P139")
        self.assertEqual(handoff["commit"], None)
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(handoff["nextPhase"], "P140")
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p139*.py' -v",
        )
        self.assertEqual(handoff["title"], _MODULE.TITLE)
        self.assertEqual(handoff["deliverable"], _MODULE.DELIVERABLE)
        for relative in handoff["changedFiles"]:
            self.assertTrue((ROOT / relative).is_file(), relative)
            self.assertIn("139", relative)
