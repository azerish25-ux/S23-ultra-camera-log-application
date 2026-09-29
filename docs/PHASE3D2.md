# Phase 3D.2 — acquisition isolation and timing evidence

## Recording path

MicrophoneReader exclusively owns AudioRecord start/read/timestamp/route/stop/release on a dedicated audio-priority thread. AAC callbacks and MP4 writes stay serialized on the existing encoder handler. PcmHandoff copies incoming bytes, accepts at most 96,000 PCM frames, and exposes high-water/accounting/overflow measurements. Consumer notifications are coalesced; PCM is never carried in an unbounded Handler message queue. An exhausted budget fails explicitly without evicting previously accepted sound. On exceptional abort, read/accepted/submitted differences remain visible in the report; sound that could not reach a failed encoder is not claimed saved.

The reader uses nonblocking reads and immediately catches up while data remains available; it waits two milliseconds only on an empty read. Silence is valid input. Route/privacy checks do not depend on receiving nonzero-amplitude sound. Encoder congestion therefore no longer directly schedules microphone acquisition. This does not make the app immune to native capture errors, OS starvation, or a stalled filesystem.

## Clock and stop policy

Production PcmClock requires at least three progressive observations over 100ms with projected-origin spread <=2ms before accepting a native startup anchor. Qualification uses a constant-space stable interval, not a fixed-count timestamp window: even 1 ms progressive observations can qualify without weakening the 100 ms minimum. An origin shift beyond 2 ms restarts that interval. The anchor is the midpoint of its observed origin bounds and is then immutable. A 750ms startup without qualified native timestamps uses an explicitly unverified read-completion estimate. Regressions, nonprogressive timestamps, abrupt residual changes >20ms, and gradual nominal-clock deviation >33.333ms are separately reported. Later observations never rewrite encoded timestamps. No resampling is performed and these diagnostics cannot determine an exact missing-input count.

Stop captures a monotonic cutoff before camera-session teardown and signals acquisition independently of the encoder queue. A qualified, non-starved reader drains toward the corresponding sample-count cutoff, with a 200ms ceiling. Otherwise it drains currently available native PCM until the first empty read, also bounded by 200ms, labelled available_buffer_drain_unverified. Already read PCM is preserved, including any measured cutoff overshoot. The AAC handoff drains after the native owner terminates; the existing explicitly counted final AAC silence padding remains unchanged.

Failure shuts down the camera and drains retained audio/video through the existing bounded EOS path. Codec failure can still leave unsubmitted audio, reported as failure/recovery rather than success. Native input closure is asynchronous: no joins on camera/UI/encoder threads. Final reporting waits up to two seconds for the reader owner; timeout is an error and never claims native release was confirmed.

## User-visible quality

The live meter reports reader starvation risk, unverified clocks, discontinuity suspicion, and nominal-clock deviation rather than a generic synchronized claim. Saved results include timingQuality separately from media-integrity status. Packet coverage warnings remain warnings even for a decodable file. API 26–32 retain the explicit legacy-video-clock warning. physicalLipSyncVerified is always false in this milestone.

## Tests and acceptance

- CaptureTimingTest and scripts/timing_core_smoke.kt exercise a paused consumer, bounded overflow with retained data, pre-start Stop/cancel, final byte preservation, startup qualification, timestamp jumps, smooth drift, and immutable clocks.
- AudioAcquisitionLoadTest uses real AudioRecord/AAC and blocks the encoder handler for 250ms. Acquisition must advance during the block; all read PCM must be submitted, no handoff overflow may occur, and the native owner must close.
- TimingFixtureTest exists only in the test APK. It encodes known flashes and tones at 1s/4s, at both 24/30fps, using production PcmHandoff and AvMuxCoordinator plus real AVC/AAC codecs. Audio deliberately starts 125ms after video; event content is on the shared timeline. Selected mux writes block for 75ms.
- scripts/check_timing.py decodes actual image luminance and PCM amplitudes, using decoded-frame timestamps. It requires two events, video-marker accuracy within one frame, and marker drift <=one frame. Absolute audio offset permits one frame plus reported AAC delay, or at most 2,048 samples (42.667ms) when priming metadata is unavailable. That explicit uncertainty is NOT frame-accurate physical lip-sync certification. Per-track zero reset, missing markers and collapsed audio intervals fail the host regression tests.
- CI requires the fixtures, real acquisition-under-load evidence, and reader shutdown/accounting in every microphone recording. The real microphone timing status is separately classified in timing-summary.json; an emulator timing warning is not converted to success by synthetic results. All existing microphone/permission, codec-tail, video-only, recovery and full-decode checks remain.

Run:

```sh
./gradlew :app:testDebugUnitTest :app:lintDebug :app:lintRelease :app:assembleDebug :app:assembleRelease :app:assembleDebugAndroidTest
bash .github/scripts/emulator-test.sh
python3 -m unittest discover -s scripts/tests -v
python3 scripts/check_timing.py evidence/emulator/app-evidence.tar
kotlinc app/src/main/java/com/s23log/probe/core/*.kt scripts/timing_core_smoke.kt -include-runtime -d /tmp/timing.jar
java -jar /tmp/timing.jar
```

## Physical-device gate remains open

Neither synthetic encoding nor silent/emulated AudioRecord proves acoustic synchronization. Record identifiable audiovisual events near both ends of ten-minute 24/30fps clips on the S23 Ultra, measure initial offset and drift accounting for known priming/padding, and retain the media, diagnostics and validation JSON. The physical target remains <=one frame, not the broader fixture priming allowance. Investigate any warning rather than retiming the output to conceal it. No new Log transform, 8K hardware certification, external microphone route, or background recording is claimed.

Primary contracts:
- https://developer.android.com/reference/android/media/AudioRecord (nonblocking read, native timestamp, stop)
- https://developer.android.com/reference/android/media/AudioTimestamp
- https://developer.android.com/reference/android/media/MediaFormat#KEY_ENCODER_DELAY
- https://developer.android.com/reference/android/opengl/EGLExt#eglPresentationTimeANDROID(android.opengl.EGLDisplay,%20android.opengl.EGLSurface,%20long)
