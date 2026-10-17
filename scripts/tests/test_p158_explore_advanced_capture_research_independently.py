"""Host checks for P158. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p158_explore_advanced_capture_research_independently",
    Path(__file__).resolve().parents[1] / "gates" / "p158_explore_advanced_capture_research_independently.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P158_EXPLORE_ADVANCED_CAPTURE_RESEARCH_INDEPENDENTLY.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def hidden_artifact(**overrides):
    artifact = {"reported": False, "hidden": True, "magnitude": 0.2}
    artifact.update(overrides)
    return artifact


class P158Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P158")
        self.assertEqual(_MODULE.WORKSTREAM, 20)
        self.assertEqual(_MODULE.TITLE, "Explore advanced capture research independently")
        self.assertEqual(
            _MODULE.GOAL,
            "Investigate multi-frame HDR, alternative RAW modes, and synchronization only as "
            "clearly labelled experiments.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Define source sampling, motion assumptions, exposure differences, merge artifacts, "
            "and output lineage. Compare against single-exposure baselines. Multi-frame "
            "computational capture must not be presented as a single unmodified sensor exposure "
            "or guaranteed dynamic-range increase in every scene.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A moving subject across differently exposed frames used for a computational HDR merge.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The report measures motion artifacts and retained highlight information separately "
            "and labels the merge explicitly.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Advertise merged dynamic range without testing motion or alignment failures.",
        )
        self.assertEqual(
            _MODULE.DELIVERABLE,
            "Advanced capture experiment and motion-aware acceptance plan",
        )
        self.assertEqual(_MODULE.DEPENDENCIES, ("P157",))
        self.assertIn("claims_extra_stops > 0", _MODULE.MOTION_RULE)
        self.assertIn("motion_alignment", _MODULE.MOTION_RULE)
        self.assertIn("ghosting or alignment error", _MODULE.MOTION_RULE)
        self.assertIn("measurement id", _MODULE.MOTION_RULE)
        self.assertIn("never qualified", _MODULE.MOTION_RULE)
        self.assertIn("sensor-derived Log", _MODULE.MOTION_RULE)
        self.assertIn("experimental", _MODULE.MOTION_RULE)
        self.assertTrue(
            _MODULE.advertises_without_motion_test(2, False)
        )
        self.assertFalse(
            _MODULE.advertises_without_motion_test(2, True)
        )
        self.assertFalse(
            _MODULE.advertises_without_motion_test(0, False)
        )

    def test_fixture_records_an_experimental_merge_with_motion_alignment(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P158")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("sensor-derived Log was not established", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.MOTION_RULE, " ".join(result["reasons"]))
        self.assertIn("claims_extra_stops 2 motion_alignment present", result["reasons"])
        snapshot = result["preservedResults"][1]
        self.assertEqual(snapshot["experimentLabel"], "experimental")
        self.assertEqual(snapshot["claimsExtraStops"], 2)
        self.assertTrue(snapshot["motionAlignmentPresent"])
        self.assertEqual(snapshot["motionAlignmentStatus"], "pass")
        self.assertTrue(snapshot["ghostingReported"])
        self.assertFalse(snapshot["ghostingHidden"])
        self.assertTrue(snapshot["alignmentErrorReported"])
        self.assertFalse(snapshot["alignmentErrorHidden"])
        self.assertTrue(snapshot["measurementsSeparate"])
        self.assertEqual(snapshot["unmeasuredAvailableRawModes"], [])
        self.assertFalse(snapshot["claimsSensorDerivedLog"])
        self.assertEqual(snapshot["baselineEvidenceId"], _MODULE.BASELINE_EVIDENCE_ID)
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_advertising_stops_without_motion_alignment_is_rejected(self):
        result = assess(document(motionAlignment=None))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.MERGED_DR_WITHOUT_MOTION, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["motionAlignmentPresent"])
        self.assertEqual(result["preservedResults"][1]["claimsExtraStops"], 2)
        self.assertIn("p158-advanced-capture", result["preservedResults"])
        self.assertIn("motion_alignment test result", " ".join(result["reasons"]))
        self.assertIn("claims_extra_stops 2 motion_alignment absent", result["reasons"])
        zero = assess(document(claimsExtraStops=0, motionAlignment=None))
        self.assertEqual(zero["decision"], "recorded")
        self.assertEqual(zero["rejectedClaims"], [])

    def test_apply_mutant_advertises_dynamic_range_without_a_motion_test(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MERGED_DR_WITHOUT_MOTION, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["motionAlignmentPresent"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertIn(_MODULE.MOTION_RULE, " ".join(result["reasons"]))
        self.assertIn("p158-advanced-capture", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        forced = assess(document(applyMutant=True, claimsExtraStops=0, motionAlignment=None))
        self.assertEqual(forced["decision"], "rejected")
        self.assertEqual(forced["preservedResults"][1]["requestedClaimsExtraStops"], 0)
        self.assertEqual(forced["preservedResults"][1]["claimsExtraStops"], 1)
        self.assertIn(_MODULE.MERGED_DR_WITHOUT_MOTION, forced["rejectedClaims"])

    def test_multi_frame_hdr_must_report_ghosting_or_alignment_error(self):
        hidden = assess(document(
            ghosting=hidden_artifact(),
            alignmentError=hidden_artifact(magnitude=1.5),
        ))
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn(_MODULE.HIDDEN_MERGE_ARTIFACT, hidden["rejectedClaims"])
        self.assertNotIn(_MODULE.MERGED_DR_WITHOUT_MOTION, hidden["rejectedClaims"])
        self.assertTrue(hidden["preservedResults"][1]["ghostingHidden"])
        self.assertIn("p158-advanced-capture", hidden["preservedResults"])
        omitted = assess(document(
            ghosting={"reported": False, "hidden": False, "magnitude": 0},
            alignmentError={"reported": False, "hidden": False, "magnitude": 0},
            mergeArtifacts=["unspecified"],
        ))
        self.assertEqual(omitted["decision"], "rejected")
        self.assertIn(_MODULE.HIDDEN_MERGE_ARTIFACT, omitted["rejectedClaims"])
        reported = assess(document(
            motionAlignment={"status": "fail", "error": 1.5, "frames": 3},
            alignmentError={"reported": True, "hidden": False, "magnitude": 1.5},
            ghosting={"reported": True, "hidden": False, "magnitude": 0.2},
        ))
        self.assertEqual(reported["decision"], "recorded")
        self.assertEqual(reported["preservedResults"][1]["motionAlignmentStatus"], "fail")
        self.assertNotIn(reported["decision"], {"qualified", "allowed"})

    def test_alternative_raw_stays_unavailable_without_a_measurement_id(self):
        modes = [
            {"id": "raw-10bit", "available": True, "measurementId": None},
            {"id": "raw-14bit", "available": False, "measurementId": None},
        ]
        result = assess(document(alternativeRawModes=modes))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ALT_RAW_WITHOUT_MEASUREMENT, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["unmeasuredAvailableRawModes"], ["raw-10bit"])
        self.assertIn("p158-advanced-capture", result["preservedResults"])
        measured = assess(document(alternativeRawModes=[
            {"id": "raw-14bit", "available": True, "measurementId": "meas-raw-14bit-001"},
        ]))
        self.assertEqual(measured["decision"], "recorded")

    def test_label_must_be_experimental_and_sensor_log_is_not_claimed(self):
        labelled = assess(document(experimentLabel="qualified"))
        self.assertEqual(labelled["decision"], "rejected")
        self.assertNotIn(labelled["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.LABEL_NOT_EXPERIMENTAL, labelled["rejectedClaims"])
        sync = assess(document(synchronization={
            "labelled": "production",
            "offsetMeasured": False,
            "offsetMs": None,
        }))
        self.assertIn(_MODULE.LABEL_NOT_EXPERIMENTAL, sync["rejectedClaims"])
        sensor = assess(document(claimsSensorDerivedLog=True))
        self.assertEqual(sensor["decision"], "rejected")
        self.assertIn(_MODULE.SENSOR_DERIVED_LOG, sensor["rejectedClaims"])
        self.assertTrue(sensor["preservedResults"][1]["claimsSensorDerivedLog"])
        phrased = assess(document(claim="sensor-derived Log from the merge"))
        self.assertIn(_MODULE.SENSOR_DERIVED_LOG, phrased["rejectedClaims"])
        self.assertIn("p158-advanced-capture", phrased["preservedResults"])

    def test_merge_cannot_pose_as_an_unmodified_exposure_or_a_guarantee(self):
        posed = assess(document(presentedAs="single-unmodified-sensor-exposure"))
        self.assertEqual(posed["decision"], "rejected")
        self.assertIn(_MODULE.PRESENTED_AS_UNMODIFIED_SENSOR, posed["rejectedClaims"])
        guaranteed = assess(document(guaranteedEveryScene=True))
        self.assertIn(_MODULE.GUARANTEED_EVERY_SCENE, guaranteed["rejectedClaims"])
        unlabelled = assess(document(labelsMergeExplicitly=False))
        self.assertIn(_MODULE.MERGE_NOT_LABELLED, unlabelled["rejectedClaims"])
        collapsed = assess(document(motionArtifacts={"measured": False, "value": 0}))
        self.assertIn(_MODULE.MOTION_AND_HIGHLIGHTS_NOT_SEPARATE, collapsed["rejectedClaims"])
        same = assess(document(exposureDifferences=[0, 0]))
        self.assertIn(_MODULE.EXPOSURE_DIFFERENCE_MISSING, same["rejectedClaims"])
        self.assertIn("p158-advanced-capture", posed["preservedResults"])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P159"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            document(claimsExtraStops=-1),
            document(claimsExtraStops=True),
            document(claimsExtraStops=float("nan")),
            document(motionAlignment={"status": "unavailable", "error": 0, "frames": 1}),
            document(ghosting={"reported": True, "hidden": True, "magnitude": 0.1}),
            document(experimentLabel=""),
            document(captureKind="hdr-plus"),
            document(alternativeRawModes=[{"id": "raw", "available": True}]),
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
            evaluate({"evidenceId": "only"})

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P158-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P158")
        self.assertEqual(handoff["nextPhase"], "P159")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p158*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertIn("sensor-derived Log", handoff["unverified"])
        note = (_ROOT / "docs" / "P158_EXPLORE_ADVANCED_CAPTURE_RESEARCH_INDEPENDENTLY.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Advanced capture experiment and motion-aware acceptance plan", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("claims_extra_stops > 0", note)
        self.assertIn("motion_alignment", note)
        self.assertIn("ghosting or alignment error", note)
        self.assertIn("measurement id", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("never `qualified` or `allowed`", note)
        self.assertIn(_MODULE.MOTION_RULE, note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p158_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p158_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P158-0{index}")
            self.assertEqual(module.CASE["phase"], "P158")
            self.assertEqual(module.CASE["workstream"], 20)
            self.assertNotIn("applyNegative", module.PAYLOAD_KEYS)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
            result = module.evaluate(module.case_payload())
            self.assertEqual(result["decision"], "recorded")
            self.assertNotIn(result["decision"], {"qualified", "allowed"})
            self.assertIn("p158-advanced-capture", result["preservedResults"])
