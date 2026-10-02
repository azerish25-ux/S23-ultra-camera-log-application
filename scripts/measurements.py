#!/usr/bin/env python3
"""P005 measurement registry and uncertainty assessor.

The assessor keeps measurement-record consistency separate from experimental
success. A valid record may contain a failed cadence-integrity result or an
exploratory colour result. It never upgrades emulator/synthetic evidence into a
physical S23 claim, and it never replaces complete samples with a mean.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

OUTCOMES = {"passed", "failed", "exploratory", "inconclusive", "unavailable", "invalid"}
KINDS = {"cadence", "precision", "sensor_precision", "colour", "memory", "latency", "geometry"}
CLAIMS = {"average_cadence", "per_frame_integrity", "codec_precision", "sensor_precision",
          "exploratory_colour", "calibrated_colour", "physical_capture", "scalar_threshold"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def exact_keys(value: dict, required: set[str], context: str, optional: set[str] | None = None) -> None:
    require(isinstance(value, dict), context + " must be an object")
    optional = optional or set()
    missing = required - set(value)
    extra = set(value) - required - optional
    require(not missing, f"{context} missing fields: {', '.join(sorted(missing))}")
    require(not extra, f"{context} has unexpected fields: {', '.join(sorted(extra))}")


def unique(items: list[dict], context: str) -> dict[str, dict]:
    require(isinstance(items, list), context + " must be a list")
    result: dict[str, dict] = {}
    for item in items:
        require(isinstance(item, dict) and text(item.get("id")), context + " needs stable ids")
        require(item["id"] not in result, "Duplicate " + context + " id: " + item["id"])
        result[item["id"]] = item
    return result


def threshold(policy: dict, name: str) -> dict:
    value = policy["thresholds"].get(name)
    require(isinstance(value, dict), f"Missing threshold {policy['id']}:{name}")
    return value


def validate_registry(registry: dict, previous: dict | None = None) -> dict[str, dict]:
    exact_keys(registry, {"schemaVersion", "phase", "registryId", "implementationBaseRevision", "scope", "policies"}, "registry")
    require(registry["schemaVersion"] == 1 and registry["phase"] == "P005", "Unsupported measurement registry")
    require(text(registry["registryId"]) and HEX40.fullmatch(registry["implementationBaseRevision"] or ""),
            "Registry needs an exact implementation base revision")
    require(text(registry["scope"]), "Registry scope is required")
    policies = unique(registry["policies"], "policy")
    for item in policies.values():
        exact_keys(item, {"id", "version", "kind", "unit", "domain", "samplingProcedure", "statisticalScope",
                          "uncertaintySources", "thresholds", "calibration", "supersedes", "review", "history"},
                   "policy " + item["id"])
        require(re.fullmatch(r"[a-z0-9_.-]+\.v[0-9]+", item["id"]) is not None, "Invalid policy id")
        require(type(item["version"]) is int and item["version"] > 0 and item["kind"] in KINDS, "Invalid policy kind/version")
        require(all(text(item[k]) for k in ("unit", "domain", "samplingProcedure", "statisticalScope")),
                "Policy needs units, domain and sampling scope")
        require(isinstance(item["uncertaintySources"], list) and item["uncertaintySources"] and
                all(text(v) for v in item["uncertaintySources"]), "Policy uncertainty sources are required")
        require(isinstance(item["thresholds"], dict), "Policy thresholds must be an object")
        for name, gate in item["thresholds"].items():
            require(text(name), "Threshold needs an id")
            exact_keys(gate, {"value", "unit", "domain", "operator", "provisional"}, "threshold " + name)
            require(finite(gate["value"]) and text(gate["unit"]) and text(gate["domain"]), "Threshold needs finite value/unit/domain")
            require(gate["operator"] in {"le", "ge", "eq"} and type(gate["provisional"]) is bool,
                    "Invalid threshold operator/status")
        exact_keys(item["calibration"], {"required", "inputs"}, "calibration " + item["id"])
        require(type(item["calibration"]["required"]) is bool and isinstance(item["calibration"]["inputs"], list) and
                all(text(v) for v in item["calibration"]["inputs"]), "Invalid calibration contract")
        require(isinstance(item["history"], list) and item["history"], "Policy history is required")
        versions: list[int] = []
        for history in item["history"]:
            exact_keys(history, {"version", "reason", "reviewer", "validationEvidence"}, "policy history")
            require(type(history["version"]) is int and history["version"] > 0 and text(history["reason"]) and
                    text(history["reviewer"]) and isinstance(history["validationEvidence"], list) and
                    history["validationEvidence"] and all(text(v) for v in history["validationEvidence"]),
                    "Policy history needs reason, reviewer and validation evidence")
            versions.append(history["version"])
        require(versions == sorted(set(versions)) and versions[-1] == item["version"], "Policy history/version mismatch")
        if item["supersedes"] is None:
            require(item["version"] == 1 and item["review"] is None, "Initial policy must be version 1 without successor review")
        else:
            require(text(item["supersedes"]) and isinstance(item["review"], dict), "Policy successor needs review")
            exact_keys(item["review"], {"reviewer", "reason", "validationEvidence"}, "policy review")
            require(text(item["review"]["reviewer"]) and text(item["review"]["reason"]) and
                    isinstance(item["review"]["validationEvidence"], list) and item["review"]["validationEvidence"] and
                    all(text(v) for v in item["review"]["validationEvidence"]), "Policy successor review is incomplete")
    if previous is not None:
        old = validate_registry(previous)
        for policy_id, prior in old.items():
            require(policy_id in policies, "Historical policy removed: " + policy_id)
            require(canonical_hash(policies[policy_id]) == canonical_hash(prior),
                    "Policy changed without a versioned successor: " + policy_id)
        for policy_id, item in policies.items():
            if policy_id in old:
                continue
            require(item["supersedes"] in old, "New policy must name a historical predecessor")
            prior = old[item["supersedes"]]
            require(item["version"] == prior["version"] + 1 and item["kind"] == prior["kind"] and
                    item["unit"] == prior["unit"] and item["domain"] == prior["domain"],
                    "Policy successor lineage mismatch")
    return policies


def validate_budget_template(template: dict, registry: dict) -> None:
    validate_registry(registry)
    exact_keys(template, {"schemaVersion", "phase", "templateId", "registryId", "requiredSections", "outcomeVocabulary", "rules"},
               "uncertainty budget template")
    require(template["schemaVersion"] == 1 and template["phase"] == "P005" and template["registryId"] == registry["registryId"],
            "Budget template registry identity mismatch")
    sections = unique(template["requiredSections"], "budget section")
    require(set(sections) == {"identity", "environment", "provenance", "sampling", "uncertainty", "calibration", "claims"},
            "Budget template sections are incomplete")
    for item in sections.values():
        exact_keys(item, {"id", "fields"}, "budget section")
        require(isinstance(item["fields"], list) and item["fields"] and all(text(v) for v in item["fields"]),
                "Budget section fields are required")
    require(set(template["outcomeVocabulary"]) == OUTCOMES, "Budget outcome vocabulary mismatch")
    require(isinstance(template["rules"], list) and len(template["rules"]) >= 6 and all(text(v) for v in template["rules"]),
            "Budget rules are incomplete")


def current_head(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=10).strip()


def check_head(root: Path, expected: str) -> str:
    actual = current_head(root)
    require(actual == expected, f"Expected HEAD {expected}; observed {actual}")
    return actual


def compare(value: float, gate: dict) -> bool:
    limit = float(gate["value"])
    return {"le": value <= limit, "ge": value >= limit, "eq": value == limit}[gate["operator"]]


def cadence_assessment(observation: dict, policy: dict) -> dict:
    nominal = observation.get("nominalFps")
    require(finite(nominal) and float(nominal) > 0, "Cadence needs a positive nominalFps")
    nominal = float(nominal)
    tolerance = float(threshold(policy, "nominalFpsToleranceFraction")["value"])
    minimum_span = float(threshold(policy, "minimumSpan")["value"])
    multiplier = float(threshold(policy, "largeGapMultiplier")["value"])
    units_per_second = 1_000_000_000.0 if policy["unit"] == "ns" else 1_000_000.0
    expected_interval = units_per_second / nominal
    if "summaryOnly" in observation:
        summary = observation["summaryOnly"]
        exact_keys(summary, {"measuredFps", "duration", "largeIntervals", "frames"}, "summary-only cadence")
        require(all(finite(summary[k]) for k in ("measuredFps", "duration", "largeIntervals", "frames")),
                "Summary cadence needs finite values")
        mean = float(summary["measuredFps"])
        duration = float(summary["duration"])
        average = duration >= minimum_span and abs(mean / nominal - 1.0) <= tolerance
        return {"outcome": "inconclusive", "averageOutcome": "passed" if average else "failed",
                "timingOutcome": "inconclusive", "contentOutcome": "unavailable", "meanFps": mean,
                "duration": duration, "frames": int(summary["frames"]), "largeIntervalIndices": [],
                "invalidTimestampIndices": [], "duplicateContentIndices": [], "intervals": [],
                "completeSequenceRetained": False,
                "reason": "Aggregate cadence retained, but per-frame timestamps/content identifiers are unavailable."}
    timestamps = observation.get("timestamps")
    require(isinstance(timestamps, list) and len(timestamps) >= 2 and all(finite(v) for v in timestamps),
            "Cadence needs at least two finite timestamps")
    resolution = observation.get("timestampResolution")
    require(finite(resolution) and float(resolution) > 0, "Timestamp resolution is required")
    values = [float(v) for v in timestamps]
    intervals = [b - a for a, b in zip(values, values[1:])]
    invalid = [i + 1 for i, value in enumerate(intervals) if value <= 0]
    duration = values[-1] - values[0]
    mean = (len(values) - 1) * units_per_second / duration if duration > 0 and not invalid else None
    average = mean is not None and duration >= minimum_span and abs(mean / nominal - 1.0) <= tolerance
    large = [i + 1 for i, value in enumerate(intervals) if value > expected_interval * multiplier]
    timing = average and not invalid and not large
    identifiers = observation.get("frameIdentifiers")
    duplicates: list[int] = []
    if identifiers is None:
        content = "unavailable"
    else:
        require(isinstance(identifiers, list) and len(identifiers) == len(values),
                "Frame identifiers must match every timestamp")
        seen: set[str] = set()
        for index, identifier in enumerate(identifiers):
            key = json.dumps(identifier, sort_keys=True, allow_nan=False)
            if key in seen:
                duplicates.append(index)
            seen.add(key)
        content = "failed" if duplicates else "passed"
    if not timing or content == "failed":
        outcome = "failed"
    elif content == "unavailable":
        outcome = "inconclusive"
    else:
        outcome = "passed"
    return {"outcome": outcome, "averageOutcome": "passed" if average else "failed",
            "timingOutcome": "passed" if timing else "failed", "contentOutcome": content,
            "meanFps": mean, "duration": duration, "frames": len(values),
            "largeIntervalIndices": large, "invalidTimestampIndices": invalid,
            "duplicateContentIndices": duplicates, "intervals": intervals,
            "timestampResolution": float(resolution), "timestampResolutionUnit": policy["unit"],
            "completeSequenceRetained": True,
            "reason": "Every interval and supplied content identifier was evaluated; no outlier was discarded."}


def precision_assessment(observation: dict, policy: dict, environment: dict) -> dict:
    if policy["kind"] == "sensor_precision":
        calibrated = (environment["kind"] == "physical_s23" and environment["available"] is True and
                      observation.get("sensorSamplesRetained") is True and text(observation.get("calibrationTrace")))
        return {"outcome": "passed" if calibrated else "unavailable", "sensorOutcome": "passed" if calibrated else "unavailable",
                "codecOutcome": "unavailable", "physicalQualified": bool(calibrated),
                "reason": "Effective sensor precision requires retained physical samples and calibration."}
    observed = observation.get("observed")
    expected = observation.get("expected")
    require(isinstance(observed, list) and isinstance(expected, list) and len(observed) == len(expected) and len(observed) >= 600 and
            all(finite(v) for v in observed + expected), "Codec precision needs at least 600 paired finite samples")
    errors = [abs(float(a) - float(b)) for a, b in zip(observed, expected)]
    mean = sum(errors) / len(errors)
    peak = max(errors)
    levels = len({round(float(v)) for v in observed})
    passed = (compare(mean, threshold(policy, "meanCodeError")) and
              compare(peak, threshold(policy, "peakCodeError")) and
              compare(levels, threshold(policy, "minimumLevels")))
    return {"outcome": "passed" if passed else "failed", "codecOutcome": "passed" if passed else "failed",
            "sensorOutcome": "unavailable", "meanCodeError": mean, "peakCodeError": peak,
            "distinguishableLevels": levels, "sampleCount": len(errors), "errors": errors,
            "containerBitDepth": observation.get("containerBitDepth"), "sensorSamplesRetained": observation.get("sensorSamplesRetained") is True,
            "physicalQualified": False,
            "reason": "Decoded codec samples were compared; no sensor precision is inferred."}


def colour_assessment(observation: dict, policy: dict) -> dict:
    samples = observation.get("deltaE2000")
    require(isinstance(samples, list) and samples and all(finite(v) and float(v) >= 0 for v in samples),
            "Colour measurement needs non-negative finite patch errors")
    values = [float(v) for v in samples]
    mean = sum(values) / len(values)
    maximum = max(values)
    calibrated = all(text(observation.get(name)) for name in ("illuminant", "instrument", "chartId", "calibrationTrace"))
    numerical = compare(mean, threshold(policy, "meanDeltaE2000")) and compare(maximum, threshold(policy, "maximumDeltaE2000"))
    outcome = ("passed" if numerical else "failed") if calibrated else "exploratory"
    return {"outcome": outcome, "calibrated": calibrated, "numericThresholdOutcome": "passed" if numerical else "failed",
            "meanDeltaE2000": mean, "maximumDeltaE2000": maximum, "sampleCount": len(values),
            "patchErrors": values, "outliersRetained": True, "physicalQualified": False,
            "reason": "Patch statistics retained; calibration scope is explicit." if calibrated else
                      "Unknown illuminant/instrument/calibration keeps the result exploratory."}


def scalar_assessment(observation: dict, policy: dict) -> dict:
    value = observation.get("value")
    require(finite(value), "Scalar measurement needs a finite non-Boolean value")
    require(len(policy["thresholds"]) == 1, "Scalar policy must have one threshold")
    gate = next(iter(policy["thresholds"].values()))
    passed = compare(float(value), gate)
    return {"outcome": "passed" if passed else "failed", "value": float(value),
            "threshold": gate, "physicalQualified": False,
            "reason": "Scalar threshold evaluated with exact unit and domain."}


def issue(target: list[dict], code: str, subject: str, detail: str) -> None:
    target.append({"code": code, "subject": subject, "detail": detail})


def assess(record: dict, registry: dict, *, root: Path | None = None, expected_head: str | None = None) -> dict:
    policies = validate_registry(registry)
    start: str | None = None
    if root is not None and expected_head is not None:
        start = check_head(Path(root), expected_head)
    issues: list[dict] = []
    report: dict[str, Any] = {"status": "failed", "measurementId": record.get("measurementId"),
                              "registrySha256": canonical_hash(registry), "observations": {},
                              "acceptedClaims": [], "rejectedClaims": [], "claimReasons": {},
                              "researchQuestions": record.get("researchQuestions", []), "issues": issues,
                              "physicalCameraCertified": False}
    required = {"schemaVersion", "measurementId", "sourceRevision", "registrySha256", "inspection", "environments",
                "fixtures", "observations", "claims", "researchQuestions"}
    try:
        exact_keys(record, required, "measurement record", optional={"declaredSummary"})
        require(record["schemaVersion"] == 1 and text(record["measurementId"]) and HEX40.fullmatch(record["sourceRevision"] or ""),
                "Invalid measurement identity")
        require(record["registrySha256"] == canonical_hash(registry), "Registry identity mismatch")
    except (ValueError, TypeError) as error:
        code = "registry_identity_mismatch" if "Registry identity" in str(error) else "record_invalid"
        issue(issues, code, record.get("measurementId", "record"), str(error))
    inspection = record.get("inspection", {})
    overlapping_changes: set[str] = set()
    unrelated_changes: list[str] = []
    inspected_paths: set[str] = set()
    try:
        exact_keys(inspection, {"revision", "currentRevision", "inspectedPaths", "changedPaths"}, "inspection")
        require(HEX40.fullmatch(inspection["revision"] or "") and HEX40.fullmatch(inspection["currentRevision"] or ""),
                "Inspection revisions must be exact")
        require(inspection["revision"] == record["sourceRevision"], "Inspection/source revision mismatch")
        require(isinstance(inspection["inspectedPaths"], list) and isinstance(inspection["changedPaths"], list) and
                all(text(v) for v in inspection["inspectedPaths"] + inspection["changedPaths"]), "Invalid inspection paths")
        inspected_paths = set(inspection["inspectedPaths"])
        changed = set(inspection["changedPaths"])
        if inspection["currentRevision"] != inspection["revision"]:
            if not changed:
                issue(issues, "source_revision_conflict", "inspection", "Revision changed without an incremental changed-path record")
            overlapping_changes = changed & inspected_paths
            unrelated_changes = sorted(changed - inspected_paths)
    except (ValueError, TypeError) as error:
        issue(issues, "source_revision_conflict", "inspection", str(error))
    report["inspection"] = {"reviewedRevision": inspection.get("revision"), "currentRevision": inspection.get("currentRevision"),
                            "overlappingChangedPaths": sorted(overlapping_changes), "unrelatedChangedPaths": unrelated_changes}
    fixtures: dict[str, dict] = {}
    invalid_fixtures: set[str] = set()
    try:
        fixtures = unique(record.get("fixtures", []), "fixture")
        for fixture_id, fixture in fixtures.items():
            try:
                exact_keys(fixture, {"id", "kind", "identity", "provenance"}, "fixture " + fixture_id)
                require(text(fixture["kind"]) and HEX64.fullmatch(fixture["identity"] or ""), "Fixture identity is missing")
                exact_keys(fixture["provenance"], {"origin", "owner", "acquiredAt", "permittedUse"}, "fixture provenance")
                require(all(text(fixture["provenance"][key]) for key in ("origin", "owner", "acquiredAt", "permittedUse")),
                        "Fixture acquisition context/ownership is incomplete")
            except (ValueError, TypeError) as error:
                invalid_fixtures.add(fixture_id)
                issue(issues, "missing_provenance", fixture_id, str(error))
    except (ValueError, TypeError) as error:
        issue(issues, "missing_provenance", "fixtures", str(error))
    environments: dict[str, dict] = {}
    invalid_environments: set[str] = set()
    try:
        environments = unique(record.get("environments", []), "environment")
        for environment_id, environment in environments.items():
            try:
                exact_keys(environment, {"id", "kind", "backend", "available", "details"}, "environment " + environment_id)
                require(all(text(environment[key]) for key in ("kind", "backend", "details")) and type(environment["available"]) is bool,
                        "Invalid environment identity")
            except (ValueError, TypeError) as error:
                invalid_environments.add(environment_id)
                issue(issues, "environment_invalid", environment_id, str(error))
    except (ValueError, TypeError) as error:
        issue(issues, "environment_invalid", "environments", str(error))
    observations: dict[str, dict] = {}
    try:
        raw_observations = unique(record.get("observations", []), "observation")
    except (ValueError, TypeError) as error:
        issue(issues, "observation_invalid", "observations", str(error))
        raw_observations = {}
    common = {"id", "metricId", "policySha256", "fixtureId", "environmentId", "sourcePaths", "unit", "domain", "declaredOutcome"}
    for observation_id, observation in raw_observations.items():
        result: dict[str, Any] = {"outcome": "invalid", "reason": "Observation was not evaluated."}
        try:
            require(common <= set(observation), "Observation common fields are incomplete")
            require(observation["metricId"] in policies, "Unknown measurement policy")
            policy = policies[observation["metricId"]]
            require(observation["policySha256"] == canonical_hash(policy), "Measurement policy identity changed")
            require(observation["unit"] == policy["unit"] and observation["domain"] == policy["domain"] and
                    text(observation["unit"]) and text(observation["domain"]), "Measurement unit/domain mismatch")
            require(observation["declaredOutcome"] in OUTCOMES, "Unknown declared outcome")
            require(observation["fixtureId"] in fixtures and observation["fixtureId"] not in invalid_fixtures,
                    "Observation fixture has missing provenance")
            require(observation["environmentId"] in environments and observation["environmentId"] not in invalid_environments,
                    "Observation environment is invalid")
            require(isinstance(observation["sourcePaths"], list) and all(text(v) for v in observation["sourcePaths"]),
                    "Observation source paths are invalid")
            source_paths = set(observation["sourcePaths"])
            require(source_paths <= inspected_paths or not source_paths, "Observation uses uninspected source paths")
            require(not (source_paths & overlapping_changes), "Affected source changed after inspection")
            if policy["kind"] == "cadence":
                result = cadence_assessment(observation, policy)
            elif policy["kind"] in {"precision", "sensor_precision"}:
                result = precision_assessment(observation, policy, environments[observation["environmentId"]])
            elif policy["kind"] == "colour":
                result = colour_assessment(observation, policy)
            else:
                result = scalar_assessment(observation, policy)
            result.update(metricId=policy["id"], policySha256=canonical_hash(policy), unit=policy["unit"], domain=policy["domain"],
                          fixtureId=observation["fixtureId"], environmentId=observation["environmentId"])
            if observation["declaredOutcome"] != result["outcome"]:
                issue(issues, "contradictory_outcome", observation_id,
                      f"Declared {observation['declaredOutcome']} contradicts computed {result['outcome']}")
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            issue(issues, "observation_invalid", observation_id, str(error))
            result = {"outcome": "invalid", "reason": str(error)}
        observations[observation_id] = result
    report["observations"] = observations
    accepted: list[str] = []
    rejected: list[str] = []
    claim_reasons: dict[str, str] = {}
    try:
        raw_claims = unique(record.get("claims", []), "claim")
    except (ValueError, TypeError) as error:
        issue(issues, "claim_invalid", "claims", str(error))
        raw_claims = {}
    for claim_id, claim in raw_claims.items():
        try:
            exact_keys(claim, {"id", "class", "statement", "dependsOn"}, "claim " + claim_id)
            require(claim["class"] in CLAIMS and text(claim["statement"]) and isinstance(claim["dependsOn"], list) and
                    claim["dependsOn"] and all(dep in observations for dep in claim["dependsOn"]), "Invalid claim contract")
            deps = [observations[dep] for dep in claim["dependsOn"]]
            if claim["class"] == "average_cadence":
                supported = all(dep.get("averageOutcome") == "passed" and dep.get("outcome") != "invalid" for dep in deps)
                reason = "Complete/declared aggregate mean is within its policy; this does not establish frame integrity."
            elif claim["class"] == "per_frame_integrity":
                supported = all(dep.get("outcome") == "passed" and dep.get("completeSequenceRetained") is True for dep in deps)
                reason = "Requires complete timestamps and unique changing-content identifiers."
            elif claim["class"] == "codec_precision":
                supported = all(dep.get("codecOutcome") == "passed" for dep in deps)
                reason = "Codec/arithmetic precision is limited to the decoded fixture domain."
            elif claim["class"] == "sensor_precision":
                supported = all(dep.get("sensorOutcome") == "passed" and dep.get("physicalQualified") is True for dep in deps)
                reason = "Effective sensor precision requires a physical calibrated protocol."
            elif claim["class"] == "exploratory_colour":
                supported = all(dep.get("outcome") in {"exploratory", "passed", "failed"} and "meanDeltaE2000" in dep for dep in deps)
                reason = "Patch numbers may remain exploratory even when calibration is incomplete."
            elif claim["class"] == "calibrated_colour":
                supported = all(dep.get("outcome") == "passed" and dep.get("calibrated") is True for dep in deps)
                reason = "Calibrated colour requires known illuminant, instrument, chart and calibration trace."
            elif claim["class"] == "physical_capture":
                supported = all(dep.get("outcome") == "passed" and dep.get("physicalQualified") is True for dep in deps)
                reason = "No software, emulator or unavailable probe can certify physical capture."
            else:
                supported = all(dep.get("outcome") == "passed" for dep in deps)
                reason = "Scalar threshold requires valid unit/domain and passing measurements."
            (accepted if supported else rejected).append(claim_id)
            claim_reasons[claim_id] = reason
        except (ValueError, TypeError, KeyError) as error:
            rejected.append(claim_id)
            claim_reasons[claim_id] = str(error)
            issue(issues, "claim_invalid", claim_id, str(error))
    report["acceptedClaims"] = sorted(accepted)
    report["rejectedClaims"] = sorted(rejected)
    report["claimReasons"] = claim_reasons
    questions = record.get("researchQuestions", [])
    if not isinstance(questions, list) or not all(text(v) for v in questions):
        issue(issues, "record_invalid", "researchQuestions", "Research questions must be explicit text")
        report["researchQuestions"] = []
    declared = record.get("declaredSummary")
    if declared is not None:
        try:
            exact_keys(declared, {"observationOutcomes", "acceptedClaims"}, "declared summary")
            computed = {name: value["outcome"] for name, value in observations.items()}
            require(declared["observationOutcomes"] == computed, "Green summary contradicts individual observation outcomes")
            require(sorted(declared["acceptedClaims"]) == report["acceptedClaims"], "Green summary contradicts accepted claims")
        except (ValueError, TypeError) as error:
            issue(issues, "contradictory_summary", "declaredSummary", str(error))
    report["status"] = "passed" if not issues else "failed"
    if start is not None:
        require(current_head(Path(root)) == start, "HEAD moved during measurement assessment")
    return report


def adapt_p003(report: dict, registry: dict) -> dict:
    policies = validate_registry(registry)
    require(report.get("kind") == "ordinary-recording-evidence" and report.get("schemaVersion") == 1,
            "Only ordinary P003 recording reports are supported by this adapter")
    revision = report.get("sourceRevision")
    require(HEX40.fullmatch(revision or ""), "P003 report lacks exact source revision")
    observations = report.get("observations", {})
    raw = observations.get("output_validation-observation")
    require(text(raw), "P003 report lacks output-validation observation")
    verification = json.loads(raw)["facts"]["verification"]
    cadence = policies["cadence.muxed-presentation.v1"]
    model = report.get("context", {}).get("device", {}).get("model", "unknown")
    environment_kind = "emulator" if "sdk" in model.lower() or "emu" in model.lower() else "device_report"
    measured = float(verification["measuredFps"])
    duration = int(verification["sampleSpanUs"])
    frames = int(verification["samples"])
    nominal = int(report["context"]["selectedMode"]["fps"])
    average = (duration >= threshold(cadence, "minimumSpan")["value"] and
               abs(measured / nominal - 1.0) <= threshold(cadence, "nominalFpsToleranceFraction")["value"])
    fixture_id = "p003-report"
    observation_id = "muxed-cadence-summary"
    return {
        "schemaVersion": 1,
        "measurementId": "P005-from-" + str(report.get("attemptId")),
        "sourceRevision": revision,
        "registrySha256": canonical_hash(registry),
        "inspection": {"revision": revision, "currentRevision": revision,
                       "inspectedPaths": ["app/src/main/java/com/s23log/probe/core/RecordingEvidence.kt"], "changedPaths": []},
        "environments": [{"id": "p003-environment", "kind": environment_kind, "backend": "ordinary-recording-report",
                          "available": True, "details": "Adapted from an existing P003 report; no new phone execution."}],
        "fixtures": [{"id": fixture_id, "kind": "generated_application_report", "identity": canonical_hash(report),
                      "provenance": {"origin": "p003-attempt:" + str(report.get("attemptId")),
                                     "owner": "repository application output", "acquiredAt": "2026-10-02",
                                     "permittedUse": "diagnostic validation and private comparison"}}],
        "observations": [{"id": observation_id, "metricId": cadence["id"], "policySha256": canonical_hash(cadence),
                          "fixtureId": fixture_id, "environmentId": "p003-environment",
                          "sourcePaths": ["app/src/main/java/com/s23log/probe/core/RecordingEvidence.kt"],
                          "unit": cadence["unit"], "domain": cadence["domain"], "declaredOutcome": "inconclusive",
                          "nominalFps": nominal,
                          "summaryOnly": {"measuredFps": measured, "duration": duration,
                                          "largeIntervals": int(verification.get("largeFrameIntervals", 0)), "frames": frames}}],
        "claims": [
            {"id": "average-cadence", "class": "average_cadence",
             "statement": "The report's aggregate muxed cadence is within the registered average-rate policy.",
             "dependsOn": [observation_id]},
            {"id": "per-frame-integrity", "class": "per_frame_integrity",
             "statement": "Every recorded content frame is unique and cadence-integral.",
             "dependsOn": [observation_id]},
        ],
        "researchQuestions": ["What does the complete packet/content sequence establish under the P005 integrity protocol?"],
        "declaredSummary": {"observationOutcomes": {observation_id: "inconclusive"},
                            "acceptedClaims": ["average-cadence"] if average else []},
    }


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise ValueError("Missing prerequisite file: " + str(path))
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid JSON prerequisite " + str(path) + ": " + str(error)) from error
    require(isinstance(value, dict), "JSON prerequisite must be an object: " + str(path))
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    registry_parser = sub.add_parser("validate-registry")
    registry_parser.add_argument("--registry", type=Path, default=Path(__file__).resolve().parents[1] / "docs/MEASUREMENT_REGISTRY.json")
    registry_parser.add_argument("--previous-registry", type=Path)
    registry_parser.add_argument("--budget-template", type=Path, default=Path(__file__).resolve().parents[1] / "docs/MEASUREMENT_BUDGET_TEMPLATE.json")
    registry_parser.add_argument("--expected-head")
    registry_parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    assess_parser = sub.add_parser("assess")
    assess_parser.add_argument("--registry", type=Path, required=True)
    assess_parser.add_argument("--input", type=Path, required=True)
    assess_parser.add_argument("--expected-head")
    assess_parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    adapt_parser = sub.add_parser("adapt-p003")
    adapt_parser.add_argument("--registry", type=Path, required=True)
    adapt_parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        registry = read_json(args.registry)
        if args.command == "validate-registry":
            previous = read_json(args.previous_registry) if args.previous_registry else None
            policies = validate_registry(registry, previous=previous)
            validate_budget_template(read_json(args.budget_template), registry)
            if args.expected_head:
                check_head(args.root, args.expected_head)
            print(json.dumps({"status": "passed", "phase": "P005", "registryId": registry["registryId"],
                              "registrySha256": canonical_hash(registry), "policies": len(policies),
                              "physicalCameraCertified": False}, indent=2, allow_nan=False))
            return 0
        if args.command == "adapt-p003":
            print(json.dumps(adapt_p003(read_json(args.input), registry), indent=2, allow_nan=False))
            return 0
        report = assess(read_json(args.input), registry, root=args.root if args.expected_head else None,
                        expected_head=args.expected_head)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if report["status"] == "passed" else 1
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as error:
        print("Measurement verification failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
