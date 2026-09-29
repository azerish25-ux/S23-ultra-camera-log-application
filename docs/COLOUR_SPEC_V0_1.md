# Colour reference specification 0.1

**Status:** executable reference and experimental HLG identity implementation; not calibrated S23 sensor Log and not a shipping custom-Log recording format.

## Spaces and normalization

Input is already processed camera BT.2020 non-constant-luminance HLG YUV, not RAW. For ten-bit limited range, normalize `Y=(codeY−64)/876`, `Cb=(codeCb−512)/896`, and `Cr=(codeCr−512)/896`. Full-range input uses `Y=codeY/1023`, `Cb=(codeCb−512)/1023`, and `Cr=(codeCr−512)/1023`. The incoming dataspace selects which; unknown data is rejected. The sampler supplies normalized codes, so shader calculations first multiply by 1023.

Recover HLG-encoded R′G′B′ with `R′=Y+1.4746Cr`, `B′=Y+1.8814Cb`, and `G′=Y−0.164553126844Cb−0.571353126844Cr`. These are the BT.2020 NCL coefficients using Kr=0.2627 and Kb=0.0593. Chroma interpolation and camera processing remain upstream limitations.

For nonnegative HLG signal E′:

```
a = 0.17883277
b = 0.28466892
c = 0.55991073
E = E′²/3                         when E′ <= 0.5
E = (exp((E′−c)/a)+b)/12          otherwise
E′ = sqrt(3E)                    when E <= 1/12
E′ = a*ln(12E−b)+c                otherwise
```

Working values are stored in RGBA16F using high-precision arithmetic/samplers. A sign-preserving extension avoids undefined operations for negative matrix excursions in the intermediate; it is an implementation convention, not a sensor dynamic-range extension. Final RGB10 normalized output clamps to 0…1. Out-of-gamut/superwhite preservation and bit-exact lossless identity are **not** claimed. The identity recorder re-applies HLG and tags BT.2020/HLG/limited-range HEVC Main10.

## Reference custom curve, not enabled for recording

The reference curve maps normalized, nonnegative, inverse-HLG-derived working components `x` in `[0,1]` to:

```
L(x) = ln(1 + 63x) / ln(64)
x(L) = (exp(L * ln(64)) - 1) / 63
```

Black maps to0, unity to1. The domain is explicit; CPU calls reject invalid/nonfinite values. GPU reference tests use only valid input. The curve is per component and retains BT.2020 primaries. It is not a luminance-only transform, a camera exposure calibration, or a claim of recovered highlight detail. Its parameter63 is a project reference choice, not a sensor-stop specification.

There is no accepted MP4 transfer identifier/editing workflow for this project curve yet. It is never stored in a file tagged as HLG by this milestone. Unit tests verify monotonicity, endpoints and the inverse over10001 values; GPU tests compare against the CPU reference. Version and domain must accompany any future LUT/export before recording is enabled.

## Viewing transform

The initial SDR view multiplies linear BT.2020 by:

```
[ 1.660491 -0.587641 -0.072850 ]
[-0.124550  1.132900 -0.008349 ]
[-0.018151 -0.100579  1.118730 ]
```

Negative viewing components are clamped, multiplied by4, mapped with `t/(1+t)`, then encoded with the sRGB transfer function. This is a fixed practical viewing transform, not a calibrated mastering/display transform, standardized tone mapper, or exposure meter. The alternative HLG-signal view displays the encoded signal without that viewing correction and is labelled accordingly. Both write only the monitor branch. Neither changes the stored HLG recording.

## Boundaries

Image arithmetic, GPU storage precision, camera import fidelity, rendered encoder support, lossy compression error, display interpretation, physical image quality and acoustic synchronization are separate tests. Never infer all of them from a Main10 profile or a passing synthetic ramp.

Primary definitions: ITU-R BT.2100 HLG and BT.2020 NCL (https://www.itu.int/rec/R-REC-BT.2100 and https://www.itu.int/rec/R-REC-BT.2020); the executable implementation is `ColourMath` and `ColourShaders`, with acceptance tolerances in `PHASE3E1.md`.
