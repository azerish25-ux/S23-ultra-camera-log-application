# S23Log — Phase 3D.1 audio/video recording foundation

Kotlin/XML Android application for exploring the public camera capabilities of the Samsung Galaxy S23 Ultra and other Android devices. This milestone hardens the Camera2 engine against footage loss and mismatched preview/recording controls. **It does not implement proprietary Samsung Log, a custom log curve or sustained RAW video.**

## Phase 3D.1 changes

- Built-in microphone mono/stereo at 48 kHz, encoded as AAC-LC, alongside explicitly selected video-only. Microphone permission denial never silently removes sound from a requested audio take.
- Bounded two-track startup, one shared timestamp epoch, actual audio/video sample acknowledgement, coordinated EOS draining and existing footage recovery. API 33+ encoder surfaces use explicit monotonic timestamps; estimated/legacy clock paths and drift are labelled unverified.
- Persistent microphone choice and live per-channel PCM levels/clipping during recording. Input route changes or Android-reported silencing fail visibly and preserve recorded footage.
- Schema-3 reports and Android/host checks now validate requested audio tracks, AAC configuration, timing and decoded PCM. The host checker fully decodes both tracks. Packet alignment is not physical lip-sync certification.

See [Phase 3D.1 scope and acceptance](docs/PHASE3D1.md). Physical-phone synchronization, sustained 8K, Log processing, external audio routing and monitoring remain separate acceptance/development work.

## Phase 3B changes

- Capability-driven ordinary-session planning retains advertised sizes and explicitly evaluates 8K 24/30 targets. SDR offers AVC and HEVC independently of HLG10; encoder alternatives remain selectable. Mode evidence exports exact candidates and structured rejection reasons. This does not certify 8K on any phone.
- Fixed AE, variable AE and manual sensor timing are distinguished. A 15–30 AE range is not relabelled 24 fps. Manual-only candidates cannot record before manual exposure has actually been applied; saved mode keys migrate from Phase 3A.
- The portrait viewfinder and landscape recording rail keep Record/Stop outside scrolling controls. Manual controls and recovery remain in a dismissible panel without replacing the live preview surface.
- STARTING remains visible until the first successfully muxed samples from every selected track. Stop cannot resurrect recording through a late first-frame callback. The elapsed timer begins at that acknowledgement.
- **Test 5 seconds** requires explicit confirmation, saves a real clip with the selected audio mode, and automatically stops approximately five seconds after its first encoded frame. Mode and validation JSON include device/firmware, source revision, selected codec/rate strategy, requested/effective controls and actual output evidence.
- Cadence is reported separately from file integrity: at least two seconds of samples, a 3% average-rate tolerance and no intervals over 1.5 frame periods are required for `within_tolerance`. This is not thermal certification. Cadence warnings never delete readable footage.

See [Phase 3B scope and acceptance](docs/PHASE3B.md). Custom Log, high-speed/max-resolution sessions, a full clip browser and physical S23 Ultra acceptance remain separate work.

## Preserved Phase 3A safeguards

- Video is encoded to a private staging file. Verification gates gallery publication, but auxiliary JSON report failures never roll back retained/published footage. Interrupted, format-rejected, and failed-publication clips remain clearly labelled **unverified recovery clips**; zero-sample attempts may be discarded.
- **Recover captures** lists retained footage for grant-based export or explicitly confirmed deletion. Cold-start recovery keeps nonempty videos (including the previous private-file journal format). Cleanup failures keep a retryable journal record. Uninstalling still removes private recovery files: export them first.
- Successful Android 29+ publication copies the verified staging file into a pending MediaStore row, commits publication, then removes the private original. This deliberately needs temporary space for two copies; lack of gallery space retains the original. Android 26–28 moves completed video into private shareable storage.
- Preview uses the selected mode's rate and matching aspect ratio. Camera route, mode and accepted control intent survive recreation and are revalidated on reopen.
- Entering manual exposure is a bounded converge → focus/WB lock → manual-result-confirmation sequence. Record and lens changes are disabled during it. Missing lock metadata/focus failures reject the transition and restore auto exposure. A new metering strategy is not introduced mid-recording. Physical overrides use only the logical device's advertised keys and a physical-aware request builder.
- Optional MediaCodec stream-query failures no longer discard other formats. Nested timing/query errors count in the report summary.

## Implemented

- Lifecycle-managed Camera2 preview, logical/public camera selection, and physical-only camera routing through a logical device.
- Supported manual ISO/shutter/focus controls, available white-balance presets/lock, and actual applied sensor settings from capture results. Video exposure is bounded by its frame interval; no calibrated Kelvin conversion is claimed.
- Per-camera size/rate/encoder planning. SDR offers AVC or HEVC Surface input. HLG10 candidates require explicit camera 10-bit capability, the HLG10 profile, and a matching Surface-input HEVC Main10 encoder. P010 CPU-buffer support is not a prerequisite.
- MediaCodec → MediaMuxer audio/video or explicit video-only recording, EOS draining and timeout, private video staging, transactional MediaStore publication, and explicitly labelled recovery of unfinished footage. API 26–28 uses private, grant-shareable files without broad storage permission.
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
python3 scripts/check_video.py /path/to/capture.mp4 --min-duration 60 --expect-audio
python3 scripts/check_video.py /path/to/hlg.mp4 --min-duration 60 --expect-hlg10
```

JVM regression tests cover 8/10-bit classification (including real libx265 HEVC SPS fixtures), timing policies, stale callback tokens, timestamp pairing, scan/save failures, and lossless report serialization. Framework tests exercise preview recovery, report persistence and FileProvider containment, repeated real recording, and automatic finalization when leaving the activity. CI uses an API 36 emulator with an emulated camera; **that is not physical S23 Ultra validation**.

Each recording produces a shareable validation JSON with requested/applied settings, frame counts/timing, and evidence stages. `advertised` is not the same as `session_configured`, `encoded_frames_received`, or `container_and_output_checked`. Even a checked file is not a full-duration image-quality/thermal certification.

## Use on the phone

Grant Camera permission, select a publicly exposed lens and advertised mode, then choose Mic mono, Mic stereo or Video only. For audio, grant Microphone permission when prompted and press Record again. Stop to finalize and validate. Use **Share capture** and **Share validation** for the resulting files. Open **Diagnostics** for a complete capability report and **Recover captures** for footage retained after an error. A recovery export is not a verified video. Leaving the screen or rotating the device stops and finalizes an active recording; background recording is deliberately not supported.

Different debug signing keys can prevent an update over a previous APK: preserve exported evidence before uninstalling an older debug build. Production signing and a release-update policy remain separate work.

See [device acceptance plan](docs/DEVICE_TEST_PLAN.md) for the remaining hardware evidence and the next custom-log milestone. No 4K/8K, lens, HDR, or RAW throughput is guaranteed without a test of that exact configuration.
