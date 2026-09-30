# Versioned reference forward/inverse LUT export

Controls → Prepare reference LUTs creates five application-owned files off the UI thread. Completion does not launch a sharing destination. Share reference LUTs then opens the normal user-selected share chooser. Preparation survives an observer/activity detachment; failures stay explicit and never enable sharing a partial bundle.

- `linear-bt2020-to-reference-log.cube`: the analytic S23Log-reference-0.1 curve, sampled into 8192 1D RGB entries.
- `reference-log-to-linear-bt2020.cube`: its inverse, with the same entry count.
- `reference-vectors.csv`: 1025 analytic forward/inverse vectors.
- `README.txt`: exact input/output domains, workflow exclusions and remaining acceptance gates.
- `manifest.json`: version, app revision, domains, interpolation, primaries and SHA-256/byte-count identities for the four content files.

The app **does not record this custom curve**. These assets are not a viewing LUT for existing HLG/SDR recordings or proprietary Samsung Log. The forward input is normalized linear BT.2020 RGB in [0,1]; the inverse expects that exact reference curve and returns linear BT.2020. Neither performs range conversion, gamut conversion, display tone mapping, sensor calibration or highlight recovery. Out-of-domain preservation is undefined. An inverse result is linear data, not a finished display image.

## Verification

Pure tests check monotonicity/endpoints, locale-independent deterministic bytes, analytic vectors, and linear-interpolated errors over 10001 values. The native export test checks application-owned lifecycle behavior and identities through FileProvider content URIs. CI then checks the actual exported archive, exact revision, domains, identity pairing, and both LUTs with the independent FFmpeg `lut1d` consumer. It compares 10001 planar float RGB values against analytic forward/inverse/round-trip results. These checks verify mathematical assets, not a calibrated camera/editor workflow.

The 8192-entry density was chosen to keep analytic interpolated round-trip error below 3e-7; this was improved rather than relaxing the test after the initial 4096-entry version exceeded that bound. FFmpeg's separately declared tolerances include float-consumer arithmetic. Results and measured errors are retained in `reference-luts-summary.json`.

Primary consumer documentation: [FFmpeg lut1d](https://ffmpeg.org/ffmpeg-filters.html#lut1d). The curve and normalization are defined in [the project colour specification](COLOUR_SPEC_V0_1.md). Container/sidecar interpretation, a measured camera input and real editor/device image-quality acceptance are still required before enabling custom-Log recording.
