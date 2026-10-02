# P003 — capability and ordinary-recording evidence

Active slice: **P003**, with focused TC-P003-01 through TC-P003-08 coverage.
Continue the [Master Directive](../MASTER_DIRECTIVE.md); this extends the existing
Kotlin camera, not a new recorder or a new Log/HDR mode. Saved-RAW reporting remains
in [its separate contract](P003_SAVED_RAW_EVIDENCE.md). The live adapter and P004
formal baseline are still open.

## Application behaviour

Diagnostics now provides **Recording attempt reports**, listing the latest 64
retained attempt files, their independent stage outcomes and a share action.
Reports are written to `files/exports/recording-evidence/recording-attempt-<uuid>.json`.
Files outside the UI's latest-64 window are not deleted. Every accepted recording
start creates an attempt before codec setup, including failures before a camera
session or encoded footage exists. Rejected UI actions that never pass the
existing start guards do not pretend to be recording attempts.

`CameraController` retains the actual selected `CameraCatalog.plan` candidate,
mode, route and request. `ModeEvidence` binds the advertised-only planner subset
to device build and application revision. `ProbeReport` preserves its schema-2
field states while adding report/revision/build identity and an advertised stage;
query failures remain distinct from unsupported or unreported properties.

`SurfaceRecorder` observes its existing preparation, configuration callback,
written video/audio samples, output validation, publication and recovery. The
same UUID joins its legacy schema-3 sidecar to the new report. Early preparation
failures produce a closed attempt without inventing a session or output. Stops
before frames remain blocked, and requested audio cannot disappear into a
video-only success. Each retry has a new identity; late callbacks cannot rewrite
a closed stage or earlier attempt.

## Evidence and retention contracts

The shared P003 outcome vocabulary is reused. The ordinary recording classifier
has its own applicable stages: it does not invent RAW-source or profile checks.
Raw observation JSON strings retain SHA-256 identities. The independent Python
consumer checks these bytes, source/attempt/configuration identities, actual
outcomes, units, existing numerical policy and media/sample-count consistency.
A valid output check can remain useful even if recording fails or publication
requires recovery. Publication must reference the same checked media identity.

**The on-device verifier inspects every packet timestamp and decodes a sample
video frame and, when requested, sample audio PCM. It does not fully decode the
movie.** The adapter therefore leaves `full_decode` and `physical_qualification`
`not_run`. Existing CI's separate `check_video.py` still performs full-file decode;
it is not silently credited to the on-device adapter. SDR/HLG recording is not
labelled custom Log, and the new reports do not certify sensor precision,
sustained native 4K/8K, physical synchronisation, calibrated colour or dynamic range.

The existing 3% cadence warning policy, two-second minimum measurement span,
AAC selection, HLG SPS/tag checks, image processing and finalizer thresholds are
unchanged. Source span units are microseconds in the muxed-video presentation
 timestamp domain, not wall-clock duration. Camera/profile/capture correctness
requires its own evidence; a matching hash proves bytes, not measurement honesty.

Checkpoints are queued on the existing serial diagnostics IO executor, not written
per frame or synchronously on a codec callback. Interrupted persistence can leave
an incomplete checkpoint. Exclusive creation refuses to overwrite an existing
attempt. Report/observation errors are isolated from successful media operations:
a save failure must not delete footage or turn a published movie into recovery.
The UI exposes persistence failure separately. This is bounded best-effort report
persistence, not proof against every disk/power-loss condition or a resumable job.

## Reproduction and tests

```sh
python3 scripts/verify_master_directive.py
python3 scripts/verify_research_contract.py --expected-head "$(git rev-parse HEAD)"
python3 scripts/verify_repository_continuity.py --expected-head "$(git rev-parse HEAD)"
python3 -m unittest discover -s scripts/tests -p 'test_recording_evidence.py' -v
python3 -m unittest discover -s scripts/tests -v
python3 scripts/check_recording_evidence.py <attempt.json-or-app-evidence.tar> --expected-revision <sha>
```

The pure classifier runner `scripts/recording_evidence_smoke.kt` has 39 host
assertions. The independent consumer has 25 tests, including an advertised/
configured 8K candidate without encoded frames, synthetic output mistaken for
physical evidence, misleading green summaries, wrong revisions/media, missing
provenance/units, altered policy and fresh isolated reading. Three deliberately
introduced consumer defects are detected and restored in the retained host logs.
`RecordingAttemptTest` has 16 JVM methods covering the real producer, immutable
records, actual finalizer boundaries, queued persistence, auxiliary write failure
and publication identity. Authored tests are not executed Android evidence until
CI for the corresponding source is inspected.

Two new instrumentation methods exercise actual `SurfaceRecorder` preparation
with a missing codec and cancellation without any camera session. Existing
`CameraSmokeTest` recordings now require their real exported attempts, while
its diagnostics test checks the actual probe identity and report button. CI's
independent consumer requires successful recording, early-failure, no-frame and
probe evidence and pairs legacy sidecars to their attempts. Existing full-file
video, audio, RAW and live checks remain enabled.

TC-P003-01: unsupported success/physical claims; -02: exact revision and media
binding; -03: observation/provenance identity; -04: raw outcomes and requested
audio; -05: units/domains; -06: unchanged numerical policy; -07: retained source,
media and prior attempts; -08: isolated consumer and actual exported reports.
These are focused cases for this slice, not all repetitions of P003's catalogue.

## Handoff boundary

A new immutable source inspection is appended for the changed code; historical
P001/P002/saved-RAW records are retained, not relabelled as current. Source review,
host execution, Android/JVM execution and emulator/physical outcomes remain
separate. Local API type-checks using compile-only AndroidX/generated stubs are
not an Android build or runtime proof. Exact Android results belong to the
published revision's CI artifacts.

**Next: P003 live-laboratory adapter and final cross-adapter acceptance**, followed
by P004's reproducible application baseline. No live-camera qualification or
physical S23 capability is claimed by this recording/reporting work.
