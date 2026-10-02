"""P005 measurement uncertainty and integrity acceptance cases."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import measurements


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def policy(registry: dict, policy_id: str) -> dict:
    return next(item for item in registry["policies"] if item["id"] == policy_id)


class MeasurementFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = json.loads((ROOT / "docs/MEASUREMENT_REGISTRY.json").read_text())
        self.registry_hash = canonical_hash(self.registry)
        self.revision = "a" * 40
        self.current = self.revision
        self.cadence_policy = policy(self.registry, "cadence.sensor-timestamp.v1")
        self.colour_policy = policy(self.registry, "colour.chart-deltae2000.v1")
        self.precision_policy = policy(self.registry, "precision.codec-p010.v1")
        # 61 frames span exactly two seconds at 30 fps. Frame identifier 29 is duplicated,
        # so the average remains exactly 30 fps while content integrity fails.
        timestamps = [round(i * 1_000_000_000 / 30) for i in range(61)]
        identifiers = list(range(61))
        identifiers[30] = identifiers[29]
        self.record = {
            "schemaVersion": 1,
            "measurementId": "P005-authored-fixture",
            "sourceRevision": self.revision,
            "registrySha256": self.registry_hash,
            "inspection": {
                "revision": self.revision,
                "currentRevision": self.current,
                "inspectedPaths": ["app/src/main/java/com/s23log/probe/core/CapturePolicy.kt"],
                "changedPaths": [],
            },
            "environments": [
                {"id": "synthetic-host", "kind": "synthetic", "backend": "python", "available": True,
                 "details": "Authored deterministic host fixture; no phone was used."},
                {"id": "unknown-chart-lab", "kind": "host", "backend": "manual-chart", "available": True,
                 "details": "Authored noisy chart fixture with deliberately unknown illuminant."},
            ],
            "fixtures": [
                {"id": "cadence", "kind": "generated_sequence", "identity": "1" * 64,
                 "provenance": {"origin": "authored:P005-cadence", "owner": "repository tests",
                                "acquiredAt": "2026-10-02", "permittedUse": "test and private comparison"}},
                {"id": "chart", "kind": "generated_chart_measurement", "identity": "2" * 64,
                 "provenance": {"origin": "authored:P005-chart", "owner": "repository tests",
                                "acquiredAt": "2026-10-02", "permittedUse": "test and private comparison"}},
            ],
            "observations": [
                {"id": "cadence-series", "metricId": self.cadence_policy["id"],
                 "policySha256": canonical_hash(self.cadence_policy), "fixtureId": "cadence",
                 "environmentId": "synthetic-host", "sourcePaths": ["app/src/main/java/com/s23log/probe/core/CapturePolicy.kt"],
                 "unit": "ns", "domain": "sensor_timestamp", "declaredOutcome": "failed",
                 "nominalFps": 30, "timestamps": timestamps, "timestampResolution": 1,
                 "frameIdentifiers": identifiers},
                {"id": "chart-measurement", "metricId": self.colour_policy["id"],
                 "policySha256": canonical_hash(self.colour_policy), "fixtureId": "chart",
                 "environmentId": "unknown-chart-lab", "sourcePaths": [], "unit": "deltaE2000",
                 "domain": "chart_reflectance_D65", "declaredOutcome": "exploratory",
                 "deltaE2000": [1.2, 1.8, 2.4, 2.9, 3.1, 4.2], "illuminant": None,
                 "instrument": None, "chartId": "authored-noisy-chart", "calibrationTrace": None},
            ],
            "claims": [
                {"id": "mean-rate", "class": "average_cadence",
                 "statement": "The complete authored sequence has a 30 fps mean over two seconds.",
                 "dependsOn": ["cadence-series"]},
                {"id": "frame-integrity", "class": "per_frame_integrity",
                 "statement": "Every content frame is unique and cadence-integral.",
                 "dependsOn": ["cadence-series"]},
                {"id": "chart-exploration", "class": "exploratory_colour",
                 "statement": "The noisy chart numbers are retained as exploratory observations.",
                 "dependsOn": ["chart-measurement"]},
                {"id": "chart-certified", "class": "calibrated_colour",
                 "statement": "The chart establishes calibrated colour accuracy.",
                 "dependsOn": ["chart-measurement"]},
            ],
            "researchQuestions": [
                "What cadence integrity is observed on the physical S23 under a changing-content protocol?",
                "What colour error is measured under a known illuminant with a traceable instrument?",
            ],
            "declaredSummary": {
                "observationOutcomes": {"cadence-series": "failed", "chart-measurement": "exploratory"},
                "acceptedClaims": ["chart-exploration", "mean-rate"],
            },
        }

    def assess(self, record: dict | None = None, registry: dict | None = None) -> dict:
        return measurements.assess(record or self.record, registry or self.registry)

    def save_case(self, case: str, label: str, record: dict, result: object) -> None:
        location = os.environ.get("S23_P005_EVIDENCE_DIR")
        if not location:
            return
        folder = Path(location) / case
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{label}.json").write_text(json.dumps({
            "case": case,
            "fixture": "Authored P005 measurement fixture; not phone evidence",
            "input": record,
            "registrySha256": self.registry_hash,
            "result": result,
        }, indent=2, allow_nan=False) + "\n")

    def test_baseline_fixture_preserves_mean_but_fails_integrity_and_keeps_chart_exploratory(self):
        result = self.assess()
        self.assertEqual("passed", result["status"], result)
        cadence = result["observations"]["cadence-series"]
        self.assertEqual("passed", cadence["averageOutcome"])
        self.assertAlmostEqual(30.0, cadence["meanFps"], places=5)
        self.assertEqual("failed", cadence["outcome"])
        self.assertEqual([30], cadence["duplicateContentIndices"])
        self.assertEqual("exploratory", result["observations"]["chart-measurement"]["outcome"])
        self.assertEqual(["chart-exploration", "mean-rate"], result["acceptedClaims"])
        self.assertEqual(["chart-certified", "frame-integrity"], result["rejectedClaims"])
        self.assertEqual(self.record["researchQuestions"], result["researchQuestions"])

    def test_mutant_average_only_summary_cannot_pass_frame_integrity(self):
        record = deepcopy(self.record)
        cadence = record["observations"][0]
        cadence.pop("timestamps")
        cadence.pop("frameIdentifiers")
        cadence["summaryOnly"] = {"measuredFps": 30.0, "duration": 2_000_000_000,
                                  "largeIntervals": 0, "frames": 61}
        cadence["declaredOutcome"] = "passed"
        record["declaredSummary"]["observationOutcomes"]["cadence-series"] = "passed"
        record["declaredSummary"]["acceptedClaims"].append("frame-integrity")
        result = self.assess(record)
        self.assertEqual("failed", result["status"])
        self.assertEqual("inconclusive", result["observations"]["cadence-series"]["outcome"])
        self.assertIn("frame-integrity", result["rejectedClaims"])
        self.assertTrue(any("contradicts" in issue["detail"] for issue in result["issues"]))
        self.save_case("TC-P005-04", "average-only-mutant", record, result)

    def test_tc_p005_01_unsupported_physical_certainty_is_rejected_without_losing_narrow_result(self):
        for kind, available in (("emulator", True), ("simulated", True), ("physical_s23", False)):
            record = deepcopy(self.record)
            record["environments"][0].update(kind=kind, available=available)
            record["claims"].append({"id": f"physical-{kind}", "class": "physical_capture",
                                     "statement": "Physical S23 cadence is established.",
                                     "dependsOn": ["cadence-series"]})
            result = self.assess(record)
            self.assertIn("mean-rate", result["acceptedClaims"])
            self.assertIn(f"physical-{kind}", result["rejectedClaims"])
            self.assertEqual(record["researchQuestions"], result["researchQuestions"])
            self.save_case("TC-P005-01", kind, record, result)

    def test_tc_p005_01_codec_precision_does_not_become_sensor_precision(self):
        record = deepcopy(self.record)
        observed = [float(i) for i in range(600)]
        expected = observed.copy()
        record["observations"].append({"id": "codec-ramp", "metricId": self.precision_policy["id"],
            "policySha256": canonical_hash(self.precision_policy), "fixtureId": "cadence",
            "environmentId": "synthetic-host", "sourcePaths": [], "unit": "code_value",
            "domain": "decoded_P010", "declaredOutcome": "passed", "observed": observed,
            "expected": expected, "containerBitDepth": 10, "sensorSamplesRetained": False})
        record["claims"].extend([
            {"id": "codec-precision", "class": "codec_precision", "statement": "Synthetic P010 ramp preserved.",
             "dependsOn": ["codec-ramp"]},
            {"id": "sensor-precision", "class": "sensor_precision", "statement": "The S23 sensor has ten effective bits.",
             "dependsOn": ["codec-ramp"]},
        ])
        del record["declaredSummary"]
        result = self.assess(record)
        self.assertIn("codec-precision", result["acceptedClaims"])
        self.assertIn("sensor-precision", result["rejectedClaims"])

    def test_tc_p005_02_overlapping_source_revision_change_invalidates_only_affected_observation(self):
        record = deepcopy(self.record)
        record["inspection"]["currentRevision"] = "b" * 40
        record["inspection"]["changedPaths"] = ["app/src/main/java/com/s23log/probe/core/CapturePolicy.kt"]
        del record["declaredSummary"]
        result = self.assess(record)
        self.assertEqual("failed", result["status"])
        self.assertEqual("invalid", result["observations"]["cadence-series"]["outcome"])
        self.assertEqual("exploratory", result["observations"]["chart-measurement"]["outcome"])
        self.assertIn("chart-exploration", result["acceptedClaims"])
        self.assertIn("mean-rate", result["rejectedClaims"])
        self.save_case("TC-P005-02", "overlap", record, result)

    def test_tc_p005_02_documentation_only_revision_is_reported_but_does_not_relabel_audit(self):
        record = deepcopy(self.record)
        record["inspection"]["currentRevision"] = "b" * 40
        record["inspection"]["changedPaths"] = ["docs/notes.md"]
        result = self.assess(record)
        self.assertEqual("passed", result["status"], result)
        self.assertEqual(["docs/notes.md"], result["inspection"]["unrelatedChangedPaths"])
        self.assertEqual(self.revision, result["inspection"]["reviewedRevision"])
        self.assertEqual("b" * 40, result["inspection"]["currentRevision"])

    def test_tc_p005_02_unknown_revision_change_without_paths_is_rejected(self):
        record = deepcopy(self.record)
        record["inspection"]["currentRevision"] = "b" * 40
        result = self.assess(record)
        self.assertEqual("failed", result["status"])
        self.assertTrue(any(i["code"] == "source_revision_conflict" for i in result["issues"]))

    def test_tc_p005_03_missing_fixture_provenance_excludes_only_that_fixture(self):
        kinds = ["model", "stock_profile", "movie_reference", "generated_screenshot"]
        for kind in kinds:
            record = deepcopy(self.record)
            record["fixtures"][1]["kind"] = kind
            record["fixtures"][1]["provenance"].pop("owner")
            del record["declaredSummary"]
            result = self.assess(record)
            self.assertEqual("failed", result["status"])
            self.assertIn("mean-rate", result["acceptedClaims"])
            self.assertIn("chart-exploration", result["rejectedClaims"])
            self.save_case("TC-P005-03", kind, record, result)

    def test_tc_p005_03_missing_identity_is_not_a_reproducible_visual_fixture(self):
        record = deepcopy(self.record)
        record["fixtures"][1]["identity"] = ""
        del record["declaredSummary"]
        result = self.assess(record)
        self.assertEqual("failed", result["status"])
        self.assertEqual("invalid", result["observations"]["chart-measurement"]["outcome"])

    def test_tc_p005_04_green_summary_cannot_override_raw_duplicate(self):
        record = deepcopy(self.record)
        record["observations"][0]["declaredOutcome"] = "passed"
        record["declaredSummary"]["observationOutcomes"]["cadence-series"] = "passed"
        record["declaredSummary"]["acceptedClaims"].append("frame-integrity")
        result = self.assess(record)
        self.assertEqual("failed", result["status"])
        self.assertEqual("failed", result["observations"]["cadence-series"]["outcome"])
        self.assertIn("frame-integrity", result["rejectedClaims"])
        self.save_case("TC-P005-04", "green-vs-raw", record, result)

    def test_tc_p005_04_skipped_physical_probe_cannot_be_counted_as_passed(self):
        record = deepcopy(self.record)
        record["environments"].append({"id": "phone", "kind": "physical_s23", "backend": "camera2",
                                       "available": False, "details": "No phone connected"})
        record["claims"].append({"id": "physical", "class": "physical_capture",
                                 "statement": "Physical cadence passed.", "dependsOn": ["cadence-series"]})
        del record["declaredSummary"]
        result = self.assess(record)
        self.assertIn("physical", result["rejectedClaims"])

    def test_tc_p005_04_stale_policy_hash_is_rejected(self):
        record = deepcopy(self.record)
        record["observations"][0]["policySha256"] = "0" * 64
        del record["declaredSummary"]
        result = self.assess(record)
        self.assertEqual("failed", result["status"])
        self.assertEqual("invalid", result["observations"]["cadence-series"]["outcome"])

    def test_tc_p005_05_units_domains_and_values_are_not_interchangeable(self):
        variants = [("us", "sensor_timestamp"), ("ns", "display_encoded"), ("", "sensor_timestamp")]
        for unit, domain in variants:
            record = deepcopy(self.record)
            record["observations"][0].update(unit=unit, domain=domain)
            del record["declaredSummary"]
            result = self.assess(record)
            self.assertEqual("failed", result["status"])
            self.assertEqual("invalid", result["observations"]["cadence-series"]["outcome"])
            self.save_case("TC-P005-05", f"{unit or 'missing'}-{domain}", record, result)

    def test_tc_p005_05_boolean_or_nonfinite_measurements_are_rejected(self):
        for value in (True, float("inf"), float("nan")):
            record = deepcopy(self.record)
            record["observations"][1]["deltaE2000"] = [value]
            del record["declaredSummary"]
            result = self.assess(record)
            self.assertEqual("failed", result["status"])

    def test_tc_p005_05_registry_covers_timing_colour_memory_blur_and_precision_domains(self):
        policies = {p["kind"]: p for p in self.registry["policies"]}
        for kind in ("cadence", "colour", "memory", "geometry", "precision"):
            self.assertIn(kind, policies)
            self.assertTrue(policies[kind]["unit"])
            self.assertTrue(policies[kind]["domain"])

    def test_tc_p005_06_policy_cannot_be_loosened_in_place(self):
        changed = deepcopy(self.registry)
        target = policy(changed, "cadence.sensor-timestamp.v1")
        target["thresholds"]["nominalFpsToleranceFraction"]["value"] = 0.3
        with self.assertRaisesRegex(ValueError, "changed without a versioned successor"):
            measurements.validate_registry(changed, previous=self.registry)
        self.save_case("TC-P005-06", "in-place-threshold", changed, {"rejected": True})

    def test_tc_p005_06_reviewed_successor_preserves_original_policy(self):
        changed = deepcopy(self.registry)
        old = policy(changed, "cadence.sensor-timestamp.v1")
        successor = deepcopy(old)
        successor.update(id="cadence.sensor-timestamp.v2", version=2,
                         supersedes=old["id"], review={"reviewer": "measurement owner",
                         "reason": "Authored positive-control revision", "validationEvidence": ["TC-P005-06"]})
        successor["thresholds"]["nominalFpsToleranceFraction"]["value"] = 0.04
        successor["history"].append({"version": 2, "reason": "Authored positive-control revision",
                                     "reviewer": "measurement owner", "validationEvidence": ["TC-P005-06"]})
        changed["policies"].append(successor)
        measurements.validate_registry(changed, previous=self.registry)
        self.assertEqual(0.03, policy(changed, old["id"])["thresholds"]["nominalFpsToleranceFraction"]["value"])

    def test_tc_p005_06_successor_needs_review_and_validation_evidence(self):
        changed = deepcopy(self.registry)
        old = policy(changed, "latency.render.v1")
        successor = deepcopy(old)
        successor.update(id="latency.render.v2", version=2, supersedes=old["id"], review=None)
        successor["history"].append({"version": 2, "reason": "", "reviewer": "", "validationEvidence": []})
        changed["policies"].append(successor)
        with self.assertRaisesRegex(ValueError, "review"):
            measurements.validate_registry(changed, previous=self.registry)

    def test_tc_p005_07_assessment_preserves_unrelated_collaborator_bytes_and_git_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
            (root / "tracked.txt").write_text("original")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            collaborator = root / "collaborator.bin"
            collaborator.write_bytes(b"keep\x00\xff")
            index_before = hashlib.sha256((root / ".git/index").read_bytes()).hexdigest()
            result = measurements.assess(self.record, self.registry)
            self.assertEqual("passed", result["status"])
            self.assertEqual(b"keep\x00\xff", collaborator.read_bytes())
            self.assertEqual(index_before, hashlib.sha256((root / ".git/index").read_bytes()).hexdigest())
            self.save_case("TC-P005-07", "collaborator-preserved", self.record,
                           {"status": result["status"], "bytesPreserved": True, "indexPreserved": True})

    def test_tc_p005_07_expected_head_mismatch_is_reported_not_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
            (root / "x").write_text("x")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            with self.assertRaisesRegex(ValueError, "Expected HEAD"):
                measurements.check_head(root, "0" * 40)
            self.assertEqual(head, subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip())

    def test_tc_p005_07_head_move_during_assessment_is_rejected(self):
        with patch.object(measurements, "current_head", side_effect=["a" * 40, "b" * 40]):
            with self.assertRaisesRegex(ValueError, "HEAD moved"):
                measurements.assess(self.record, self.registry, root=ROOT, expected_head="a" * 40)

    def test_tc_p005_08_isolated_cli_reproduces_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            registry = folder / "registry.json"
            record = folder / "record.json"
            registry.write_text(json.dumps(self.registry))
            record.write_text(json.dumps(self.record))
            env = {"PATH": os.environ["PATH"], "HOME": str(folder / "home"), "PYTHONDONTWRITEBYTECODE": "1"}
            Path(env["HOME"]).mkdir()
            result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/measurements.py"),
                                     "assess", "--registry", str(registry), "--input", str(record)],
                                    env=env, text=True, capture_output=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual("failed", report["observations"]["cadence-series"]["outcome"])
            self.assertEqual("exploratory", report["observations"]["chart-measurement"]["outcome"])

    def test_tc_p005_08_missing_registry_is_a_concrete_prerequisite(self):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / "record.json"
            record.write_text(json.dumps(self.record))
            result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/measurements.py"),
                                     "assess", "--registry", str(Path(directory) / "missing.json"),
                                     "--input", str(record)], text=True, capture_output=True, timeout=30)
            self.assertEqual(1, result.returncode)
            self.assertIn("Missing prerequisite file", result.stderr)
            self.save_case("TC-P005-08", "missing-registry", self.record, {"stderr": result.stderr})

    def test_summary_only_p003_adapter_preserves_average_but_not_per_frame_integrity(self):
        attempt = {
            "schemaVersion": 1, "kind": "ordinary-recording-evidence", "attemptId": "attempt",
            "sourceRevision": self.revision,
            "context": {"device": {"model": "sdk_gphone64_x86_64", "fingerprint": "fixture"},
                        "selectedMode": {"fps": 30}},
            "observations": {"output_validation-observation": json.dumps({"facts": {"verification": {
                "measuredFps": 30.0, "sampleSpanUs": 2_000_000, "samples": 61,
                "largeFrameIntervals": 0, "cadenceToleranceFraction": 0.03,
                "cadenceMinimumSpanUs": 2_000_000}}})},
            "classification": {"physicalCameraCertified": False},
        }
        record = measurements.adapt_p003(attempt, self.registry)
        result = measurements.assess(record, self.registry)
        observation = next(iter(result["observations"].values()))
        self.assertEqual("passed", observation["averageOutcome"])
        self.assertEqual("inconclusive", observation["outcome"])
        self.assertIn("average-cadence", result["acceptedClaims"])
        self.assertIn("per-frame-integrity", result["rejectedClaims"])

    def test_known_illuminant_and_traceable_instrument_can_reach_calibrated_colour(self):
        record = deepcopy(self.record)
        colour = record["observations"][1]
        colour.update(illuminant="D65 measured", instrument="traceable spectrophotometer",
                      calibrationTrace="certificate-authored-fixture", declaredOutcome="passed")
        record["declaredSummary"]["observationOutcomes"]["chart-measurement"] = "passed"
        record["declaredSummary"]["acceptedClaims"] = ["chart-certified", "chart-exploration", "mean-rate"]
        result = self.assess(record)
        self.assertEqual("passed", result["status"], result)
        self.assertIn("chart-certified", result["acceptedClaims"])

    def test_outliers_are_retained_in_colour_statistics(self):
        record = deepcopy(self.record)
        colour = record["observations"][1]
        colour["deltaE2000"] = [1, 1, 1, 20]
        result = self.assess(record)
        observed = result["observations"]["chart-measurement"]
        self.assertEqual(20, observed["maximumDeltaE2000"])
        self.assertEqual(4, observed["sampleCount"])

    def test_registry_and_budget_template_validate(self):
        measurements.validate_registry(self.registry)
        template = json.loads((ROOT / "docs/MEASUREMENT_BUDGET_TEMPLATE.json").read_text())
        measurements.validate_budget_template(template, self.registry)

    def test_registry_hash_binds_record(self):
        record = deepcopy(self.record)
        record["registrySha256"] = "f" * 64
        result = self.assess(record)
        self.assertEqual("failed", result["status"])
        self.assertTrue(any(i["code"] == "registry_identity_mismatch" for i in result["issues"]))


if __name__ == "__main__":
    unittest.main()
