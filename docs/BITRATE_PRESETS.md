# Bounded encoder bitrate targets

Controls offers Low, Standard and High targets. Standard preserves the catalog's existing resolution/rate/codec baseline. Low requests half that baseline and High requests 1.5 times it, using overflow-safe arithmetic. Every target is bounded by the selected encoder's advertised bitrate range, then checked as part of the complete MediaFormat. A codec-limit label identifies clamping.

A preset is a target, not a measured output bitrate, quality certification or guaranteed file size. The encoder's rate-control behavior and scene complexity still matter. Storage safety uses the configured target with its independent reserve policy; it cannot guarantee remaining recording time. If a saved format is unavailable, changing the preset must recover that same format; it cannot silently replace it. A first-run route without any saved format may choose an advertised initial default.

Changing a preset is allowed only in an idle preview. It retains the exact selected format key, camera and colour path. If that combination is unsupported, the previous selection is retained and an explicit rejection appears. It does not silently choose another codec, frame rate or resolution. When no format was available, choosing another preset can recover an advertised candidate and rebuild preview. The successful preset is saved locally. Recording rejects stale full-format intent even when the compatibility key matches.

Each validation report records the target, Standard baseline, preset, encoder bounds and whether the target was limited. Original mode keys stay compatible with saved selections. Manual exposure still requires matching camera-result evidence before Record is enabled, including on normally auto-exposure-capable modes.

## Verification

Pure tests cover bounded targets, noncompounding changes, integer overflow, unchanged format/colour identity and manual readiness. The Android test changes the preset on a real emulator preview, verifies there was no implicit capture or format substitution, records and validates a clip, and checks its retained target and bounds. Physical S23 Ultra quality, bitrate stability and 4K/8K throughput remain separate device acceptance evidence.
