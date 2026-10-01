# On-device RAW development — 0.8

This milestone develops a **saved sensor RAW sequence into LogC3/AWG3 on Android**. It is a row-streamed CPU reference engine, not a real-time GPU recorder. Capture remains the separate five-second RAW experiment. No firmware is modified; no S23 lens, resolution, sustained performance, sensor dynamic range or ARRI-equivalent image quality is certified by this release.

## Use

1. Record and retain a RAW sequence using Continuous RAW lab. Stop capture before opening the developer.
2. Settings & exports → Retained RAW sequences → select the source → **Develop as LogC3**.
3. Import a matching colour-profile JSON using Android's document picker, or create a manufacturer-metadata starting profile as described below. Profiles are copied into the app's private storage; imported originals and RAW sources are never overwritten.
4. Select full, half or quarter crop dimensions. Reduction is a scene-linear box average before Log encoding, not an upscale. The crop must divide evenly into the chosen even output dimensions.
5. Confirm provisional development separately when using a starting profile. Output clipping requires its own explicit checkbox; it is not silently enabled. Press **Develop as LogC3**.
6. The app qualifies an advertised P010/Main10 codec route, develops the sequence, fully decodes and compares every output frame, and only then promotes the file from `.partial.mp4` to `.mp4`. Share the video **with its `.logc3.json` sidecar**. Checked outputs are indexed in the existing Clips library with their LogC3 and calibration labels.

Remain on the development screen. Rotation reattaches to the same application-owned task without starting another export; leaving the screen cancels it. A controlled cancellation, failed encoder, low storage or severe thermal event does not delete RAW sources. Partial/unpublished MP4s remain explicitly named `.partial.mp4` in **Retained exports / partial files**. They are not accepted clips and may not be playable. Export before uninstalling: all private source/profile/export data is removed by uninstalling the app.

## Colour profiles

Imported profiles use the same schema as [the desktop developer](RAW_SEQUENCE.md#calibrated-profile-contract). Source firmware, logical and physical lens route, dimensions and CFA must match exactly; crop, finite transforms and frame exposure/ISO are checked. `measured` is the imported author's assertion, **not certification by the app**. `provisional` requires explicit user consent. A synthetic profile is accepted only for a declared synthetic fixture source; it cannot qualify physical phone footage.

New RAW captures preserve available Camera2 forward, calibration and colour transforms, both reference illuminants, errors/nulls, and per-frame neutral colour point. Older 0.7 sources lack that snapshot: they can still be developed with an imported matching profile, but cannot manufacture missing calibration metadata.

For a starting profile, select a uniformly lit, known **18% neutral-grey reference in the FIRST recorded frame**. Drag/tap the preview or use the accessible numeric ROI entry. Select the reference-illuminant endpoint corresponding to the capture lighting; the UI displays Android's illuminant code. This milestone does not interpolate endpoints or estimate lighting. Sources must provide the selected forward matrix, calibration matrix, reference illuminant and neutral colour point. Missing/singular/inconsistent data fails explicitly, not through identity-matrix fallback.

The provisional conversion accounts for actual-device → reference calibration, neutral-based white balancing, the forward matrix's XYZ D50 output and Bradford adaptation to D65. In matrix notation, with actual neutral `n` normalized to green=1:

```
M = Bradford(D50→D65) · Forward · diag(1 / (Calibration⁻¹ · n))
    · Calibration⁻¹ · diag(n)
```

This matrix consumes white-balanced actual-camera RGB. The implementation checks positive neutral values, invertibility/conditioning and neutral output, and rejects clipped, dark, textured or substantially nonneutral grey regions. The grey measurement establishes scene scale; it does not measure the camera's spectral/colour response. The default provisional crop is the complete captured buffer, not an assertion that it excludes optical-black margins. A measured profile should establish the actual imaging crop and shading/defect behaviour.

The profile is labelled **manufacturer-metadata-derived / provisional**, includes source hash, ROI, chosen endpoint and the original calibration snapshot, and is shareable. A real colour-chart measurement/fit and independent colour-error validation remain separate work. Selecting a grey patch alone cannot establish ARRI sensor behaviour or a complete colour calibration.

## Android development engine

`RawSourceReader` checks every complete record CRC, lengths, metadata, timestamp order and source identity with bounded buffers. Incomplete/corrupted files are rejected; the separate desktop `--recover-tail` tool remains the explicit path for inspecting complete prefixes. App development never rewrites the source.

`RawFrameDeveloper` accepts a frame-row source and an output-row sink, independent of Android UI or media APIs. It performs per-frame black/white normalization, CFA-position white balance, bilinear reference demosaic, camera RGB → XYZ D65 → AWG3, exposure scaling, optional scene-linear reduction and the published LogC3 EI800 exposure-domain curve. Signed intermediate values and highlights above scene-linear one are retained until the final storage boundary. It uses a few source/output rows, not a full-resolution floating-point RGB framebuffer. The current implementation is CPU-only and deliberately prioritizes correctness over speed. The same row interface/reference vectors can validate a subsequent native/GPU backend; no such backend is implied here.

Every source interval and average cadence must fit the requested 24/30 fps within 3%. Encoded presentation times use CFR frame positions; the sidecar retains all original sensor timestamps and identifies that distinction. There is no retiming/upscaling/frame-duplication fallback. Orientation is recorded but not applied to pixels; rotate explicitly in the editor. RAW-derived output is video-only.

## 10-bit codec gate

Android API 33+ is required for this backend. The codec must explicitly advertise **P010 Image input** and HEVC Main10, and accept the chosen size/rate. A decoder exposing P010 Images is also required. Main10 alone, a Surface input alone, or an HLG-editing feature does not qualify this path. Devices exposing ten-bit encoding only through another interface may currently report this developer unavailable even when direct HLG recording works. That is a remaining backend-coverage task, not proof of a hardware impossibility.

The backend accesses actual plane/crop/stride metadata, handles documented two- or three-plane P010 layouts, writes 10-bit codes into the high bits of little-endian 16-bit samples, and rejects unknown layouts. No 8-bit Bitmap, YUV420 fallback, HLG surface or implicit transfer conversion is used for recorded pixels.

Before each export, a four-frame 1024×128 grayscale ramp is encoded and decoded. The positive control must preserve at least 600 distinguishable averaged ramp values, mean error ≤0.75 code and maximum error ≤2 codes. A deliberately eight-bit-degraded control traverses the same encoder/decoder and **must fail the same criteria**. This is a codec-route test, not a sensor measurement. A failed advertised route remains a failure, with reasons; a device without advertised candidates is explicitly unavailable.

The actual output is then independently decoded in full and compared to a second development of the original RAW. Every Y/Cb/Cr sample is checked after the defined 4:2:0 chroma reduction. Per-frame mean errors must be ≤4 code values for both luma and chroma, peak error ≤64, with exact frame count and CFR timestamp checks. These are reference codec acceptance tolerances, not a claim of losslessness or cinema-camera colour quality. Source/profile hashes are rechecked after development.

### Colour signalling

AWG3 LogC3 RGB is represented as limited-range 10-bit YUV using BT.709 **matrix coefficients only**. This does not mean Rec.709 primaries or transfer. HEVC VUI is explicitly reauthored to primaries=2 (unspecified), transfer=2 (unspecified), matrix=1 (BT.709 YUV coefficients), limited range. Android track colour-standard/transfer values are unspecified. This is necessary because standard HEVC identifiers do not describe this workflow.

The bounded Annex-B parser changes SPS VUI metadata, not picture data, and rewrites any repeated in-band SPS as well as configuration data. It rejects unsupported/malformed data and non-ten-bit SPS. An independent desktop x265 test verifies that metadata rewriting leaves decoded frame hashes unchanged. Main10 and all stored signal fields are inspected again from the finalized file before acceptance.

In the editor, assign **ARRI Wide Gamut 3 / LogC3, video levels**, then the desired viewing/output transform once. Do not assign HLG, LogC4 or Rec.709 primaries. A generic player's thumbnail/preview is not a colour-correct viewing transform. Editor automatic detection is not certified. The sidecar identifies the development app commit/version and contains the exact profile, source/output hashes, calibration status, transfer/gamut/range, encoder qualification, every-frame verification, timing, orientation and clipping counts.

## Acceptance and remaining gates

JVM tests cover the source/profile contract, CRC/tail rejection, signed Log math, all four mosaics, scene-linear reduction, exact plane strides/packing, metadata-derived profile provenance, cancellation, SPS rewriting and fixed Python-reference vectors. Native tests cover profile import, source retention, Activity recreation, RAW arithmetic and the actual P010 route when available. CI's dedicated evidence checker refuses to convert `unavailable` into a codec pass.

Physical S23 calibration, on-device throughput, editor interoperability, large-text review of the new screen, long-duration reliability, a live GPU preview/recording path, RAW audio synchronization, denoising/shading/defect correction, high-resolution/private HDR access and firmware changes remain unqualified. The existing SDR/HLG recorder is unchanged.

## Primary specifications

- Android CameraCharacteristics RAW calibration/forward matrices: https://developer.android.com/reference/android/hardware/camera2/CameraCharacteristics
- Android P010 image layout: https://developer.android.com/reference/android/graphics/ImageFormat#YCBCR_P010
- Android codec P010 capability: https://developer.android.com/reference/android/media/MediaCodecInfo.CodecCapabilities#COLOR_FormatYUVP010
- Android Image input/output lifetime: https://developer.android.com/reference/android/media/MediaCodec
- ARRI LogC3 transfer and AWG3: https://www.arri.com/resource/blob/31918/66f56e6abb6e5b6553929edf9aa7483e/2017-03-alexa-logc-curve-in-vfx-data.pdf
