# Phase 3B — mode planning and capture-screen foundation

## Implemented scope

Public ordinary Camera2 output sizes are no longer reduced to a four-size whitelist. The planner evaluates the full advertised size list plus explicit 7680×4320 targets, at 24/30 and other ordinary candidate rates (25/50/60 and reported AE endpoints through 60). Missing 8K, insufficient timing, unavailable HDR, incompatible encoders and preview failures are exported as structured reasons. This is not a maximum-resolution-sensor or constrained-high-speed session implementation.

SDR AVC, SDR HEVC Main and HLG HEVC Main10 are separate choices. Encoder alternatives remain explicit; configuration failure does not silently change codec, size, frame rate or colour profile. Candidates remain advertised, not certified.

An exact AE range is preferred, followed by a variable range ending at the target. A containing range such as 15–30 does not establish fixed 24 fps. With advertised manual controls and known sensor limits, a separate manual-timing candidate may be offered. During its AE focus/WB preflight the app does not claim that the target cadence is active. Recording requires applied manual exposure. Requested, effective/clamped and latest sensor controls are exported separately.

Record/Stop and elapsed time stay in a fixed portrait dock or landscape rail. Controls overlay the viewfinder without replacing its TextureView. Mode evidence is available on demand and exportable as JSON. RAW still and recovery controls remain available in the panel. This is the capture-screen foundation, not a completed clip library, touch focus, scopes or direct-control dial redesign.

The first successfully muxed payload acknowledges recording. Session configuration alone leaves the app STARTING; late callbacks cannot revive a stopped capture. A user-confirmed test uses the same recording pipeline and stops approximately five seconds after acknowledgement. It creates real footage, uses storage and has no audio. Cancel does not start a recording.

Validation schema 2 adds device/firmware/source identity and cadence status. `checked` continues to mean file integrity, not proven cadence or sustained image quality. `within_tolerance` requires two seconds, mean rate within 3% and no >1.5-period gaps; warning and insufficient-duration results preserve readable footage.

## Verification

The existing Gradle unit/lint/build/instrumentation workflow remains authoritative. New JUnit cases cover the rate policy, mode identity, first-sample gate and cadence classification. Framework tests exercise the persistent recording dock in landscape and an explicitly confirmed short recording with first-sample evidence. Existing media-recovery and sidecar-failure tests remain enabled.

For an offline policy sanity check with Kotlin CLI installed:

```sh
kotlinc app/src/main/java/com/s23log/probe/core/*.kt scripts/core_smoke.kt -include-runtime -d /tmp/s23-core-smoke.jar
java -jar /tmp/s23-core-smoke.jar
python3 -m unittest discover -s scripts/tests -v
```

These commands do not replace the Android build or instrumentation tests.

## Physical-device gate

On the S23 Ultra, export Diagnostics and Mode evidence. Select each actual 8K24/8K30 candidate and confirm Test 5 seconds. Export the clip and its validation; record failures and their exact mode rather than guessing a lens ID or inferring success from advertisements. Test each codec and colour profile separately, including manual timing where necessary. Then perform the longer tests in DEVICE_TEST_PLAN.md.

No physical S23 Ultra capture or 8K/HLG performance result is claimed by this implementation. HLG remains processed HDR, not proprietary Samsung Log or a custom Log curve. Audio, Log processing, continuous HDR monitoring, thermal/storage budgets and signed-release acceptance are subsequent milestones.
