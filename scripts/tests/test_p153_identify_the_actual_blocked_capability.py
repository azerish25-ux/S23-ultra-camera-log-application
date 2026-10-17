"""Host checks for P153. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p153_identify_the_actual_blocked_capability",
    Path(__file__).resolve().parents[1] / "gates" / "p153_identify_the_actual_blocked_capability.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
QUESTION = "raw-route missing sustained-disk-write-megabytes-per-second"


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P153_IDENTIFY_THE_ACTUAL_BLOCKED_CAPABILITY.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def hypothesis(**overrides):
    return _MODULE.fixture_hypothesis(**overrides)


class P153Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p153-blocked-capability"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P153")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.UNMEASURED_FPS_CANNOT_PROVE, " ".join(result["reasons"]))

    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P153")
        self.assertEqual(_MODULE.WORKSTREAM, 20)
        self.assertEqual(_MODULE.TITLE, "Identify the actual blocked capability")
        self.assertEqual(_MODULE.GOAL, "State a concrete research question before proposing firmware work.")
        self.assertEqual(
            _MODULE.METHOD,
            "Use current public diagnostics and failed qualified app experiments to locate the "
            "bottleneck: sensor stream, HAL exposure, codec interface, synchronization, or app "
            "performance. Specify the desired observation and an alternative application-level "
            "path. Avoid vague goals such as unlock everything.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A RAW route limited by measured disk throughput rather than a denied camera mode.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The research plan addresses storage and buffering before proposing a firmware modification.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Attribute every low frame rate to Samsung restrictions without measurements.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Blocked-capability hypothesis and evidence dossier")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P008", "P016", "P040", "P152"))
        self.assertEqual(_MODULE.SLUG, "identify_the_actual_blocked_capability")
        self.assertEqual(len(_MODULE.CASES), 8)
        self.assertEqual(_MODULE.CASES[0]["id"], "TC-P153-01")
        self.assertEqual(_MODULE.CASES[0]["name"], "Wrong bottleneck attribution")
        self.assertEqual(_MODULE.CASES[7]["id"], "TC-P153-08")
        self.assertEqual(_MODULE.CASES[7]["name"], "Unreproducible research closure")
        self.assertIn("measurement_id null", _MODULE.HYPOTHESIS_RULE)
        self.assertIn("Low fps alone", _MODULE.HYPOTHESIS_RULE)
        self.assertIn("never qualified", _MODULE.HYPOTHESIS_RULE)
        self.assertEqual(
            _MODULE.UNMEASURED_FPS_CANNOT_PROVE,
            "a firmware restriction, a Samsung restriction, or any vendor block",
        )

    def test_fixture_records_disk_throughput_before_firmware(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn(QUESTION, result["openQuestions"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.HYPOTHESIS_RULE, " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        self.assertEqual(snapshot["limiterCause"], "disk-throughput")
        self.assertEqual(snapshot["route"], "raw")
        self.assertEqual(snapshot["limiterMeasurement"], "disk-throughput-m1")
        self.assertEqual(snapshot["plan"][:2], ["buffering", "storage"])
        self.assertNotIn("firmware", snapshot["plan"])
        self.assertEqual(snapshot["concreteQuestions"], [QUESTION])
        self.assertEqual(snapshot["fpsDrops"][0]["observed_fps"], 8)
        self.assertEqual(snapshot["fpsDrops"][0]["advertised_fps"], 24)
        self.assertFalse(snapshot["fpsDrops"][0]["claims_restriction"])
        self.assertEqual(snapshot["unmeasuredFpsCannotProve"], _MODULE.UNMEASURED_FPS_CANNOT_PROVE)
        self.assertFalse(snapshot["mutantAttributedLowFps"])
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_unmeasured_firmware_blame_is_rejected(self):
        result = assess(document(hypotheses=[hypothesis(blamed="firmware", measurement_id=None)]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNMEASURED_FIRMWARE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.LOW_FPS_ALONE, result["rejectedClaims"])
        self.assertIn("p153-blocked-capability", result["preservedResults"])
        self.assertIsNone(result["preservedResults"][1]["fpsDrops"][0]["measurement_id"])

    def test_unmeasured_samsung_blame_is_rejected(self):
        result = assess(document(hypotheses=[hypothesis(vendor="Samsung", measurement_id=None)]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNMEASURED_SAMSUNG, result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        lower = assess(document(hypotheses=[hypothesis(vendor="samsung", measurement_id=None, blamed="unknown")]))
        self.assertIn(_MODULE.UNMEASURED_SAMSUNG, lower["rejectedClaims"])

    def test_measured_firmware_or_samsung_blame_is_not_the_unmeasured_fault(self):
        firmware = assess(document(hypotheses=[hypothesis(
            blamed="firmware",
            vendor=None,
            measurement_id="hal-m1",
            claims_restriction=True,
        )]))
        self.assertEqual(firmware["decision"], "recorded")
        self.assertNotIn(_MODULE.UNMEASURED_FIRMWARE, firmware["rejectedClaims"])
        self.assertNotIn(_MODULE.LOW_FPS_ALONE, firmware["rejectedClaims"])
        self.assertNotIn(firmware["decision"], {"qualified", "allowed"})
        samsung = assess(document(hypotheses=[hypothesis(vendor="Samsung", measurement_id="disk-throughput-m1")]))
        self.assertEqual(samsung["decision"], "recorded")
        self.assertNotIn(_MODULE.UNMEASURED_SAMSUNG, samsung["rejectedClaims"])

    def test_low_fps_alone_is_not_a_restriction(self):
        result = assess(document(hypotheses=[hypothesis(
            measurement_id=None,
            blamed="unknown",
            claims_restriction=True,
        )]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOW_FPS_ALONE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.RESTRICTION_UNMEASURED, result["rejectedClaims"])
        self.assertIn("low fps alone is not proof of a restriction", result["reasons"])
        measured = assess(document(hypotheses=[hypothesis(claims_restriction=True)]))
        self.assertEqual(measured["decision"], "recorded")
        self.assertNotIn(_MODULE.LOW_FPS_ALONE, measured["rejectedClaims"])
        no_drop = assess(document(hypotheses=[hypothesis(
            observed_fps=24,
            advertised_fps=24,
            measurement_id=None,
            claims_restriction=True,
            blamed="unknown",
        )]))
        self.assertEqual(no_drop["decision"], "rejected")
        self.assertIn(_MODULE.RESTRICTION_UNMEASURED, no_drop["rejectedClaims"])
        self.assertNotIn(_MODULE.LOW_FPS_ALONE, no_drop["rejectedClaims"])
        self.assertEqual(no_drop["preservedResults"][1]["fpsDrops"], [])

    def test_concrete_question_requires_capability_and_missing_measurement(self):
        vague = assess(document(questions=[{
            "capability": None,
            "missing_measurement": None,
            "text": "unlock everything",
            "concrete": True,
        }]))
        self.assertEqual(vague["decision"], "rejected")
        self.assertIn(_MODULE.VAGUE_UNLOCK, vague["rejectedClaims"])
        self.assertIn(_MODULE.UNNAMED_CONCRETE, vague["rejectedClaims"])
        self.assertIn(_MODULE.CONCRETE_MISSING, vague["rejectedClaims"])
        self.assertNotIn(QUESTION, vague["openQuestions"])
        self.assertEqual(vague["preservedResults"][1]["concreteQuestions"], [])
        unnamed = assess(document(questions=[_MODULE.fixture_question(
            capability="raw-route",
            missing_measurement=None,
            concrete=True,
        )]))
        self.assertIn(_MODULE.UNNAMED_CONCRETE, unnamed["rejectedClaims"])
        self.assertNotIn(QUESTION, unnamed["openQuestions"])
        other = assess(document(questions=[_MODULE.fixture_question(
            capability="ten-bit-encoding",
            missing_measurement="p010-sample-receipt",
        )]))
        self.assertEqual(other["decision"], "rejected")
        self.assertIn(_MODULE.QUESTION_NOT_HYPOTHESIZED, other["rejectedClaims"])
        self.assertIn("ten-bit-encoding missing p010-sample-receipt", other["openQuestions"])

    def test_storage_and_buffering_precede_firmware(self):
        early = assess(document(plan=[
            {"id": "fw", "addresses": "firmware"},
            {"id": "buffer-depth", "addresses": "buffering"},
            {"id": "disk-throughput", "addresses": "storage"},
            {"id": "app-path", "addresses": "alternative-app-path"},
        ]))
        self.assertEqual(early["decision"], "rejected")
        self.assertIn(_MODULE.FIRMWARE_BEFORE_STORAGE, early["rejectedClaims"])
        self.assertIn(_MODULE.ORACLE, early["reasons"])
        missing = assess(document(plan=[
            {"id": "disk-throughput", "addresses": "storage"},
            {"id": "app-path", "addresses": "alternative-app-path"},
        ]))
        self.assertIn(_MODULE.FIRMWARE_BEFORE_STORAGE, missing["rejectedClaims"])
        self.assertNotIn(_MODULE.ALTERNATIVE_MISSING, missing["rejectedClaims"])
        denied = assess(document(limiter=_MODULE.fixture_limiter(cause="denied-camera-mode")))
        self.assertIn(_MODULE.LIMITER_NOT_DISK, denied["rejectedClaims"])
        self.assertNotIn(_MODULE.FIRMWARE_BEFORE_STORAGE, denied["rejectedClaims"])
        unmeasured = assess(document(limiter=_MODULE.fixture_limiter(measurement_id=None)))
        self.assertIn(_MODULE.DISK_UNMEASURED, unmeasured["rejectedClaims"])
        jpeg = assess(document(limiter=_MODULE.fixture_limiter(route="jpeg")))
        self.assertIn(_MODULE.ROUTE_NOT_RAW, jpeg["rejectedClaims"])

    def test_apply_mutant_attributes_low_fps_without_using_the_measurement(self):
        result = assess(document(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT_FPS, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertTrue(result["preservedResults"][1]["mutantAttributedLowFps"])
        self.assertEqual(result["preservedResults"][1]["fpsDrops"][0]["measurement_id"], "disk-throughput-m1")
        quiet = assess(document(
            applyMutant=True,
            hypotheses=[hypothesis(observed_fps=24, advertised_fps=24)],
        ))
        self.assertEqual(quiet["decision"], "recorded")
        self.assertFalse(quiet["preservedResults"][1]["mutantAttributedLowFps"])
        self.assertNotIn(_MODULE.MUTANT_FPS, quiet["rejectedClaims"])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P154"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            document(hypotheses=[]),
            document(hypotheses=[hypothesis(blamed="samsung")]),
            document(hypotheses=[hypothesis(observed_fps=float("nan"))]),
            document(hypotheses=[hypothesis(measurement_id="")]),
            document(questions=[{"capability": "raw-route"}]),
            document(plan=[]),
            document(limiter={"route": "raw", "cause": "disk-throughput"}),
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
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P153-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P153")
        self.assertEqual(handoff["nextPhase"], "P154")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p153*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P153_IDENTIFY_THE_ACTUAL_BLOCKED_CAPABILITY.md").read_text(encoding="utf-8")
        self.assertIn("Blocked-capability hypothesis and evidence dossier", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("measurement_id", note)
        self.assertIn("Low fps alone", note)
        self.assertIn("Samsung", note)
        self.assertIn("storage and buffering", note)
        self.assertIn(_MODULE.UNMEASURED_FPS_CANNOT_PROVE, note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("never `qualified` or `allowed`", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p153_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p153_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P153-0{index}")
            self.assertEqual(module.CASE["phase"], "P153")
            self.assertEqual(module.CASE["workstream"], 20)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
