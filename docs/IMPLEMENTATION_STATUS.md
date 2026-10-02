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
