# Implementation status and acceptance boundaries

> **Specification authority:** [MASTER_DIRECTIVE.md](../MASTER_DIRECTIVE.md) and its linked complete package govern future development. This file records implementation evidence; its legacy phase names are not completion claims for the new P001-P160 programme. See [directive integration](master-directive/INTEGRATION.md).


## Version 0.7 imaging milestone

Continuous RAW acquisition/source retention and an offline LogC3/AWG3 developer are implemented. Exact source/profile binding, checksum/cadence/clipping checks and full decode protect the conversion contract. Physical S23 capture, calibration, real-time processing and high-resolution endurance remain unverified. See [RAW sequence scope and workflow](RAW_SEQUENCE.md).

## On-device RAW development addition (0.8)

Saved RAW sequences can be developed on Android through a row-streaming CPU reference engine into ten-bit LogC3/AWG3 HEVC, subject to explicit P010 encoder/decoder qualification. Includes imported profile binding, captured manufacturer calibration metadata, provisional grey-reference starting profiles, every-frame decode/pixel comparison, cancellation and retained output/source recovery. See [complete contract](ON_DEVICE_LOGC3.md). This does not enable live RAW-to-Log recording or certify physical S23 colour/performance; devices lacking the required codec route remain unavailable.

## Implemented software paths

- Public Camera2 capability discovery, logical/physical route identity, explicit unsupported/query-failed states, complete mode diagnostics and independently revalidated per-camera settings.
- Ordinary-session AVC/HEVC SDR planning, advertised HLG10/Main10 paths, target dimensions/rates including explicit 4K/8K candidates without hidden format fallback. Experimental GPU HLG is limited to eligible ≤1080p24/30 paths.
- Lifecycle preview, persistent Record/Stop, explicit lens-route rail, partial-height draft controls, bounded ISO/shutter/focus, shutter-angle conversion, WB presets/locking, manual sensor-result matching, AE compensation and bounded encoder bitrate targets.
- Foreground recording with AAC mono/stereo or explicit video-only, bounded drain, packet/format/decode checks, private staging, transactional publication, nonempty-footage recovery, storage/thermal controlled stops and requested orientation locking.
- Capture library with actual decoded thumbnails, measured metadata, playback/share, original reports and SHA-256/byte-count video/report pairing.
- Display-only grid/level/histogram/waveform/zebras/false-colour/edge aids, explicit sampling/freshness limits, separate encoded and monitoring surfaces, retained aid changes and bounded recording control history.
- RAW DNG still/short sequential-still measurement, versioned mathematical colour reference/LUT export and independent FFmpeg-consumer checks. Neither is represented as RAW video or custom-Log recording.
- Android debug/release compilation, both lint variants, JVM/host regressions, native emulator camera/encoder/microphone tests, original-byte media verification and captured native UI evidence. Exact counts and source revision are in each CI artifact.

## Deliberately not certified or enabled

| Area | Remaining gate |
| --- | --- |
| Actual S23 Ultra lens/format support | Export diagnostics from the exact phone/firmware; exercise each public route and output configuration |
| Sustained 4K/8K, HDR and GPU processing | Physical long takes, repeated start/stop, storage/temperature/battery conditions, dropped-frame and decoded image checks |
| Native/proprietary Samsung Log | A supported public input/API and independently verified file interpretation; no assumption from the phone model |
| Custom Log recording | Measured input, explicit transfer/container or sidecar contract, full encoder/decode/editor validation, highlight/noise/colour tests |
| RAW-derived video | Continuous source capture and offline reference development now exist; physical calibration/capture, real-time processing and measured sustained device bandwidth remain gates |
| High-speed sessions and stabilization policy | Separate session/control implementation and verified device-specific combinations; ordinary-session advertisements are not proof |
| Calibrated Kelvin, scopes and optical focus | Sensor/display calibration and actual-device measurements; current WB presets and RGB8 display aids are labelled accordingly |
| Physical audiovisual synchronization | Real acoustic/visual events and extended drift tests; packet timestamps alone are insufficient |
| Production distribution | Release-key custody, stable signed update verification, licensing/distribution decision and final device/accessibility/localization review |

## Evidence rules

An advertised capability, a configured session, received encoded frames, a checked container and a physically qualified mode are distinct states. Unavailable hardware must remain unavailable rather than being converted into a passing test. Existing tests retain their failure thresholds; diagnostic/precision repairs must preserve negative controls. Every meaningful source batch is tied to a main-branch revision and CI evidence. A green emulator campaign does not close the device gates above.

## Live lab 0.9

Standalone backend qualification, GPU RAW development, relative-sensor-timestamp streaming and independent live preview are implemented in a separate experimental path. See [LIVE_LOGC3.md](LIVE_LOGC3.md). Physical camera operation, actual end-to-end precision/throughput, audio synchronization, high resolutions and long-duration image quality remain unqualified. Surface capability advertisements are not accepted in place of decoded-pixel proof.

## P001 — research contract (host scope)

The [structured charter](RESEARCH_CHARTER.json) records twenty stable obligations:
required outcomes, conditional research, prohibited claims and excluded scope.
The [requirement-to-evidence index](REQUIREMENT_EVIDENCE.json) preserves a bounded
source inspection and leaves all product claims open, conditional, prohibited or
excluded. The six format identifiers declare required scope; they are not six
implemented film profiles.

The read-only `scripts/verify_research_contract.py` checks receipt bytes, provenance,
inspection revisions, independent evidence classes, raw outcomes, units/domains,
immutable prior records, reviewed policy changes and the planned checkout SHA.
The separate P001 suite exercises TC-P001-01 through TC-P001-08 with twenty-one test
methods and repeated adversarial fixtures. CI retains the exact-commit result and
baseline/perturbed case inputs. See [P001 operation and limits](P001_RESEARCH_CONTRACT.md)
and [local TDD record](evidence/P001-tdd-record.json).

This is host-verified research-record enforcement, not completion of P002-P004,
physical S23 qualification, a production evidence adapter, a film renderer or a
new capture mode. Existing Android code and pinned build configuration are
unchanged. The next dependency-ready work package is P002: reconcile the current
production interfaces/tests with the directive without duplicating the camera
engine. P003 and P004 remain subsequent gated work.

## P002 — bounded repository continuity (host scope)

The [source-backed continuity map](REPOSITORY_CONTINUITY.json) maps all twenty
charter obligations across thirteen existing ownership seams. It records 1,297
reviewed lines in 31 production/build/test files at
`835f67aca7576397e11faafe71ecfb5c93be8a57`, including the retained RAW → profile →
development → verification/retention path. Whole-file identity checking is not a
claim that every line or every other repository file was semantically audited.
The checker explicitly lists uninspected baseline files and unrelated changes.

`scripts/verify_repository_continuity.py` reuses P001 record validation and adds
source/blob/range checks, caller/test anchors, minimum ownership coverage,
requirement completeness, minimal-change decisions and independently parsed
historical JUnit evidence. Twenty-two focused tests cover TC-P002-01 through
TC-P002-08 and CI/archive negative controls. No Android source, package, build
pin or original directive file was changed.

The recorded prior Android run passed its JVM/instrumentation tests, while its
saved-RAW codec route and live backend remained explicitly unavailable. P002 does
not turn those results into physical S23 qualification. Current saved-RAW
processing also cancels on non-configuration screen exit; durable background
jobs, film graphs, virtual optics and the catalogue remain future work.

See [P002 decisions, reproduction and limits](P002_REPOSITORY_CONTINUITY.md).
The next dependency-ready work is **P003 production evidence adapters and stage
classification**; P004 baseline acceptance remains subsequent work. This is a
bounded continuity implementation, not a complete audit of every application
file or a new capture/film-rendering feature.

## P003 — saved-RAW evidence integration (first production slice)

The saved-RAW development worker now produces a distinct stage report for each
attempt, including unavailable, cancelled and failed attempts. The shared model
and independent consumer retain source/profile identity, existing codec controls,
actual encoding/decoded-pixel results, source preservation and publication as
separate observations. Reports are shareable from the existing development screen.
A verified movie remains distinct from physical S23 qualification, and neither a
report write failure nor an unavailable codec deletes the original source.

The new source inspection supersedes the active P002 snapshot without rewriting
its historical records. See [P003 operation and limits](P003_SAVED_RAW_EVIDENCE.md)
and [local host evidence](evidence/P003-host-verification.json). The saved-RAW slice
has 27 pure-model assertions, 18 Python consumer tests, 15 JVM/JUnit test methods
and three added Android worker integration tests. Authored tests are not counted
as executed Android evidence until the exact-commit workflow is inspected.

This is not completion of all P003 adapters. Capability diagnostics, ordinary
recording and live-session stage integration remain the next P003 work; P004
baseline acceptance follows afterward. Existing capture modes, codec precision
thresholds, Android build pins and original directive files remain unchanged.

## P003 — capability and ordinary-recording adapter

The existing capability reports now carry revision/build identity and an explicit
advertised stage. Accepted recording starts retain independent attempt records
before preparation, with configuration, written samples, sample-decode validation,
publication/recovery and report-writing failures kept separate. Diagnostics exposes
**Recording attempt reports** for viewing and sharing, including failed attempts.

This adapter does not invent RAW/profile gates or promote the existing sample
decoder into full-file decoding. Existing capture/audio/HLG policies, numerical
thresholds, finalization and recovery remain intact. See
[P003 recording evidence](P003_RECORDING_EVIDENCE.md) for the tested boundaries and
[local host verification](evidence/P003-recording-host-verification.json).
Actual Android/JVM and emulator results remain separate exact-commit CI evidence.
The remaining P003 work is the live-laboratory adapter and cross-adapter acceptance;
P004 and physical S23 qualification are not closed by this change.

## P003 — live adapter and cross-adapter checks

The live path now creates separate backend-test and camera-session attempt
records, observes its existing operations, and exports them from **Live attempt
reports**. Full structural/timestamp decode remains distinct from original-RAW
pixel comparison and physical qualification. Failed final renames no longer
leave a false published-media reference; partial footage and auxiliary report
failures remain independent.

The prior zero-frame recording control is retained outside the successful-video
corpus and still independently required. The original video acceptance checker,
existing image policies, build pins and preserved directive are unchanged.

See [P003 live evidence](P003_LIVE_EVIDENCE.md) for operation, negative controls and
reproduction. This source change does not claim new Android runtime execution or
physical S23 qualification. Exact-commit Android/JVM/emulator and actual exported
report acceptance remain required before P003 closure; P004 is subsequent work.

## P004 — frozen software baseline

The original `d3a6adaadcbe9349f3f9b017c5da92b0b4c1b9df` Android run
37024421010 passed its complete software campaign: 249 host tests, 340 JVM cases,
62 connected instrumentation cases and one separately executed permission-denial
case. Independent artifact replay validates 25 ordinary recordings and all 38
P003 attempts, while preserving the unavailable saved-RAW codec and live backend.
This accepts P003's tested runtime/exported-report gate, not physical qualification.

The P004 collector now binds source trees, original artifacts, individual test
outcomes, build/command identities and classified reports. A frozen lock and
summary support one-command offline verification. The separate reproduction
workflow runs the unmodified original source, records resolved tools/dependencies
and preserves new failures independently. See [P004 operation and limits](P004_BASELINE.md).
New P004 tests are not part of the historical 249-test baseline. Physical S23,
calibration, high-resolution/endurance and byte-identical APK reproduction remain
unclaimed. P005 follows inspection of actual clean reproduction outcomes.

## P005 — measurement uncertainty and per-frame integrity

The [versioned metric registry](MEASUREMENT_REGISTRY.json) and
[uncertainty-budget template](MEASUREMENT_BUDGET_TEMPLATE.json) now bind units,
domains, sampling procedures, uncertainty sources, calibration inputs,
provisional thresholds and immutable revision history. The standard-library
`measurements.py` assessor preserves every cadence interval and chart patch,
rejects mean-only frame-integrity claims, and keeps codec precision, sensor
precision, exploratory colour and calibrated colour as separate conclusions.

A P003 ordinary-recording adapter preserves useful aggregate cadence while marking
per-frame content integrity inconclusive when the complete sequence is absent.
No Android source, capture path, build pin or existing numerical image-processing
threshold changed. See [P005 operation and limits](P005_MEASUREMENT_UNCERTAINTY.md).
The focused host suite covers TC-P005-01 through TC-P005-08; physical S23,
calibrated colour, effective sensor precision and changing-content device cadence
remain unqualified until their documented protocols are executed.

After exact-commit acceptance, P006 decision/risk gates are the next foundation
phase. This work adds measurement discipline, not a new recording mode or a
physical-camera performance claim.

## P006 — decision and risk gates

Host-only. The [risk register](RISK_REGISTER.json) covers footage loss, misleading
labels, thermal load, rendering instability, licensing, and firmware modification.
The [phase-entry log](PHASE_ENTRY_LOG.json) defers an irreversible firmware
proposal that has no identified blocked stream and no verified recovery.
Enthusiasm is not authorization to flash. `scripts/gates/p006_register.py` and
`scripts/gates/p006_tc01.py` through `p006_tc08.py` implement TC-P006-01 through
TC-P006-08. No Android source, build pin, or physical qualification changed.
See [P006 decision gates](P006_DECISION_GATES.md).

## P007 — provenance ledger

Host-only. The [provenance ledger](PROVENANCE_LEDGER.json) content-addresses
fixtures. Two stock profiles that share a display name and differ in sha256 stay
distinct. Unknown redistribution rights stay out of the public bundle and do not
block private comparison. `scripts/gates/p007_ledger.py` and `p007_tc01.py`
through `p007_tc08.py` implement TC-P007-01 through TC-P007-08. No secrets, media
tokens, or user identifiers are stored in the manifest. See
[P007 provenance](P007_PROVENANCE.md).

## P008 — execution protocol

Host-only. The [agent protocol](AGENT_PROTOCOL.json) and [handoff schema](HANDOFF_SCHEMA.json)
require dependency order, a failing test first, fast-forward publication on
`main`, and remote-head verification before push. A host pass with a pending
physical gate is software-verified only. A local build does not complete the
programme. `scripts/gates/p008_protocol.py` and `p008_tc01.py` through
`p008_tc08.py` implement TC-P008-01 through TC-P008-08. See
[P008 execution protocol](P008_EXECUTION_PROTOCOL.md).

## P009 — logical and physical camera routes

Host fixture, not a live probe. The [route inventory](CAMERA_ROUTE_INVENTORY.json)
keeps a physical member that is not a public camera id addressable through its
logical owner, leaves missing focal length unknown, and rejects opening that
member as an independent camera. One property failure does not erase other
routes. `scripts/gates/p009_routes.py` and `p009_tc01.py` through `p009_tc08.py`
implement TC-P009-01 through TC-P009-08. Existing Camera2 Kotlin is unchanged.
See [P009 camera routes](P009_CAMERA_ROUTES.md).

## P010 — ordinary stream configurations

Host fixture, not a device probe. The [stream map](STREAM_MAP.json) preserves
every advertised size, including a stream whose timing query failed, withholds
fixed cadence when only a variable AE range contains the nominal rate, and
rejects an illegal simultaneous combination without deleting the export.
`scripts/gates/p010_stream_map.py` and `p010_tc01.py` through `p010_tc08.py`
implement TC-P010-01 through TC-P010-08. See [P010 stream map](P010_STREAM_MAP.md).

P006 through P010 are host-verified software gates. They do not certify physical
S23 capture, sustained 4K/8K, endurance, or cinema-camera equivalence. The next
dependency-ready phase is P011, rational capture timing. A later host audit
closed false passes in those gates: weak or "established" physical wording
cannot allow TC-P006-01; incomplete or duplicate fixtures cannot pass
TC-P006-03; skip/stale reports block TC-P006-04; different units block
TC-P006-05 even on one domain; blank prerequisites do not reproduce TC-P006-08;
blank units require clarification in TC-P007-05; a reviewed loosening still
requires renewed validation in TC-P007-06; an unadvertised route is not stored
as advertised-only in TC-P009-02; a constraint violation rejects every output
in TC-P009-03. TC-P006-02 accepts only lowercase 40-character revision hashes.
That audit is still not physical S23 qualification.

## P022 — Protect preview independence (host scope)

Host gate for the directive deliverable "Monitoring branch contract and clean-master invariance test". See [P022_PROTECT_PREVIEW_INDEPENDENCE.md](P022_PROTECT_PREVIEW_INDEPENDENCE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P017 — Model camera resource ownership (host scope)

Host gate for the directive deliverable "Resource-lifetime map and deterministic owner tests". See [P017_MODEL_CAMERA_RESOURCE_OWNERSHIP.md](P017_MODEL_CAMERA_RESOURCE_OWNERSHIP.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P023 — Handle interruption and permission changes (host scope)

Host gate for the directive deliverable "Interruption policy and permission fault tests". See [P023_HANDLE_INTERRUPTION_AND_PERMISSION_CHANGES.md](P023_HANDLE_INTERRUPTION_AND_PERMISSION_CHANGES.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P013 — Discover codec input routes (host scope)

Host gate for the directive deliverable "Codec-route database and interface-specific qualification plan". See [P013_DISCOVER_CODEC_INPUT_ROUTES.md](P013_DISCOVER_CODEC_INPUT_ROUTES.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P012 — Discover dynamic-range profiles (host scope)

Host gate for the directive deliverable "Profile-combination planner and explicit rejection reasons". See [P012_DISCOVER_DYNAMIC_RANGE_PROFILES.md](P012_DISCOVER_DYNAMIC_RANGE_PROFILES.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P021 — Implement focus intent and observed lens state (host scope)

Host gate for the directive deliverable "Dual focus model and focus provenance tests". See [P021_IMPLEMENT_FOCUS_INTENT_AND_OBSERVED_LENS_STATE.md](P021_IMPLEMENT_FOCUS_INTENT_AND_OBSERVED_LENS_STATE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P014 — Plan native high-resolution experiments (host scope)

Host gate for the directive deliverable "High-resolution experiment matrix and source-geometry evidence". See [P014_PLAN_NATIVE_HIGH_RESOLUTION_EXPERIMENTS.md](P014_PLAN_NATIVE_HIGH_RESOLUTION_EXPERIMENTS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P015 — Cache capability evidence safely (host scope)

Host gate for the directive deliverable "Capability cache invalidation and historical evidence viewer". See [P015_CACHE_CAPABILITY_EVIDENCE_SAFELY.md](P015_CACHE_CAPABILITY_EVIDENCE_SAFELY.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P016 — Run the first physical qualification slice (host scope)

Host gate for the directive deliverable "Physical qualification report for one exact configuration". See [P016_RUN_THE_FIRST_PHYSICAL_QUALIFICATION_SLICE.md](P016_RUN_THE_FIRST_PHYSICAL_QUALIFICATION_SLICE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P011 — Model rational capture timing (host scope)

Host gate for the directive deliverable "Rational timing policy and manual-readiness gate". See [P011_MODEL_RATIONAL_CAPTURE_TIMING.md](P011_MODEL_RATIONAL_CAPTURE_TIMING.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P018 — Implement the capture state reducer (host scope)

Host gate for the directive deliverable "Pure reducer, event log format, and race replay tests". See [P018_IMPLEMENT_THE_CAPTURE_STATE_REDUCER.md](P018_IMPLEMENT_THE_CAPTURE_STATE_REDUCER.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P019 — Implement applied manual exposure (host scope)

Host gate for the directive deliverable "Manual exposure controller and result-matching tests". See [P019_IMPLEMENT_APPLIED_MANUAL_EXPOSURE.md](P019_IMPLEMENT_APPLIED_MANUAL_EXPOSURE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P024 — Bound capture queues and backpressure (host scope)

Host gate for the directive deliverable "Backpressure policies and bounded-memory stress harness". See [P024_BOUND_CAPTURE_QUEUES_AND_BACKPRESSURE.md](P024_BOUND_CAPTURE_QUEUES_AND_BACKPRESSURE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P025 — Specify clock domains and epochs (host scope)

Host gate for the directive deliverable "Clock-domain types and timing evidence schema". See [P025_SPECIFY_CLOCK_DOMAINS_AND_EPOCHS.md](P025_SPECIFY_CLOCK_DOMAINS_AND_EPOCHS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P028 — Implement two-track startup and drain (host scope)

Host gate for the directive deliverable "Two-track mux protocol and EOS fault tests". See [P028_IMPLEMENT_TWO_TRACK_STARTUP_AND_DRAIN.md](P028_IMPLEMENT_TWO_TRACK_STARTUP_AND_DRAIN.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P031 — Recover interrupted recordings (host scope)

Host gate for the directive deliverable "Cold-start recovery scanner and interrupted-file fixtures". See [P031_RECOVER_INTERRUPTED_RECORDINGS.md](P031_RECOVER_INTERRUPTED_RECORDINGS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P027 — Qualify microphone acquisition (host scope)

Host gate for the directive deliverable "Audio acquisition contract and blocked-encoder tests". See [P027_QUALIFY_MICROPHONE_ACQUISITION.md](P027_QUALIFY_MICROPHONE_ACQUISITION.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P020 — Implement stable white-balance controls (host scope)

Host gate for the directive deliverable "White-balance intent model and capture-versus-look separation". See [P020_IMPLEMENT_STABLE_WHITE_BALANCE_CONTROLS.md](P020_IMPLEMENT_STABLE_WHITE_BALANCE_CONTROLS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P032 — Measure physical audiovisual synchronization (host scope)

Host gate for the directive deliverable "Physical audiovisual protocol and measured offset report". See [P032_MEASURE_PHYSICAL_AUDIOVISUAL_SYNCHRONIZATION.md](P032_MEASURE_PHYSICAL_AUDIOVISUAL_SYNCHRONIZATION.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P026 — Qualify video encoder startup (host scope)

Host gate for the directive deliverable "Encoder startup owner and output-signal checks". See [P026_QUALIFY_VIDEO_ENCODER_STARTUP.md](P026_QUALIFY_VIDEO_ENCODER_STARTUP.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P029 — Preserve cadence rather than hide gaps (host scope)

Host gate for the directive deliverable "Cadence analyzer and source-to-output time mapping". See [P029_PRESERVE_CADENCE_RATHER_THAN_HIDE_GAPS.md](P029_PRESERVE_CADENCE_RATHER_THAN_HIDE_GAPS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P030 — Publish media transactionally (host scope)

Host gate for the directive deliverable "Publication state machine and storage-pressure tests". See [P030_PUBLISH_MEDIA_TRANSACTIONALLY.md](P030_PUBLISH_MEDIA_TRANSACTIONALLY.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P036 — Build the acquisition-only throughput probe (host scope)

Host gate for the directive deliverable "Acquisition probe and stage-separated throughput report". See [P036_BUILD_THE_ACQUISITION_ONLY_THROUGHPUT_PROBE.md](P036_BUILD_THE_ACQUISITION_ONLY_THROUGHPUT_PROBE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P037 — Build the bounded saved-source writer (host scope)

Host gate for the directive deliverable "Bounded RAW writer and deterministic overflow harness". See [P037_BUILD_THE_BOUNDED_SAVED_SOURCE_WRITER.md](P037_BUILD_THE_BOUNDED_SAVED_SOURCE_WRITER.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P038 — Snapshot calibration metadata at capture time (host scope)

Host gate for the directive deliverable "Capture-time calibration snapshot and identity checks". See [P038_SNAPSHOT_CALIBRATION_METADATA_AT_CAPTURE_TIME.md](P038_SNAPSHOT_CALIBRATION_METADATA_AT_CAPTURE_TIME.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P034 — Pair Images with exact capture metadata (host scope)

Host gate for the directive deliverable "Exact pairing service and reorder-timeout tests". See [P034_PAIR_IMAGES_WITH_EXACT_CAPTURE_METADATA.md](P034_PAIR_IMAGES_WITH_EXACT_CAPTURE_METADATA.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P033 — Specify the RAW sequence container (host scope)

Host gate for the directive deliverable "RAW source specification and hostile-input reader tests". See [P033_SPECIFY_THE_RAW_SEQUENCE_CONTAINER.md](P033_SPECIFY_THE_RAW_SEQUENCE_CONTAINER.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P035 — Implement packed RAW decoding fixtures (host scope)

Host gate for the directive deliverable "Packing adapters and exact golden arrays". See [P035_IMPLEMENT_PACKED_RAW_DECODING_FIXTURES.md](P035_IMPLEMENT_PACKED_RAW_DECODING_FIXTURES.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P039 — Retain sources across cancelled development (host scope)

Host gate for the directive deliverable "Non-destructive development contract and cancellation tests". See [P039_RETAIN_SOURCES_ACROSS_CANCELLED_DEVELOPMENT.md](P039_RETAIN_SOURCES_ACROSS_CANCELLED_DEVELOPMENT.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P040 — Qualify saved RAW on the physical S23 (host scope)

Host gate for the directive deliverable "Physical RAW qualification matrix and retained source fixtures". See [P040_QUALIFY_SAVED_RAW_ON_THE_PHYSICAL_S23.md](P040_QUALIFY_SAVED_RAW_ON_THE_PHYSICAL_S23.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P044 — Establish neutral exposure scale (host scope)

Host gate for the directive deliverable "Neutral-reference measurement and guarded scale estimator". See [P044_ESTABLISH_NEUTRAL_EXPOSURE_SCALE.md](P044_ESTABLISH_NEUTRAL_EXPOSURE_SCALE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P042 — Measure black response and read noise (host scope)

Host gate for the directive deliverable "Black-level model and dark-frame analysis report". See [P042_MEASURE_BLACK_RESPONSE_AND_READ_NOISE.md](P042_MEASURE_BLACK_RESPONSE_AND_READ_NOISE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P041 — Define the calibrated profile contract (host scope)

Host gate for the directive deliverable "Profile schema and provenance-aware importer". See [P041_DEFINE_THE_CALIBRATED_PROFILE_CONTRACT.md](P041_DEFINE_THE_CALIBRATED_PROFILE_CONTRACT.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P043 — Measure flat-field and lens shading (host scope)

Host gate for the directive deliverable "Flat-field acquisition protocol and shading-map validator". See [P043_MEASURE_FLAT_FIELD_AND_LENS_SHADING.md](P043_MEASURE_FLAT_FIELD_AND_LENS_SHADING.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P045 — Fit color transforms with held-out validation (host scope)

Host gate for the directive deliverable "Color fitting tool and independent evaluation report". See [P045_FIT_COLOR_TRANSFORMS_WITH_HELD_OUT_VALIDATION.md](P045_FIT_COLOR_TRANSFORMS_WITH_HELD_OUT_VALIDATION.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P046 — Implement illuminant adaptation carefully (host scope)

Host gate for the directive deliverable "Illuminant handling decision and adaptation test vectors". See [P046_IMPLEMENT_ILLUMINANT_ADAPTATION_CAREFULLY.md](P046_IMPLEMENT_ILLUMINANT_ADAPTATION_CAREFULLY.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P048 — Version and retire calibration profiles (host scope)

Host gate for the directive deliverable "Profile lifecycle manager and reproducibility tests". See [P048_VERSION_AND_RETIRE_CALIBRATION_PROFILES.md](P048_VERSION_AND_RETIRE_CALIBRATION_PROFILES.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P047 — Validate profiles against independent scenes (host scope)

Host gate for the directive deliverable "Independent profile acceptance suite and limitation statement". See [P047_VALIDATE_PROFILES_AGAINST_INDEPENDENT_SCENES.md](P047_VALIDATE_PROFILES_AGAINST_INDEPENDENT_SCENES.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P049 — Normalize RAW without destroying evidence (host scope)

Host gate for the directive deliverable "Signed normalization kernel and reference vectors". See [P049_NORMALIZE_RAW_WITHOUT_DESTROYING_EVIDENCE.md](P049_NORMALIZE_RAW_WITHOUT_DESTROYING_EVIDENCE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P050 — Implement all CFA parity cases (host scope)

Host gate for the directive deliverable "CFA coordinate utility and exhaustive parity tests". See [P050_IMPLEMENT_ALL_CFA_PARITY_CASES.md](P050_IMPLEMENT_ALL_CFA_PARITY_CASES.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P055 — Convert into a declared working space (host scope)

Host gate for the directive deliverable "Working-image descriptor and color conversion tests". See [P055_CONVERT_INTO_A_DECLARED_WORKING_SPACE.md](P055_CONVERT_INTO_A_DECLARED_WORKING_SPACE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P054 — Implement denoising as an optional processing stage (host scope)

Host gate for the directive deliverable "Denoise module and detail-versus-noise evaluation protocol". See [P054_IMPLEMENT_DENOISING_AS_AN_OPTIONAL_PROCESSING_ST.md](P054_IMPLEMENT_DENOISING_AS_AN_OPTIONAL_PROCESSING_ST.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P051 — Build the row-streamed reference demosaic (host scope)

Host gate for the directive deliverable "CPU reference demosaic and exact synthetic goldens". See [P051_BUILD_THE_ROW_STREAMED_REFERENCE_DEMOSAIC.md](P051_BUILD_THE_ROW_STREAMED_REFERENCE_DEMOSAIC.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P053 — Correct defects without erasing real detail (host scope)

Host gate for the directive deliverable "Defect correction policy and highlight-preservation tests". See [P053_CORRECT_DEFECTS_WITHOUT_ERASING_REAL_DETAIL.md](P053_CORRECT_DEFECTS_WITHOUT_ERASING_REAL_DETAIL.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P058 — Define gamut and matrix conventions (host scope)

Host gate for the directive deliverable "Complete signal descriptor and contradiction tests". See [P058_DEFINE_GAMUT_AND_MATRIX_CONVENTIONS.md](P058_DEFINE_GAMUT_AND_MATRIX_CONVENTIONS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P057 — Implement LogC3 EI800 reference arithmetic (host scope)

Host gate for the directive deliverable "Forward and inverse LogC3 functions with source attribution". See [P057_IMPLEMENT_LOGC3_EI800_REFERENCE_ARITHMETIC.md](P057_IMPLEMENT_LOGC3_EI800_REFERENCE_ARITHMETIC.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P059 — Qualify ten-bit sample fidelity (host scope)

Host gate for the directive deliverable "Codec precision protocol and paired positive-negative controls". See [P059_QUALIFY_TEN_BIT_SAMPLE_FIDELITY.md](P059_QUALIFY_TEN_BIT_SAMPLE_FIDELITY.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P056 — Reduce resolution in the correct domain (host scope)

Host gate for the directive deliverable "Resampling module and geometry provenance tests". See [P056_REDUCE_RESOLUTION_IN_THE_CORRECT_DOMAIN.md](P056_REDUCE_RESOLUTION_IN_THE_CORRECT_DOMAIN.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P065 — Define a typed render graph (host scope)

Host gate for the directive deliverable "Render graph schema and static compatibility validator". See [P065_DEFINE_A_TYPED_RENDER_GRAPH.md](P065_DEFINE_A_TYPED_RENDER_GRAPH.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P063 — Validate editor interoperability (host scope)

Host gate for the directive deliverable "Editor round-trip report and import guidance". See [P063_VALIDATE_EDITOR_INTEROPERABILITY.md](P063_VALIDATE_EDITOR_INTEROPERABILITY.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P061 — Separate HLG-derived development from RAW development (host scope)

Host gate for the directive deliverable "Source normalization router and lineage assertions". See [P061_SEPARATE_HLG_DERIVED_DEVELOPMENT_FROM_RAW_DEVELO.md](P061_SEPARATE_HLG_DERIVED_DEVELOPMENT_FROM_RAW_DEVELO.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P052 — Add quality demosaic as a measured upgrade (host scope)

Host gate for the directive deliverable "Quality demosaic benchmark and algorithm selection decision". See [P052_ADD_QUALITY_DEMOSAIC_AS_A_MEASURED_UPGRADE.md](P052_ADD_QUALITY_DEMOSAIC_AS_A_MEASURED_UPGRADE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P060 — Implement P010 packing and stride handling (host scope)

Host gate for the directive deliverable "P010 writer, reader, and guarded-buffer tests". See [P060_IMPLEMENT_P010_PACKING_AND_STRIDE_HANDLING.md](P060_IMPLEMENT_P010_PACKING_AND_STRIDE_HANDLING.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P064 — Audit all product labels (host scope)

Host gate for the directive deliverable "Claim linter and source-aware product wording". See [P064_AUDIT_ALL_PRODUCT_LABELS.md](P064_AUDIT_ALL_PRODUCT_LABELS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P062 — Implement display and Log export branches (host scope)

Host gate for the directive deliverable "Output graph policies and branch-independence tests". See [P062_IMPLEMENT_DISPLAY_AND_LOG_EXPORT_BRANCHES.md](P062_IMPLEMENT_DISPLAY_AND_LOG_EXPORT_BRANCHES.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P072 — Measure full-pipeline performance (host scope)

Host gate for the directive deliverable "Integrated performance report and optimization priorities". See [P072_MEASURE_FULL_PIPELINE_PERFORMANCE.md](P072_MEASURE_FULL_PIPELINE_PERFORMANCE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P068 — Implement synchronization and ownership barriers (host scope)

Host gate for the directive deliverable "GPU resource owner and delayed-completion tests". See [P068_IMPLEMENT_SYNCHRONIZATION_AND_OWNERSHIP_BARRIERS.md](P068_IMPLEMENT_SYNCHRONIZATION_AND_OWNERSHIP_BARRIERS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P071 — Prioritize reliable capture over preview quality (host scope)

Host gate for the directive deliverable "Resource scheduler and capture-priority stress tests". See [P071_PRIORITIZE_RELIABLE_CAPTURE_OVER_PREVIEW_QUALITY.md](P071_PRIORITIZE_RELIABLE_CAPTURE_OVER_PREVIEW_QUALITY.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P066 — Select and qualify the first GPU backend (host scope)

Host gate for the directive deliverable "Backend decision record and capability probe". See [P066_SELECT_AND_QUALIFY_THE_FIRST_GPU_BACKEND.md](P066_SELECT_AND_QUALIFY_THE_FIRST_GPU_BACKEND.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P067 — Validate half and full precision boundaries (host scope)

Host gate for the directive deliverable "Precision budget and CPU-GPU differential suite". See [P067_VALIDATE_HALF_AND_FULL_PRECISION_BOUNDARIES.md](P067_VALIDATE_HALF_AND_FULL_PRECISION_BOUNDARIES.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P070 — Implement temporal chunk boundaries (host scope)

Host gate for the directive deliverable "Temporal chunk contract and uninterrupted-versus-resumed tests". See [P070_IMPLEMENT_TEMPORAL_CHUNK_BOUNDARIES.md](P070_IMPLEMENT_TEMPORAL_CHUNK_BOUNDARIES.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P073 — Define stock profiles and evidence levels (host scope)

Host gate for the directive deliverable "Stock schema and evidence-level validator". See [P073_DEFINE_STOCK_PROFILES_AND_EVIDENCE_LEVELS.md](P073_DEFINE_STOCK_PROFILES_AND_EVIDENCE_LEVELS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P069 — Implement tiled spatial rendering (host scope)

Host gate for the directive deliverable "Tile planner and boundary equivalence tests". See [P069_IMPLEMENT_TILED_SPATIAL_RENDERING.md](P069_IMPLEMENT_TILED_SPATIAL_RENDERING.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P074 — Implement an abstract sensitometric reference (host scope)

Host gate for the directive deliverable "Abstract density reference and response-curve tests". See [P074_IMPLEMENT_AN_ABSTRACT_SENSITOMETRIC_REFERENCE.md](P074_IMPLEMENT_AN_ABSTRACT_SENSITOMETRIC_REFERENCE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P075 — Build data ingestion for sensitometry (host scope)

Host gate for the directive deliverable "Sensitometry importer and unit-consistency checks". See [P075_BUILD_DATA_INGESTION_FOR_SENSITOMETRY.md](P075_BUILD_DATA_INGESTION_FOR_SENSITOMETRY.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P076 — Model channel interaction conservatively (host scope)

Host gate for the directive deliverable "Channel-coupling model and stability tests". See [P076_MODEL_CHANNEL_INTERACTION_CONSERVATIVELY.md](P076_MODEL_CHANNEL_INTERACTION_CONSERVATIVELY.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P077 — Implement exposure and development controls (host scope)

Host gate for the directive deliverable "Exposure-development-grade parameter contract". See [P077_IMPLEMENT_EXPOSURE_AND_DEVELOPMENT_CONTROLS.md](P077_IMPLEMENT_EXPOSURE_AND_DEVELOPMENT_CONTROLS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P078 — Protect skin and neutrals without hidden beautification (host scope)

Host gate for the directive deliverable "Skin-texture evaluation and optional adjustment policy". See [P078_PROTECT_SKIN_AND_NEUTRALS_WITHOUT_HIDDEN_BEAUTIF.md](P078_PROTECT_SKIN_AND_NEUTRALS_WITHOUT_HIDDEN_BEAUTIF.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P079 — Validate stock behaviour across exposure (host scope)

Host gate for the directive deliverable "Stock exposure-series benchmark and limitation notes". See [P079_VALIDATE_STOCK_BEHAVIOUR_ACROSS_EXPOSURE.md](P079_VALIDATE_STOCK_BEHAVIOUR_ACROSS_EXPOSURE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P080 — Package a small validated stock library (host scope)

Host gate for the directive deliverable "Initial versioned stock pack and profile acceptance report". See [P080_PACKAGE_A_SMALL_VALIDATED_STOCK_LIBRARY.md](P080_PACKAGE_A_SMALL_VALIDATED_STOCK_LIBRARY.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P081 — Establish deterministic grain coordinates (host scope)

Host gate for the directive deliverable "Grain seed contract and render-order invariance tests". See [P081_ESTABLISH_DETERMINISTIC_GRAIN_COORDINATES.md](P081_ESTABLISH_DETERMINISTIC_GRAIN_COORDINATES.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P082 — Model exposure-dependent grain statistics (host scope)

Host gate for the directive deliverable "Grain-statistics model and exposure-series tests". See [P082_MODEL_EXPOSURE_DEPENDENT_GRAIN_STATISTICS.md](P082_MODEL_EXPOSURE_DEPENDENT_GRAIN_STATISTICS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P083 — Scale grain by virtual gate and delivery geometry (host scope)

Host gate for the directive deliverable "Format-aware grain mapping and resolution consistency tests". See [P083_SCALE_GRAIN_BY_VIRTUAL_GATE_AND_DELIVERY_GEOMETR.md](P083_SCALE_GRAIN_BY_VIRTUAL_GATE_AND_DELIVERY_GEOMETR.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P084 — Implement emulsion halation separately from bloom (host scope)

Host gate for the directive deliverable "Halation model, kernel tests, and controlled-light benchmark". See [P084_IMPLEMENT_EMULSION_HALATION_SEPARATELY_FROM_BLOO.md](P084_IMPLEMENT_EMULSION_HALATION_SEPARATELY_FROM_BLOO.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P085 — Implement optical bloom and diffusion (host scope)

Host gate for the directive deliverable "Optical diffusion module and energy-response tests". See [P085_IMPLEMENT_OPTICAL_BLOOM_AND_DIFFUSION.md](P085_IMPLEMENT_OPTICAL_BLOOM_AND_DIFFUSION.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P086 — Model print and scan finishing (host scope)

Host gate for the directive deliverable "Print-scan graph and domain-boundary tests". See [P086_MODEL_PRINT_AND_SCAN_FINISHING.md](P086_MODEL_PRINT_AND_SCAN_FINISHING.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P087 — Add aging and mechanical imperfections as optional layers (host scope)

Host gate for the directive deliverable "Optional aging module and clean-default tests". See [P087_ADD_AGING_AND_MECHANICAL_IMPERFECTIONS_AS_OPTION.md](P087_ADD_AGING_AND_MECHANICAL_IMPERFECTIONS_AS_OPTION.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P088 — Validate the combined material pipeline (host scope)

Host gate for the directive deliverable "Combined film-material regression suite". See [P088_VALIDATE_THE_COMBINED_MATERIAL_PIPELINE.md](P088_VALIDATE_THE_COMBINED_MATERIAL_PIPELINE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P089 — Specify all six requested virtual formats (host scope)

Host gate for the directive deliverable "Virtual-format registry and geometry validation". See [P089_SPECIFY_ALL_SIX_REQUESTED_VIRTUAL_FORMATS.md](P089_SPECIFY_ALL_SIX_REQUESTED_VIRTUAL_FORMATS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P090 — Map captured field of view to virtual lenses (host scope)

Host gate for the directive deliverable "Field-of-view mapping and framing guidance". See [P090_MAP_CAPTURED_FIELD_OF_VIEW_TO_VIRTUAL_LENSES.md](P090_MAP_CAPTURED_FIELD_OF_VIEW_TO_VIRTUAL_LENSES.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P091 — Implement signed thin-lens defocus (host scope)

Host gate for the directive deliverable "Thin-lens reference code and dimensional tests". See [P091_IMPLEMENT_SIGNED_THIN_LENS_DEFOCUS.md](P091_IMPLEMENT_SIGNED_THIN_LENS_DEFOCUS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P092 — Separate metric and relative focus controls (host scope)

Host gate for the directive deliverable "Depth-unit contract and honest focus UI". See [P092_SEPARATE_METRIC_AND_RELATIVE_FOCUS_CONTROLS.md](P092_SEPARATE_METRIC_AND_RELATIVE_FOCUS_CONTROLS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P093 — Implement aperture and bokeh shape models (host scope)

Host gate for the directive deliverable "Aperture kernel library and point-light tests". See [P093_IMPLEMENT_APERTURE_AND_BOKEH_SHAPE_MODELS.md](P093_IMPLEMENT_APERTURE_AND_BOKEH_SHAPE_MODELS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P094 — Add field-dependent lens characteristics (host scope)

Host gate for the directive deliverable "Lens-character profile schema and continuity tests". See [P094_ADD_FIELD_DEPENDENT_LENS_CHARACTERISTICS.md](P094_ADD_FIELD_DEPENDENT_LENS_CHARACTERISTICS.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P095 — Implement optional anamorphic interpretation (host scope)

Host gate for the directive deliverable "Anamorphic mode contract and geometry regression tests". See [P095_IMPLEMENT_OPTIONAL_ANAMORPHIC_INTERPRETATION.md](P095_IMPLEMENT_OPTIONAL_ANAMORPHIC_INTERPRETATION.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P096 — Validate virtual optics against controlled geometry (host scope)

Host gate for the directive deliverable "Optical validation laboratory and error decomposition". See [P096_VALIDATE_VIRTUAL_OPTICS_AGAINST_CONTROLLED_GEOME.md](P096_VALIDATE_VIRTUAL_OPTICS_AGAINST_CONTROLLED_GEOME.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P097 — Define the depth-provider interface (host scope)

Host gate for the directive deliverable "Depth provider contract and stale-result tests". See [P097_DEFINE_THE_DEPTH_PROVIDER_INTERFACE.md](P097_DEFINE_THE_DEPTH_PROVIDER_INTERFACE.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P098 — Select a licensable baseline model (host scope)

Host gate for the directive deliverable "Model selection record and licence manifest". See [P098_SELECT_A_LICENSABLE_BASELINE_MODEL.md](P098_SELECT_A_LICENSABLE_BASELINE_MODEL.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.

## P099 — Verify image preprocessing (host scope)

Host gate for the directive deliverable "Preprocessing reference and host-device tensor comparisons". See [P099_VERIFY_IMAGE_PREPROCESSING.md](P099_VERIFY_IMAGE_PREPROCESSING.md). A green host run is not a physical S23 measurement, sustained 4K/8K proof, or cinema-camera equivalence. Android sources were not changed by this phase.
