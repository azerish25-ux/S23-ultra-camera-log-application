# Continuous RAW lab and offline LogC3 developer (0.7)

## Version 0.8 addition

The original desktop developer remains available. Android now offers [on-device saved-source LogC3 development](ON_DEVICE_LOGC3.md) with explicit profile and P010 codec gates. The continuous RAW experiment itself is still bounded and video-only; no live Log recorder or physical calibration is implied.

## What ships in the original 0.7 path

An opt-in, five-second **continuous Camera2 RAW acquisition experiment**, with separate acquisition-only and source-saving modes. The existing DNG still buttons and direct SDR/HLG/audio recorder are unchanged. RAW source is developed **on a computer**, not encoded into Log on the phone. No Samsung/ARRI sensor equivalence, physical S23 qualification, real-time Log, 4K/8K throughput or additional firmware access is certified.

A genuine camera colour profile and physical RAW sample are still required to produce a **calibrated phone clip**. The repository deliberately does not invent a Samsung colour matrix. Synthetic test clips validate software and codecs only.

## Phone workflow

1. Select a lens. Apply manual ISO/shutter and supported focus/white-balance settings; wait for actual sensor-result confirmation.
2. In Settings & exports choose **Continuous RAW lab**. Start with **Acquire only** to separate camera delivery from storage throughput. This saves a report, not image pixels.
3. Choose an advertised RAW size and 24/30 fps. Every candidate is rechecked against the actual RAW stream map, timing, memory and storage. Unsupported candidates explain the rejection. The old 24 MP DNG ceiling is not applied to this separate path.
4. Choose **Save RAW source** for the retained sensor sequence. The dialog discloses the uncompressed payload estimate, five-second limit, paused preview and **no audio**. Existing microphone selection is not changed.
5. **Stop RAW** stays in the capture dock. Leaving the activity stops acquisition and drains retained frames. Storage reserve and severe thermal pressure also stop it; thermal protection is not disabled.
6. Open **Retained RAW sequences** to export the `.s23raw` file and original validation report. Interrupted files are listed too. Export before uninstalling, which removes private data. Deletion requires a separate confirmation. Stop recording before exporting.

The experiment holds at most three acquired Android Images, copies into a preallocated bounded pool, closes each Image promptly, and joins frame metadata using the exact sensor timestamp. Camera callbacks never wait for disk writes. Pool exhaustion, missing pairs, failed requests, changed manual exposure and writer failures stop acquisition explicitly. Only completed frame records count as written. Current implementation copies on the acquisition owner thread; a slow copy is a possible cadence bottleneck, not evidence that the sensor cannot run faster. Large native ImageReader allocations and OEM behaviour still require physical testing.

This milestone uses ordinary RAW_SENSOR sessions and conventional declared Bayer arrangements only. It does not enable maximum-resolution pixel modes, proprietary HDR readouts, high-speed RAW or hidden physical camera IDs. A minimum duration of zero means timing was not established; measured cadence remains authoritative. Three copied 8K buffers may exceed the app's heap allowance even when the acquisition-only mode is available. No lower-resolution fallback, upscaling or frame duplication is hidden.

## Host setup and inspection

Python 3.11 or newer, NumPy, FFmpeg and FFprobe are required. FFmpeg must provide FFV1 and, for MP4, libx265. A virtual environment is recommended:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r scripts/requirements-raw.txt
python scripts/raw_to_logc3.py take.s23raw --inspect
```

On Windows use `.venv\Scripts\activate` instead of the shell activation command. Inspection verifies every complete frame CRC and reports the source header/count. It does not claim colour calibration or real-time qualification. `--recover-tail` explicitly permits ignoring only an incomplete final record; checksum corruption, invalid dimensions or regressing timestamps still fail. It never changes the source file.

## Calibrated profile contract

The developer accepts a JSON object with the following fields. These are requirements, not example Samsung calibration values:

| Field | Required meaning |
| --- | --- |
| `schemaVersion`, `kind` | `1`, `raw-colour-profile` |
| `source` | Exact `fingerprint`, `logicalCamera`, nullable `physicalCamera`, `width`, `height`, `cfa` copied from inspection |
| `calibration` | `status: measured`, nonempty `evidence` identifying retained measurement records, and `illuminant` |
| `cameraToXyzD65` | Measured 3×3 row-major matrix mapping white-balanced, black-subtracted, white-level-normalized camera RGB to XYZ D65 |
| `bayerWhiteBalance` | Four gains in the source 2×2 mosaic's row-major order, **not always R,G,G,B** |
| `sceneScale` | Positive exposure normalization establishing scene-linear 18% grey, consistent with the matrix and retained grey reference |
| `crop` | `[left, top, width, height]` in RAW buffer coordinates; even coordinates/dimensions preserving mosaic phase, inside the captured buffer |
| `iso`, `exposureNs` | Calibration capture settings; each frame must remain within the documented 5% tolerance |

Use a known-illuminant chart and neutral/grey references to determine white balance, camera-to-XYZ colour conversion and scene scale. Retain the RAW chart data, measured/reference XYZ values, transform fit, held-out colour errors, clipping/noise tests and test illuminant alongside the profile. A profile's `measured` label is a supplied assertion, **not independently certified by this program**. It does not validate a matrix merely because it is invertible. A camera2 colour-correction matrix is not automatically this scene-referred camera-to-XYZ profile. Sensor active-array coordinates are recorded, but their correspondence to a binned/cropped output must be established on the phone before choosing the crop.

`--allow-provisional` accepts a profile explicitly marked `provisional` for uncalibrated research. No provisional matrix is supplied. A synthetic profile is accepted only for an input declaring the synthetic fixture device; it must not be used for actual phone footage. The exact profile and its hash travel with every output. There is no built-in, physically validated S23 profile yet.

## Development and editing

```sh
# Lossless 16-bit RGB reference master (no YUV subsampling):
python scripts/raw_to_logc3.py take.s23raw --profile phone-profile.json --output take-logc3.mkv

# More readily editable 10-bit HEVC MP4, with 4:2:0 chroma subsampling:
python scripts/raw_to_logc3.py take.s23raw --profile phone-profile.json --codec hevc10 --output take-logc3.mp4
```

The developer performs per-frame black/white normalization, Bayer-position white balance, bilinear reference demosaic, camera RGB → XYZ D65 → AWG3 conversion, scene scaling and the published **LogC3 EI800 exposure-domain** curve. EI800 describes this output encoding convention, not a demand that the phone sensor use ISO800. Negative intermediate values and scene-linear values above one are retained up to encoding. Values outside the final normalized storage range fail unless `--allow-output-clipping` is explicitly supplied; all clipped samples are counted. This is a reference demosaic, not final production denoising, lens shading, hot-pixel correction or highlight reconstruction.

Output is RGB16 FFV1/full levels or HEVC Main10/video levels. HEVC uses BT.709 **YUV matrix coefficients** solely for RGB↔YUV representation; that does **not** identify the RGB primaries as Rec.709. Both transfer and RGB-primaries tags are unspecified because these public codec identifiers do not describe the custom workflow. Never tag these samples as HLG/BT.2020 to make an encoder accept them.

Import using **ARRI Wide Gamut 3 / LogC3**, the stated data levels, and the accompanying `.logc3.json` sidecar. Apply a suitable viewing/output transform exactly once. Do not assign LogC4 or HLG. Orientation is recorded but not applied to pixels; rotate in the editor. Player thumbnails without this colour interpretation are not display-correct. Editor-specific automatic detection is not certified.

Every output is independently fully decoded before publication. FFV1 decoded RGB must match every submitted frame exactly. HEVC must decode to ten-bit pixels and meet the declared per-frame mean RGB error bound (0.02); this lossy/subsampled check is not sensor precision or colour-quality certification. Source/profile/output hashes, original timestamps, clipping counts and transform contracts are in the sidecar. Existing output files are never overwritten. Publishing a sidecar failure does not delete a newly generated usable video.

Output uses the requested constant frame rate. Source intervals and average cadence must be within 3%; otherwise development fails unless `--allow-retime` explicitly authorizes re-spacing frames. Every original timestamp is retained; no missing frame is synthesized. Even an accepted CFR mapping is distinct from preserving every original timestamp exactly. Sources are video-only.

## Append-only source format

All integers are little-endian. The header is ASCII `S23RAW01`, a uint32 JSON byte length, then UTF-8 JSON (at most 1 MiB). Each frame is ASCII `FRM1`, uint32 metadata length, uint64 pixel payload length, UTF-8 JSON metadata, tightly packed uint16le Bayer samples and uint32 CRC32. CRC32 covers the 12 length bytes, metadata and pixel payload. The header is not CRC-protected; the exported source SHA-256 identifies the complete source at development time. Neither checksum authenticates device origin.

Metadata records sensor timestamp, frame number, actual exposure and ISO, frame duration when provided, four black levels, white level and available WB metadata. uint16 storage is not a claim of 16 meaningful sensor bits. Writer finalization never rewrites a global frame count, allowing explicit inspection/recovery of complete prefix records after interruption. A truncated or zero-frame file is retained but cannot masquerade as a completed movie.

## Reproducible software evidence

```sh
python -m unittest discover -s scripts/tests -v
python scripts/raw_fixture.py evidence/raw-logc3
python scripts/raw_to_logc3.py evidence/raw-logc3/synthetic.s23raw --profile evidence/raw-logc3/synthetic-profile.json --output evidence/raw-logc3/synthetic-logc3.mkv
python scripts/raw_to_logc3.py evidence/raw-logc3/synthetic.s23raw --profile evidence/raw-logc3/synthetic-profile.json --codec hevc10 --output evidence/raw-logc3/synthetic-logc3.mp4
```

Fixtures explicitly declare `SYNTHETIC_FIXTURE`. Tests include known LogC3 values/inverse, signed toe/highlights, all four mosaics, a ten-bit ramp and degraded eight-bit negative control, CRC/truncation rejection, exact profile binding, retiming/clipping gates, independent full codec decode and no-overwrite checks. JVM tests cover pool budgets, timestamp ownership and the binary record layout. CI also preserves the existing Android build, lint and emulator campaign. **Neither a synthetic clip nor a green emulator proves a physical S23 RAW recording.**

Next device gate: export source and report from acquisition-only and saved-frame runs on the exact phone, establish crop and sensor calibration, and evaluate cadence, shading, image defects, clipping, shadow noise and heat. Only then qualify higher resolutions or implement real-time GPU RAW-to-Log encoding. This milestone performs no firmware flashing.

## Primary specifications

- ARRI, *ALEXA Log C Curve — Usage in VFX*, March 2017, exposure-domain EI800 coefficients and AWG3 matrices: https://www.arri.com/resource/blob/31918/66f56e6abb6e5b6553929edf9aa7483e/2017-03-alexa-logc-curve-in-vfx-data.pdf
- Android RAW_SENSOR layout: https://developer.android.com/reference/android/graphics/ImageFormat#RAW_SENSOR
- Camera2 repeating requests: https://developer.android.com/reference/android/hardware/camera2/CameraCaptureSession#setRepeatingRequest(android.hardware.camera2.CaptureRequest,android.hardware.camera2.CameraCaptureSession.CaptureCallback,android.os.Handler)
- x265 VUI colour parameters: https://x265.readthedocs.io/en/stable/cli.html#vui-video-usability-information-options
