# Phase 3D.1 — microphone audio and two-track recording

## Implemented scope

The capture screen offers microphone mono (the default), microphone stereo, or explicitly selected video-only. Audio uses the built-in input, AudioRecord PCM16 at 48 kHz and AAC-LC at 128 kb/s mono or 192 kb/s stereo. Stereo is a negotiated two-channel stream, not a claim of two physically independent microphones. Unsupported stereo fails visibly; it is not silently downmixed. USB/Bluetooth routing, monitoring playback, manual gain, background capture and custom Log are outside this milestone.

Microphone permission is requested only from an explicit recording action. Granting permission does not silently start a take: press Record again. Denial preserves the user's audio intent and offers Settings, video-only or cancellation. No microphone is opened just to show preview. The input closes on every stop/failure. Android-reported client silencing or a change away from the selected built-in route stops the take and preserves nonempty footage as unverified recovery media. Silent PCM alone is not evidence of a broken microphone.

A compact audio row remains in the persistent capture dock/landscape rail. It shows the selected audio mode, live channel levels and clipping while recording. A missing/estimated clock or excessive observed nominal-clock drift is labelled sync-unverified. The meter is software PCM peak/RMS metering, not calibrated analog headroom.

## Startup, timestamps and shutdown

`AvMuxCoordinator` serializes both tracks on the encoder handler. It starts MediaMuxer only after all selected track formats and first payloads are available. Startup ownership is bounded to 32 MiB/512 encoded packets; PCM awaiting AAC is bounded to two seconds. Stop/error flushes available startup samples only as partial recovery, never as a valid requested two-track capture. The RECORDING acknowledgement requires successfully muxed samples from both requested tracks; stopping suppresses late acknowledgements. The existing five-second test uses this same selected audio path.

On API 33+, the MediaCodec camera output explicitly requests OutputConfiguration.TIMESTAMP_BASE_MONOTONIC. Audio sample positions are anchored using AudioRecord.getTimestamp(TIMEBASE_MONOTONIC), and subsequent PCM timestamps follow sample count from that immutable anchor. Muxed tracks share one epoch; independently resetting each track's first timestamp is prohibited. An initial separation over five seconds is rejected as an unrelated-clock error, retaining available video separately rather than inventing sync.

A HAL that supplies no usable audio timestamp within the startup window uses a clearly labelled `read_completion_estimate_unverified`. It preserves sound, not a synchronization guarantee. The observed deviation between later timestamps and the nominal sample clock is recorded; this milestone does not resample to compensate for oscillator drift. On API 26–32, encoder defaults are labelled legacy/unverified. No path claims physical lip-sync certification. Camera SENSOR_TIMESTAMP and encoder-surface timestamps must not be interchanged.

Both encoders drain with an eight-second EOS deadline. Partial microphone reads are coalesced into 1024-sample AAC-LC inputs (except the final tail), preserving a contiguous sample-count timeline. Audio reads are nonblocking on the recorder handler, so no audio-thread join can deadlock finalization. There are separate microphone/encoded-sample watchdogs. Foreground-only behaviour remains: leaving/rotating the activity finalizes the take. MediaStore staging, recovery, report-save failure handling and first-video-frame safeguards are preserved.

## Evidence and tests

Recording validation schema 3 includes the audio mode, configured channels/rate/bitrate, input route, sample-clock anchor/source/drift, PCM counts, encoded sample counts, common epoch and explicit physicalLipSyncVerified=false. The Android verifier checks exact selected track count, AAC AudioSpecificConfig (1024-frame LC), all packet timestamps, one decoded video frame and audio PCM. The host verifier inspects every track and decodes complete video AND audio streams.

Packet start/end offsets and missing intervals are reported separately from file integrity. `within_250ms` describes broad track coverage only, NOT a lip-sync tolerance. Warning clips are preserved. Encoder priming/padding is reported when exposed. `checked` still means media integrity, not full-duration synchronization/quality certification.

JUnit/standalone policy tests exercise delayed formats, common-epoch offsets, mutable-buffer ownership, startup limits, early stop/partial recovery, late callbacks, PCM clock drift/fallback and clipping. Python tests reject missing/extra audio, mismatched channels/rate/profile, duplicate/regressing timestamps and missing CI audio evidence. Instrumentation uses real emulated Camera2/AudioRecord/AAC for repeated mono takes, stereo, a 65-second take and lifecycle finalization. A separate instrumentation process starts after actual runtime-permission revocation and exercises the system microphone denial button, cancellation, preserved audio intent, and explicitly muted recording; CI requires its evidence. It does not assume that a package-level AppOps command denied access. CI explicitly requires at least six fully decoded audio recordings, including stereo and a >=60-second audio sample span. Emulated input may be silence and does not establish physical acoustic sync.

```sh
./gradlew :app:testDebugUnitTest :app:lintDebug :app:lintRelease :app:assembleDebug :app:assembleRelease
bash .github/scripts/emulator-test.sh # Complete two-process microphone permission + recording suite
python3 -m unittest discover -s scripts/tests -v
python3 scripts/check_video.py capture.mp4 --expect-audio --audio-channels 1 --min-duration 60
python3 scripts/check_video.py muted.mp4 --expect-video-only
kotlinc app/src/main/java/com/s23log/probe/core/*.kt scripts/audio_core_smoke.kt -include-runtime -d /tmp/audio-smoke.jar
java -jar /tmp/audio-smoke.jar
```

## Physical S23 Ultra gate

Repeat mono/stereo and explicitly muted captures on the phone. Test a clap/flash event near the start and end of ten-minute 24/30 fps clips, measure actual image/sound offset and drift (accounting for AAC priming/padding), and retain original media plus validation JSON. Target no more than one video frame of measured physical offset/drift, but do not call it passed from timestamps alone. Exercise denied/revoked permissions, the microphone privacy switch, competing capture, immediate Stop, route changes, backgrounding and storage failures. Test 8K/HLG combinations separately: no new hardware capability or custom Log implementation is claimed here.

Primary API contracts used:
- https://developer.android.com/reference/android/hardware/camera2/params/OutputConfiguration#TIMESTAMP_BASE_MONOTONIC
- https://developer.android.com/reference/android/media/AudioRecord#getTimestamp(android.media.AudioTimestamp,%20int)
- https://developer.android.com/reference/android/media/MediaMuxer

## AAC end-of-stream regression

Partial AudioRecord reads are coalesced into 1024-frame AAC-LC inputs. At Stop,
the last valid buffer (including a short tail) carries end-of-stream; no second
empty input is submitted after it. If all PCM was already submitted, a single
empty EOS is used instead. No captured PCM is discarded, zero-padded by the app,
or assigned a new output timestamp to conceal a gap. Unit cases cover every
boundary; real-codec tests exercise mono/stereo tails and empty-EOS completion.
The gap-free packet assertion in repeated microphone recordings remains enabled.

Failure collection also retains published test MP4s separately for debugging.
They do not count as successful acceptance evidence.
