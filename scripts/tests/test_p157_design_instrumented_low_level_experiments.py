"""Host checks for P157. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p157_design_instrumented_low_level_experiments",
    Path(__file__).resolve().parents[1] / "gates" / "p157_design_instrumented_low_level_experiments.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P157_DESIGN_INSTRUMENTED_LOW_LEVEL_EXPERIMENTS.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    if "experiments" in overrides and "checksum" not in overrides:
        value["checksum"] = _MODULE.protocol_checksum(value["experiments"])
    return value


class P157Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P157")
        self.assertEqual(_MODULE.WORKSTREAM, 20)
        self.assertEqual(_MODULE.TITLE, "Design instrumented low-level experiments")
        self.assertEqual(
            _MODULE.GOAL,
            "Make any authorized low-level change minimal, observable, and reversible where technically possible.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Change one hypothesized constraint at a time, preserve the baseline, record checksums and logs, "
            "and define failure triggers before execution. Do not disable thermal safeguards or falsify "
            "capability metadata to make unsupported modes appear available.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A modification that changes advertised stream metadata but produces no valid additional sensor frames.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The experiment fails its actual-delivery hypothesis despite the expanded menu.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Call an advertised mode unlocked without capturing and validating its output.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Instrumented experimental protocol and observation schema")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P156",))
        self.assertIn("unlocked_claim", _MODULE.PROTOCOL_RULE)
        self.assertIn("captured_output", _MODULE.PROTOCOL_RULE)
        self.assertIn("recovery step", _MODULE.PROTOCOL_RULE)
        self.assertIn("before and after", _MODULE.PROTOCOL_RULE)
        self.assertIn("design", _MODULE.PROTOCOL_RULE)
        self.assertIn("completed device experiment", _MODULE.PROTOCOL_RULE)
        self.assertIn("never qualified", _MODULE.PROTOCOL_RULE)

    def test_design_protocol_is_recorded_and_not_qualified(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P157")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn(_MODULE.PROTOCOL_RULE, " ".join(result["reasons"]))
        self.assertIn("not a completed device experiment", " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        self.assertTrue(snapshot["recordedAsDesign"])
        self.assertEqual(snapshot["qualification"], "not-qualified")
        self.assertFalse(snapshot["deviceExperimentCompleted"])
        self.assertEqual(snapshot["unlockedWithoutOutput"], [])
        self.assertTrue(snapshot["checksumMatches"])
        self.assertEqual(snapshot["constraintCounts"], {"encoder-scheduling": 1})
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_unlocked_claim_without_captured_output_is_rejected(self):
        result = assess(document(experiments=[_MODULE.unlocked_metadata_experiment()]))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.UNLOCKED_WITHOUT_OUTPUT, result["rejectedClaims"])
        self.assertIn(_MODULE.ORACLE, result["reasons"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertIn("p157-instrumented-experiment-design", result["preservedResults"])
        self.assertEqual(
            result["preservedResults"][1]["unlockedWithoutOutput"],
            ["advertised-stream-metadata"],
        )
        self.assertTrue(result["preservedResults"][1]["recordedAsDesign"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_unlocked_claim_with_captured_output_is_recorded(self):
        experiment = _MODULE.unlocked_metadata_experiment()
        experiment["captured_output"] = True
        result = assess(document(experiments=[experiment]))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["unlockedWithoutOutput"], [])

    def test_apply_mutant_rejects_the_unlock_without_output(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNLOCKED_WITHOUT_OUTPUT, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, " ".join(result["reasons"]))
        self.assertIn("p157-instrumented-experiment-design", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_irreversible_change_without_recovery_is_rejected(self):
        result = assess(document(experiments=[_MODULE.irreversible_without_recovery_experiment()]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.IRREVERSIBLE_WITHOUT_RECOVERY, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["irreversibleWithoutRecovery"], ["unverified-flash"])
        self.assertIn("recovery step", " ".join(result["reasons"]))
        repaired = _MODULE.irreversible_without_recovery_experiment()
        repaired["recoveryStep"] = "restore the verified stock image for this exact device variant"
        recovered = assess(document(experiments=[repaired]))
        self.assertEqual(recovered["decision"], "recorded")
        self.assertEqual(recovered["preservedResults"][1]["irreversibleWithoutRecovery"], [])

    def test_observations_without_distinct_identifiers_are_rejected(self):
        experiment = _MODULE.fixture_experiments()[0]
        experiment["observations"] = {"before": "same-observation", "after": "same-observation"}
        result = assess(document(experiments=[experiment]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OBSERVATION_IDENTIFIERS_MISSING, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["observationIdentifierFaults"], ["encoder-scheduling"])
        blank = _MODULE.fixture_experiments()[0]
        blank["observations"] = {"before": "", "after": "obs-after"}
        blanked = assess(document(experiments=[blank]))
        self.assertEqual(blanked["decision"], "rejected")
        self.assertIn(_MODULE.OBSERVATION_IDENTIFIERS_MISSING, blanked["rejectedClaims"])

    def test_completed_device_experiment_is_rejected(self):
        result = assess(document(protocolKind="completed", deviceExperimentCompleted=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOT_A_DESIGN, result["rejectedClaims"])
        self.assertIn(_MODULE.COMPLETED_DEVICE_EXPERIMENT, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["recordedAsDesign"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("p157-instrumented-experiment-design", result["preservedResults"])

    def test_method_guards_reject_unsafe_or_uninstrumented_designs(self):
        thermal = assess(document(thermalSafeguardDisabled=True))
        self.assertIn(_MODULE.THERMAL_SAFEGUARD_DISABLED, thermal["rejectedClaims"])
        falsified = assess(document(capabilityMetadataFalsified=True))
        self.assertIn(_MODULE.CAPABILITY_METADATA_FALSIFIED, falsified["rejectedClaims"])
        baseline = assess(document(baselinePreserved=False))
        self.assertIn(_MODULE.BASELINE_NOT_PRESERVED, baseline["rejectedClaims"])
        checksum = assess(document(checksum="0" * 64))
        self.assertEqual(checksum["decision"], "rejected")
        self.assertIn(_MODULE.CHECKSUM_MISMATCH, checksum["rejectedClaims"])
        self.assertFalse(checksum["preservedResults"][1]["checksumMatches"])
        triggers = assess(document(failureTriggers=[]))
        self.assertIn(_MODULE.FAILURE_TRIGGERS_MISSING, triggers["rejectedClaims"])
        experiment = _MODULE.fixture_experiments()[0]
        experiment["constraints"] = ["encoder-scheduling", "thermal-policy"]
        multiple = assess(document(experiments=[experiment]))
        self.assertIn(_MODULE.NOT_ONE_CONSTRAINT, multiple["rejectedClaims"])
        self.assertEqual(multiple["preservedResults"][1]["constraintCounts"]["encoder-scheduling"], 2)

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P158"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            document(experiments=[]),
            document(checksum="abc"),
            document(protocolKind="mystery"),
            document(failureTriggers=["duplicate", "duplicate"]),
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    assess(payload)
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        experiment = _MODULE.fixture_experiments()[0]
        experiment["observations"] = {"before": "only-before"}
        with self.assertRaises(ValueError):
            assess(document(experiments=[experiment], checksum="0" * 64))

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P157-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P157")
        self.assertEqual(handoff["nextPhase"], "P158")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p157*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P157_DESIGN_INSTRUMENTED_LOW_LEVEL_EXPERIMENTS.md").read_text(encoding="utf-8")
        self.assertIn("Instrumented experimental protocol and observation schema", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("unlocked_claim", note)
        self.assertIn("captured_output", note)
        self.assertIn("recovery step", note)
        self.assertIn("before and after", note)
        self.assertIn("completed device experiment", note)
        self.assertIn("never `qualified` or `allowed`", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p157_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p157_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P157-0{index}")
            self.assertEqual(module.CASE["phase"], "P157")
            self.assertEqual(module.CASE["workstream"], 20)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
