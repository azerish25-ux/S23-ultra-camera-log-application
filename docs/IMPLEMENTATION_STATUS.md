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
