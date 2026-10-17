"""Host checks for P149. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p149_establish_thermal_and_endurance_acceptance",
    Path(__file__).resolve().parents[1] / "gates" / "p149_establish_thermal_and_endurance_acceptance.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P149_ESTABLISH_THERMAL_AND_ENDURANCE_ACCEPTANCE.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


class P149Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P149")
        self.assertEqual(_MODULE.WORKSTREAM, 19)
        self.assertEqual(_MODULE.TITLE, "Establish thermal and endurance acceptance")
        self.assertEqual(_MODULE.GOAL, "Use conservative safety policies and measured operating envelopes.")
        self.assertEqual(
            _MODULE.METHOD,
            "Run controlled sustained tests across relevant source and render configurations, "
            "record ambient conditions and device state, and observe thermal callbacks. Reduce "
            "optional preview work first. Severe pressure triggers a controlled stop that preserves "
            "footage; do not bypass protections.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A prolonged high-resolution take followed by deferred depth rendering while the phone is already warm.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The app follows its documented limits, retains media, and does not claim unlimited performance from a short cold run.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Ignore severe thermal status to maintain an advertised frame-rate claim.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Endurance protocol and configuration-specific operating envelope")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P148",))
        self.assertEqual(
            _MODULE.THERMAL_STATUSES,
            frozenset({"none", "moderate", "severe", "critical", "unknown"}),
        )
        self.assertIn("continue_capture false", _MODULE.THERMAL_RULE)
        self.assertIn("advertised_fps claimed", _MODULE.THERMAL_RULE)
        self.assertIn("measured_on_device true", _MODULE.THERMAL_RULE)
        self.assertIn("unavailable", _MODULE.THERMAL_RULE)
        self.assertIn("short sample", _MODULE.THERMAL_RULE)
        self.assertIn("never qualified", _MODULE.THERMAL_RULE)

    def test_unmeasured_warm_protocol_is_recorded_not_qualified(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P149")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.THERMAL_RULE, " ".join(result["reasons"]))
        self.assertIn("document says unavailable", " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        self.assertEqual(snapshot["thermalStatus"], "moderate")
        self.assertTrue(snapshot["continueCapture"])
        self.assertTrue(snapshot["optionalPreviewReduced"])
        self.assertFalse(snapshot["advertisedFpsClaimed"])
        self.assertFalse(snapshot["measuredOnDevice"])
        self.assertEqual(snapshot["envelopeStatus"], "unavailable")
        self.assertFalse(snapshot["envelopeRecorded"])
        self.assertFalse(snapshot["physicalPass"])
        self.assertIsNone(snapshot["envelope"])
        self.assertFalse(snapshot["shortSample"])
        self.assertFalse(snapshot["ignoredSevereForAdvertisedFps"])
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_ignoring_severe_thermal_for_advertised_fps_is_rejected(self):
        result = evaluate(_MODULE.canonical_severe_mutant())
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.ADVERTISED_FPS_IGNORED_SEVERE, result["rejectedClaims"])
        self.assertIn(_MODULE.SEVERE_OR_CRITICAL_CONTINUED, result["rejectedClaims"])
        self.assertIn(_MODULE.OPTIONAL_PREVIEW_NOT_REDUCED, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertTrue(result["preservedResults"][1]["ignoredSevereForAdvertisedFps"])
        self.assertIn("p149-thermal-endurance", result["preservedResults"])
        critical = evaluate(_MODULE.canonical_severe_mutant(thermalStatus="critical"))
        self.assertEqual(critical["decision"], "rejected")
        self.assertIn(_MODULE.ADVERTISED_FPS_IGNORED_SEVERE, critical["rejectedClaims"])

    def test_severe_without_advertised_fps_still_requires_a_stop(self):
        result = evaluate(_MODULE.core_payload(
            thermalStatus="severe",
            continueCapture=True,
            controlledStop=False,
            advertisedFpsClaimed=False,
            optionalPreviewReduced=True,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SEVERE_OR_CRITICAL_CONTINUED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.ADVERTISED_FPS_IGNORED_SEVERE, result["rejectedClaims"])

    def test_continue_capture_false_resolves_severe_pressure(self):
        result = evaluate(_MODULE.core_payload(
            thermalStatus="severe",
            continueCapture=False,
            controlledStop=False,
            advertisedFpsClaimed=False,
            footagePreserved=True,
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][1]["pressureResolved"])
        self.assertFalse(result["preservedResults"][1]["physicalPass"])

    def test_controlled_stop_under_critical_preserves_footage(self):
        result = evaluate(_MODULE.canonical_critical_stop())
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][1]["controlledStop"])
        self.assertFalse(result["preservedResults"][1]["continueCapture"])
        self.assertTrue(result["preservedResults"][1]["footagePreserved"])
        dropped = evaluate(_MODULE.canonical_critical_stop(footagePreserved=False))
        self.assertEqual(dropped["decision"], "rejected")
        self.assertIn(_MODULE.FOOTAGE_NOT_PRESERVED, dropped["rejectedClaims"])

    def test_controlled_stop_allows_continue_flag_without_an_advertised_fps(self):
        result = evaluate(_MODULE.core_payload(
            thermalStatus="severe",
            continueCapture=True,
            controlledStop=True,
            advertisedFpsClaimed=False,
            footagePreserved=True,
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(_MODULE.ADVERTISED_FPS_IGNORED_SEVERE, result["rejectedClaims"])

    def test_unmeasured_recorded_envelope_is_not_a_physical_pass(self):
        result = assess(document(envelopeStatus="recorded", measuredOnDevice=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ENVELOPE_WITHOUT_MEASUREMENT, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["physicalPass"])
        self.assertFalse(result["preservedResults"][1]["envelopeRecorded"])
        self.assertIn("not a physical pass", " ".join(result["reasons"]))
        self.assertIn("p149-thermal-endurance", result["preservedResults"])

    def test_measured_envelope_is_recorded_and_still_not_qualified(self):
        result = assess(document(
            measuredOnDevice=True,
            envelopeStatus="recorded",
            deviceState="warm-measured",
            thermalStatus="moderate",
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        snapshot = result["preservedResults"][1]
        self.assertTrue(snapshot["envelopeRecorded"])
        self.assertTrue(snapshot["physicalPass"])
        self.assertEqual(snapshot["envelope"]["configuration"], _MODULE.CONFIGURATION)
        self.assertTrue(snapshot["envelope"]["measuredOnDevice"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_short_sample_cannot_claim_a_frame_rate_guarantee(self):
        short = assess(document(
            sampleDurationSeconds=5,
            frameRateGuaranteeClaimed=True,
            measuredOnDevice=True,
            envelopeStatus="recorded",
        ))
        self.assertEqual(short["decision"], "rejected")
        self.assertIn(_MODULE.FRAME_RATE_FROM_SHORT_SAMPLE, short["rejectedClaims"])
        self.assertNotIn(_MODULE.FRAME_RATE_WITHOUT_MEASURED_ENVELOPE, short["rejectedClaims"])
        self.assertTrue(short["preservedResults"][1]["shortSample"])
        self.assertTrue(short["preservedResults"][1]["envelopeRecorded"])
        unmeasured = assess(document(sampleDurationSeconds=5, frameRateGuaranteeClaimed=True))
        self.assertEqual(unmeasured["decision"], "rejected")
        self.assertIn(_MODULE.FRAME_RATE_FROM_SHORT_SAMPLE, unmeasured["rejectedClaims"])
        self.assertIn(_MODULE.FRAME_RATE_WITHOUT_MEASURED_ENVELOPE, unmeasured["rejectedClaims"])
        long_unmeasured = assess(document(frameRateGuaranteeClaimed=True))
        self.assertEqual(long_unmeasured["decision"], "rejected")
        self.assertIn(_MODULE.FRAME_RATE_WITHOUT_MEASURED_ENVELOPE, long_unmeasured["rejectedClaims"])
        self.assertNotIn(_MODULE.FRAME_RATE_FROM_SHORT_SAMPLE, long_unmeasured["rejectedClaims"])

    def test_apply_mutant_rejects_the_advertised_rate_bypass(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ADVERTISED_FPS_IGNORED_SEVERE, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertTrue(result["preservedResults"][1]["mutantApplied"])
        self.assertIn("p149-thermal-endurance", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_warm_capture_must_reduce_optional_preview_first(self):
        result = evaluate(_MODULE.core_payload(optionalPreviewReduced=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OPTIONAL_PREVIEW_NOT_REDUCED, result["rejectedClaims"])
        stopped = evaluate(_MODULE.core_payload(
            thermalStatus="moderate",
            continueCapture=False,
            optionalPreviewReduced=False,
        ))
        self.assertEqual(stopped["decision"], "recorded")

    def test_unknown_thermal_status_is_not_a_pressure_stop(self):
        result = evaluate(_MODULE.core_payload(thermalStatus="unknown", optionalPreviewReduced=False))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["thermalStatus"], "unknown")
        self.assertFalse(result["preservedResults"][1]["physicalPass"])

    def test_none_does_not_require_a_stop(self):
        result = evaluate(_MODULE.core_payload(thermalStatus="none", optionalPreviewReduced=False))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P150"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            document(thermalStatus="hot"),
            document(envelopeStatus="qualified"),
            document(sampleDurationSeconds=0),
            document(sampleDurationSeconds=float("nan")),
            document(continueCapture="yes"),
            document(measuredOnDevice=1),
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
            evaluate(_MODULE.core_payload(thermalStatus="severe-ish"))

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P149-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P149")
        self.assertEqual(handoff["nextPhase"], "P150")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p149*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P149_ESTABLISH_THERMAL_AND_ENDURANCE_ACCEPTANCE.md").read_text(encoding="utf-8")
        self.assertIn("Endurance protocol and configuration-specific operating envelope", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("continue_capture", note)
        self.assertIn("measured_on_device", note)
        self.assertIn("unavailable", note)
        self.assertIn("short sample", note)
        self.assertIn("advertised", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("never `qualified` or `allowed`", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p149_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p149_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P149-0{index}")
            self.assertEqual(module.CASE["phase"], "P149")
            self.assertEqual(module.CASE["workstream"], 19)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
