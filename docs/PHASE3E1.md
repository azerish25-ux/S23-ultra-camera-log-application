# Phase 3E.1 — high-precision HLG processing and independent monitoring

## Implemented, not certified

An explicitly selected **GPU HLG (experimental)** mode routes Camera2 through application-controlled colour processing. Existing direct SDR and HLG modes and their saved identifiers remain unchanged. This milestone limits GPU candidates to advertised ordinary-session HLG10/HEVC configurations at no more than 1920×1080 and 24/30 fps. Direct 4K/8K candidates remain available according to the existing planner. No 8K GPU throughput, physical S23 Ultra performance, or custom-Log recording is claimed.

The recording route is:

`Camera HLG10 YUV → explicit BT.2020/range conversion → inverse HLG → RGBA16F → forward HLG → RGB10_A2 HLG EGL window → Main10 HEVC → existing A/V muxer`.

An independent display branch maps the same working image to an SDR viewing transform or an uncorrected HLG signal view. The recorded transform always remains HLG. The reference custom-Log formula and inverse are implemented/tested, but **there is no selectable custom-Log recording mode**. Files are not mislabelled with HLG metadata after applying a different recording transfer function.

## Eligibility and runtime gates

The mode planner keeps camera input, working space, recorded transfer, and monitoring separate in `ColourPipelineSpec`. GPU candidates require API 33+, the camera's ten-bit/HLG capability, an advertised SurfaceTexture size/rate and ordinary exposure-timing path, Main10 surface-input encoding, and the encoder's `HdrEditing` or (API 35+) `HlgEditing` feature. An encoder name or ten-bit bitstream header alone is insufficient.

Before camera recording starts, EGL must provide an exact recordable 10/10/10/2 configuration, `EGL_EXT_gl_colorspace_bt2020_hlg`, OpenGL ES 3, renderable RGBA16F, and `GL_EXT_YUV_target`. The selected encoder configuration is actually created. A small 1024-pixel precision/monitor/reference-transform probe must pass. The first incoming frame must identify BT.2020, HLG, and full or limited range via its dataspace. Unknown values fail explicitly; the application does not guess a matrix or silently substitute SDR/direct recording.

Input YUV is sampled with a high-precision `__samplerExternal2DY2YEXT` sampler, avoiding an implicit driver-selected colour matrix. Synthetic RGB/YUV tests exercise the math but do not certify a physical camera's private buffer representation. Camera import, encoder acceptance, decoded pixels, and physical colour accuracy are distinct evidence boundaries.

## Ownership, preview and timestamps

A dedicated colour worker owns the EGL context, camera input texture/surface, FP16 image, and encoder EGL window. The old camera preview session must report closure before EGL connects to the TextureView surface; two producers never intentionally own that surface together. Existing preview orientation/aspect handling is retained.

The monitoring worker has a separate shared EGL context and three bounded SDR textures. Fence and slot ownership prevents reuse before sampling completes. If every monitor buffer is busy, only the preview update is skipped. There is no unbounded queue of full-resolution CPU images. Shared GPU/driver capacity can still affect recording; no complete performance isolation is claimed.

Each source frame carries the explicitly requested Camera2 monotonic output timestamp into `eglPresentationTimeANDROID`. Processing completion time is not used as capture time. Nonpositive, regressing, unrelated/future, or excessively stale timestamps are rejected. SurfaceTexture may coalesce camera buffers; large source intervals and maximum processing time are reported, not concealed by inventing timestamps or duplicate frames. Existing common A/V epoch and first-written-sample gates remain.

Stop first suppresses new processing, then asynchronously closes monitor/colour ownership before signalling encoder EOS. Closure is bounded by a three-second deadline at the recorder; an unresponsive native driver is reported as unconfirmed cleanup and failure/recovery, never confirmed release. Existing audio ownership, AAC end padding, publication and nonempty-footage retention are preserved. SurfaceTexture release is deferred during GPU shutdown when the Activity disappears.

## Pixel tests and tolerances

`ColourGpuTest` must execute actual OpenGL arithmetic. It passes 1024 input gray levels through the production FP16 inverse/forward HLG shaders into an RGB10 framebuffer, requiring maximum absolute error <=1.25/1023, at least 768 distinct ten-bit codes, and monotonic output. The deliberately degraded RGBA8 working target must fail the same checker. Monitoring switches must leave recording framebuffer pixels identical.

GPU/CPU comparison limits are 0.002 for the reference Log transform and SDR monitor, and 0.003 for BT.2020 limited-range colour patches. These are normalized arithmetic tolerances, not calibrated camera colour-error claims. Small synthetic setup/test readbacks are allowed; full-resolution live CPU readbacks are not used.

A separate rendered-HLG encoder test is attempted only when the actual device exposes its necessary features/configuration. It encodes a 1024×128 neutral ramp through FP16 and a 10-bit HLG EGL encoder surface. The Android verifier checks Main10 SPS, dimensions, timestamps, decode and HLG tags. The host additionally fully decodes the clip and checks neutral luma against limited-range codes 64…940: mean error <=3 codes, maximum <=12, endpoints within 8. This lossy-output check is distinct from the precision negative control. Missing HDR hardware is recorded as **unavailable with a reason**, not a ten-bit success.

`ColourCameraTest` similarly records a short GPU-backed camera take only when a non-manual candidate plus the runtime import/EGL features exists. It toggles monitoring and checks processed frames, displayed frames, cleanup and Main10 output. An unavailable camera is explicitly reported. This is not a physical S23 Ultra certification or a sustained performance test.

The existing known-content 24/30 fps flash/tone fixtures now use the production FP16 colour renderer and change monitoring during capture. The host still decodes their actual picture/sound events and keeps the existing explicit AAC-priming allowance. The colour checker requires proof that both fixture rates used the processing stage; synthetic alignment does not establish acoustic lip-sync.

## Run and interpret

```sh
./gradlew :app:testDebugUnitTest :app:lintDebug :app:lintRelease :app:assembleDebug :app:assembleRelease :app:assembleDebugAndroidTest
bash .github/scripts/emulator-test.sh
python3 -m unittest discover -s scripts/tests -v
python3 scripts/check_timing.py evidence/emulator/app-evidence.tar
python3 scripts/check_colour.py evidence/emulator/app-evidence.tar
kotlinc app/src/main/java/com/s23log/probe/core/*.kt scripts/colour_core_smoke.kt -include-runtime -d /tmp/colour.jar
java -jar /tmp/colour.jar
```

CI retains `colour-summary.json`, pixel measurements, processed timing fixtures and explicit HDR encoder/camera availability reports. CI may pass the applicable implementation tests with the HDR hardware gates unavailable. Such a run is **not** end-to-end ten-bit camera validation. Existing microphone timing warnings remain separate and visible.

## Remaining gates

On the S23 Ultra, evaluate the exact eligible mode and export original footage plus validation/diagnostics. Use controlled gray ramps, coloured patches, highlights and identifiable audiovisual events. Test monitor changes, immediate Stop, permission/lifecycle interruption, repeated captures and longer takes. Check preview orientation and actual camera/YUV import precision. Only then promote the mode's physical support status or extend the processing limits toward 4K/8K.

Phase 3E.2 must decide and verify the custom recording transfer/metadata/editing workflow before exposing a Log switch. Sensor RAW, proprietary Samsung Log, external microphones, GPU 8K and the full clip browser are outside this change.

Primary API/format contracts:
- https://developer.android.com/media/camera/camera2/hdr-video-capture
- https://developer.android.com/reference/android/media/MediaCodecInfo.CodecCapabilities
- https://developer.android.com/reference/android/graphics/SurfaceTexture
- https://developer.android.com/reference/android/hardware/camera2/params/OutputConfiguration
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_YUV_target.txt
- https://registry.khronos.org/EGL/extensions/EXT/EGL_EXT_gl_colorspace_bt2020_hlg.txt
