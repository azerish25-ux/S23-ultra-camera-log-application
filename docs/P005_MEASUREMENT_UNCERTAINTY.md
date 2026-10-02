# P005 — measurement identity, uncertainty, and per-frame integrity

Active phase: **P005**, including **TC-P005-01 through TC-P005-08**. The
[Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. P004's accepted
software baseline is the entry gate; this phase does not change the Android app,
camera paths, build pins, numerical image-processing thresholds, or preserved
directive package.

## Purpose

P005 prevents a useful number from silently becoming a stronger claim than its
measurement supports. The implementation keeps these distinctions explicit:

- average cadence versus every-frame timing and changing-content integrity;
- container/codec bit depth versus effective physical sensor precision;
- exploratory chart numbers versus calibrated colorimetric error;
- source-plane, output-plane, encoded-value, scene-value, and elapsed-time domains;
- a consistent evidence record versus success of every contained experiment.

The [measurement registry](MEASUREMENT_REGISTRY.json) contains eight versioned,
provisional policies for sensor timestamps, muxed presentation timestamps, P010
codec precision, physical sensor precision, chart colour error, memory, render
latency, and output-plane blur. Each policy declares units, domain, complete
sampling procedure, statistical scope, uncertainty sources, calibration inputs,
thresholds where applicable, and immutable revision history.

The [uncertainty-budget template](MEASUREMENT_BUDGET_TEMPLATE.json) defines the
minimum identity, environment, provenance, sampling, uncertainty, calibration,
and claim sections required for a reproducible result. Unknown uncertainty stays
unknown; it is never recorded as zero.

## Executable assessor

`scripts/measurements.py` validates the registry and assesses versioned measurement
records. It is standard-library-only, read-only, and supports isolated execution.
A record binds:

- exact source and inspection revisions, inspected paths, and incremental changes;
- fixture identity, origin, owner, acquisition date, and permitted use;
- environment/backend identity and availability;
- exact policy and registry hashes;
- measurement unit/domain, complete samples, and declared outcome;
- proposed claims and the observations on which they depend;
- unresolved research questions.

A valid assessment can contain a failed measurement. `status=passed` means the
record is internally truthful and reproducible, not that every scientific result
passed. Unsupported claims are rejected without deleting legitimate narrower
results or open questions.

### Cadence

For a complete cadence series, every timestamp and adjacent interval is retained.
The existing project policy is preserved: average rate within 3%, a minimum two
second span, and a large-gap boundary at 1.5 nominal intervals. A changing-content
protocol must also provide one identifier per frame before content integrity can
pass. Duplicate content fails per-frame integrity even when the average rate is
exactly correct.

Aggregate-only P003 recording reports can be adapted with `adapt-p003`. Their mean
cadence may remain useful, but per-frame integrity is `inconclusive` because the
report does not contain the complete timestamp/content sequence. This is an
explicit limitation rather than a fabricated pass.

### Precision

The P010 policy retains every decoded ramp error and the existing limits: mean
code error at most 0.75, peak error at most two code values, and at least 600
distinguishable levels. Passing this policy is codec/arithmetic evidence only.
Effective sensor precision requires retained physical S23 samples, calibration,
exposure/noise context, and physical-device identity. A ten-bit label, decoded
synthetic ramp, emulator result, or unavailable backend cannot satisfy that claim.

### Colour

Every chart patch error is retained. The current project policy uses provisional
mean and maximum ΔE2000 gates only when the illuminant, instrument, chart, and
calibration trace are known. Missing calibration does not discard the numbers;
it keeps them exploratory and blocks calibrated-colour certification. No image
processing or profile acceptance behaviour is changed by this host assessor.

## Registry revision rule

A policy is immutable once evidence references its hash. A threshold change must
be a new policy id/version that keeps the old policy, names its predecessor,
records reviewer and rationale, and cites renewed validation evidence. Rewriting
an existing limit after seeing a failure is rejected even when the new JSON is
otherwise well-formed.

## Commands

```sh
python3 scripts/measurements.py validate-registry \
  --expected-head "$(git rev-parse HEAD)"

python3 scripts/measurements.py assess \
  --registry docs/MEASUREMENT_REGISTRY.json \
  --input /path/to/measurement-record.json

python3 scripts/measurements.py adapt-p003 \
  --registry docs/MEASUREMENT_REGISTRY.json \
  --input /path/to/recording-attempt.json > measurement-record.json

S23_P005_EVIDENCE_DIR=/tmp/P005-cases \
  python3 -m unittest discover -s scripts/tests -p test_measurements.py -v
```

`assess` and `validate-registry` can also bind execution to an expected Git HEAD.
They never reset, stage, clean, or overwrite repository files. A missing registry,
fixture, tool, or source identity produces a concrete failure.

## Acceptance cases and negative controls

The focused suite implements all eight case families:

- **TC-P005-01:** software/emulator/simulated results cannot certify physical S23
  behaviour; codec precision cannot become sensor precision.
- **TC-P005-02:** overlapping source changes invalidate affected assumptions,
  while unrelated documentation changes remain separately reported.
- **TC-P005-03:** missing fixture identity, acquisition context, ownership, or use
  permission excludes only the affected fixture and preserves unrelated results.
- **TC-P005-04:** raw samples override a contradictory green summary; skipped or
  unavailable physical work is not counted as passed.
- **TC-P005-05:** units and domains are exact; milliseconds/microseconds and
  encoded/scene/output-plane values are not interchangeable.
- **TC-P005-06:** in-place threshold changes fail; reviewed successors preserve the
  original policy and failure history.
- **TC-P005-07:** collaborator bytes and Git index are preserved; a changed or
  moving HEAD is reported rather than reset.
- **TC-P005-08:** isolated execution reproduces the software result or names the
  missing prerequisite.

The directive's deliberate mutant—reporting only averages and discarding
outliers—is tested directly. An aggregate with a correct mean cannot establish
per-frame integrity, and colour outliers remain in the reported sample set.
Additional source mutations are retained in the P005 evidence archive.

## Scope and next dependency

P005 provides measurement policy and inference discipline. It does not add a
camera mode, increase dynamic range, calibrate the user's S23 Ultra, establish
physical lip-sync, certify colour, or make APK builds byte-identical. Physical
measurements remain required for physical claims.

After exact-commit CI confirms this implementation, **P006 — decision and risk
gates** is the next dependency-ready foundation phase. P009 camera-route inventory
is also dependency-ready from P003/P004, but the governing foundation sequence
continues through P006 before high-risk or expansive work.
