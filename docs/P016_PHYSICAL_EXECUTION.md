# P016 physical execution protocol

This protocol converts P016 from a synthetic host fixture into an executable,
fail-closed Galaxy S23 Ultra laboratory run. It does **not** contain a phone
result. A result exists only after the exact APK revision is run on an
`SM-S918*` device and the pulled media passes the independent host validator.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This
protocol implements its P016 method and TC-P016-01 through TC-P016-08 without
replacing the existing camera, recorder, validation, retention, or evidence
adapters.

## What was added

- `P016PhysicalQualificationTest` is an opt-in Android instrumentation test. It
  is skipped unless `p016Physical=true` is supplied. It refuses non-Samsung or
  non-`SM-S918*` hardware and refuses an APK that is not bound to a 40-character
  commit revision.
- The test discovers a real rear route, chooses a conservative public SDR,
  direct, non-manual configuration no larger than 1080p30, requests mono
  48 kHz audio, records for 65 seconds, and retains the existing validation and
  recording-attempt reports.
- Before and after capture it records the device build fingerprint, Android
  version, battery state, thermal status, elapsed time, and available storage.
- It copies the published MP4, validation report, and attempt report into one
  new app-specific bundle, computes SHA-256/byte-count identities, and leaves
  physical qualification explicitly pending.
- `p016_physical_qualification.py` independently checks bundle identities,
  fully decodes the complete video and audio tracks, recomputes packet cadence,
  and detects repeated flash/tone events before it can emit an exact-slice
  qualification.
- `p016-marker.html` is the offline second-screen marker. It flashes the entire
  screen and emits a 1 kHz tone at 10, 20, 30, 40, 50, and 60 seconds.

Production capture behavior is not altered by this phase. The added Android
source is test-only and uses the existing camera engine and evidence seams.

## Required laboratory setup

1. Use a real Galaxy S23 Ultra whose model begins with `SM-S918`.
2. Enable USB debugging and authorize the host computer.
3. Install Android platform tools, the repository's pinned Android SDK, Java,
   FFmpeg, FFprobe, Python 3, and Git.
4. Use a second computer, tablet, or phone as the marker display and speaker.
   Open `docs/p016-marker.html` locally; no network service is required.
5. Frame the complete marker screen in the S23 Ultra preview. Raise the marker
   display brightness and speaker volume. Avoid automatic screen dimming.
6. Run from a clean `main` checkout so the APK and report are tied to one exact
   commit.

## One-command execution

```sh
scripts/run_p016_physical_qualification.sh
```

For multiple connected devices:

```sh
scripts/run_p016_physical_qualification.sh --serial DEVICE_SERIAL
```

The runner:

1. rejects a dirty tree, a non-`main` checkout, the wrong phone model, or an
   ambiguous ADB target;
2. builds the debug and instrumentation APKs with
   `-PsourceRevision=$(git rev-parse HEAD)`;
3. installs both APKs before asking the operator to start the marker sequence;
4. executes only `P016PhysicalQualificationTest` with explicit physical and
   marker-ready arguments;
5. pulls `/sdcard/Android/data/com.s23log.probe/files/p016/<run-id>/` into
   `evidence/p016/<run-id>/`;
6. runs the independent host decoder and marker/cadence analysis.

The `--marker-ready` switch only suppresses the prompt. It is not evidence that
markers were recorded; the host detector must still find at least two paired
flash/tone events.

## Device bundle

A successful device-side capture produces:

- `capture.mp4` — the exact published recording;
- `recording-validation.json` — existing on-device container/sample and
  first-frame/first-audio-decode checks;
- `recording-attempt.json` — existing independent stage evidence;
- `device-capture.json` — P016 device/build/route/mode/environment bindings and
  the three file identities.

`device-capture.json` must retain these false values:

```json
{
  "fullDecodeVerified": false,
  "markerEventsVerified": false,
  "physicalConfigurationQualified": false,
  "enduranceCertified": false,
  "higherResolutionQualified": false
}
```

The phone cannot promote its own output into independent host qualification.

## Host acceptance boundary

The host report is `p016-qualification.json`. It reaches
`qualified_exact_60s_slice` only when all of the following hold:

- exact revision, model, build fingerprint, route, mode, and file identities
  agree across the bundle;
- the route is rear-facing and the selected tuple is conservative SDR direct
  processing, no larger than 1080p30, without unconfirmed manual timing;
- the decoded container and video packet span are at least 60 seconds;
- every selected video and audio track fully decodes without FFmpeg errors;
- exactly one requested 48 kHz mono track exists;
- output geometry equals the selected mode;
- at least two repeated visible/acoustic marker events are independently
  detected;
- video packet timestamps are strictly increasing and cadence is within the
  declared 3%/gap boundary;
- thermal and storage observations exist before and after the run.

A fully decodable take with a cadence gap is retained as
`slice_retained_cadence_warning`; it does not receive exact-configuration
qualification. A first-frame-only result, stale revision, wrong geometry,
missing audio, absent markers, or wrong device withholds the phase result.

## Deliberate non-claims

Even a passing report applies only to the exact phone build, route, codec,
size, rate, profile, duration, conditions, and application revision in that
bundle. It does not certify:

- warm/repeated operation or long-duration endurance;
- unlimited recording;
- other lenses, 4K, 8K, HDR, high-speed, or GPU paths;
- calibrated physical audiovisual synchronization—the marker display,
  speaker, acoustic path, and camera latencies are not calibrated;
- sensor-derived Log, ten-bit sensor precision, dynamic-range improvement,
  film-stock fidelity, or cinema-camera equivalence.

The committed host and emulator tests verify the harness and its negative
controls. They are not a substitute for running this protocol on the phone.
