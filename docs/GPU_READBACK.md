# RGB10 precision readback

The Phase 3E.1 precision gate renders the production FP16 working image into an actual RGB10_A2 texture. The checker still requires a monotonic 1024-pixel ramp, maximum normalized error at most 1.25/1023, and at least 768 distinct ten-bit codes. The RGBA8 negative control must fail those same requirements. No threshold was lowered.

## Failure isolated

Hosted run [36652659014](https://github.com/azerish25-ux/S23-ultra-camera-log-application/actions/runs/36652659014) on `a48d706f86ed7df65c6008da1e0db2e4314605dd` passed JVM tests, both lint variants and APK/signature checks. Its emulator campaign passed 25 of 26 tests; the precision ramp failed with eight distinct levels and non-monotonic output.

A standalone host EGL reproduction against the installed Android emulator 37.1.11 SwiftShader library isolated its packed `GL_RGBA` / `GL_UNSIGNED_INT_2_10_10_10_REV` readback. The driver advertised that pair and returned no GL error, but left the destination buffer unchanged. Reading the same rendered target as bytes showed the expected gradient. Sampling that RGB10 texture into an FP16 framebuffer and reading floats recovered all 1024 codes with zero code error. Repeating with an RGBA8 working image produced 246 distinct codes and a maximum 78-code error, correctly failing the unchanged gate.

These are host renderer observations, not physical phone measurements or the Android instrumentation acceptance result.

## Supported diagnostic path

`GlTools.readRgb10Texture` samples the existing quantized RGB10 texture with the copy shader into a temporary FP16 framebuffer. It reads normalized floating-point samples, validates their domain, and reconstructs the ten-bit RGB and two-bit alpha codes. The source texture is not modified or bypassed. The temporary objects are released even if readback fails.

This small copy occurs only in setup/test probes. It does not add CPU readbacks to live full-resolution camera processing, change encoding, or certify camera input precision. The report identifies the readback method as `quantized_texture_sample_via_FP16`. The actual camera and HDR encoder hardware gates remain separate.
