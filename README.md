# S23Log — Phase 2 native Camera2 capture foundation

Kotlin/XML Android application for exploring the public camera capabilities of the Samsung Galaxy S23 Ultra and other Android devices. This milestone adds a real camera engine to the original capability probe. **It does not implement proprietary Samsung Log, a custom log curve, audio capture, or sustained RAW video.**

## Implemented

- Lifecycle-managed Camera2 preview, logical/public camera selection, and physical-only camera routing through a logical device.
- Supported manual ISO/shutter/focus controls, available white-balance presets/lock, and actual applied sensor settings from capture results. Video exposure is bounded by its frame interval; no calibrated Kelvin conversion is claimed.
- Per-camera size/rate/encoder planning. SDR uses AVC Surface input. HLG10 candidates require explicit camera 10-bit capability, the HLG10 profile, and a matching Surface-input HEVC Main10 encoder. P010 CPU-buffer support is not a prerequisite.
- MediaCodec → MediaMuxer video-only recording, EOS draining and timeout, pending MediaStore publication, failed-output cleanup, and recovery of journaled unfinished outputs. API 26–28 uses private, grant-shareable files without broad storage permission.
- Before publication: actual recorded codec/dimensions, all packet timestamps, and a decoded frame are checked. HLG10 additionally requires HEVC SPS 10-bit samples and BT.2020/HLG/limited-range tags. Unsupported HDR is **not silently downgraded to SDR**. Preview is suspended during HLG recording if the camera disallows a mixed SDR/HDR request.
- One RAW_SENSOR DNG or five sequential DNG stills, matching image and capture-result sensor timestamps, bounded image ownership, and metadata/timing reports. The sequence includes file-write time and is explicitly **not a RAW-video benchmark**.
- Complete schema-versioned JSON/text diagnostics: per-property error isolation, physical-camera metadata, P010 camera outputs, per-size timing, high-speed and maximum-resolution stream maps, and explicit profile classification. Exports do not truncate resolution lists.
- Application-owned probe work survives activity recreation. Scans remain available when saving fails. File sharing is limited to an exports directory with temporary URI grants.

## Build

JDK 17 or 21, SDK API 36, Build Tools 36.0.0. The checked-in official Gradle 9.6.0 wrapper and distribution are checksum-pinned; AGP is 9.4.0.

```bash
./gradlew :app:testDebugUnitTest :app:lintDebug :app:lintRelease :app:assembleDebug :app:assembleRelease
```

Debug APK: `app/build/outputs/apk/debug/app-debug.apk`. Release is unsigned until a signing configuration is supplied; no signing keys are stored here.

An explicit offline Maven mirror can be supplied with `-PofflineMavenRepo=/path/to/mirror`; otherwise all dependencies resolve from Google Maven/Maven Central. A local cache is an optimization, not a build requirement. The CI SDK installer is `.github/scripts/install-android.sh`.

## Test

```bash
./gradlew :app:testDebugUnitTest
./gradlew :app:connectedDebugAndroidTest
python3 scripts/check_video.py /path/to/capture.mp4 --min-duration 60
python3 scripts/check_video.py /path/to/hlg.mp4 --min-duration 60 --expect-hlg10
```

JVM regression tests cover 8/10-bit classification (including real libx265 HEVC SPS fixtures), timing policies, stale callback tokens, timestamp pairing, scan/save failures, and lossless report serialization. Framework tests exercise preview recovery, report persistence and FileProvider containment, repeated real recording, and automatic finalization when leaving the activity. CI uses an API 36 emulator with an emulated camera; **that is not physical S23 Ultra validation**.

Each recording produces a shareable validation JSON with requested/applied settings, frame counts/timing, and evidence stages. `advertised` is not the same as `session_configured`, `encoded_frames_received`, or `container_and_output_checked`. Even a checked file is not a full-duration image-quality/thermal certification.

## Use on the phone

Grant Camera permission, select a publicly exposed lens, choose an advertised mode, and start recording. Stop to finalize and validate. Use **Share capture** and **Share validation** for the resulting files. Open **Diagnostics** for a complete capability report. Leaving the screen or rotating the device stops and finalizes an active recording; background recording is deliberately not supported.

Different debug signing keys can prevent an update over a previous APK: preserve exported evidence before uninstalling an older debug build. Production signing and a release-update policy remain separate work.

See [device acceptance plan](docs/DEVICE_TEST_PLAN.md) for the remaining hardware evidence and the next custom-log milestone. No 4K/8K, lens, HDR, or RAW throughput is guaranteed without a test of that exact configuration.
