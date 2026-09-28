# Reproducible Phase 2 verification

The workflow builds debug/release APKs, runs both lint variants, runs JVM and device tests, and validates the debug signature before emulator work. Host-side validator regressions run with:

```sh
python3 -m unittest discover -s scripts/tests -v
```

The API 36 emulator tests perform ten independent recordings, one 65-second recording, one lifecycle-finalized recording, preview recovery, probe restoration/sharing, and FileProvider containment checks. These are tests of an emulated camera and encoder, not physical Galaxy S23 Ultra or HLG10/RAW performance certification.

## Retaining device evidence

The pinned AGP 9.4 connected-test invocation sets `android.injected.androidTest.leaveApksInstalledAfterRun=true`. The default removes APKs after testing, which also removes the target app's private reports. Reinstalling the APK afterward would not recover those reports.

On successful tests the script requires the installed package, saves a nonempty private-report tar, pulls the recorded movies, independently validates them, and captures the reopened camera screen. Cleanup preserves the original exit status and never replaces a completed archive with an empty best-effort one. Failure logs and any partial archive remain explicitly named as partial evidence.

The GitHub `S23Log-verification` artifact includes:

- Exact source archive, commit SHA and Git tree; JVM/device XML results and lint reports.
- Emulator logs, a PNG camera screenshot and a tar of app-owned exports/preferences.
- Twelve recorded MP4s, full-decode results in `ffprobe.json`, and `summary.json`.

`check_evidence.py` rejects missing/rejected recording reports, missing JSON/text probe pairs, absent full-decode results, and a missing sixty-second recording. It reads regular report files inside the tar without extracting paths. Report/file count agreement is checked; it does not claim cryptographic one-to-one provenance between reports and movies.

## Independent video checks

```sh
python3 scripts/check_video.py /path/to/recordings --min-duration 1
python3 scripts/check_video.py /path/to/long.mp4 --min-duration 60
python3 scripts/check_video.py /path/to/hlg.mp4 --min-duration 60 --expect-hlg10
```

These commands require FFmpeg/ffprobe. They check finite duration, exactly one video track, every packet's presentation timestamp, packet-span duration, and an error-free full decode. HLG10 additionally requires HEVC 10-bit 4:2:0 and BT.2020/HLG/limited-range tags. The strictly increasing packet PTS policy is intentional for this recorder's no-B-frame mode, not a general validator for all third-party videos.

Full decoding preserves the source time base and passes every frame through: it does not round variable-rate timestamps to a nominal constant rate, duplicate/drop frames, or stop after one frame. Measured frame rate remains measured evidence, not a promise of 30 fps or thermal stability. Image quality, sensor behavior, HLG/RAW operation and sustained phone performance still require the device acceptance plan.
