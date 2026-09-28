# Phase 2 acceptance and remaining hardware work

## Evidence boundaries

The code contains SDR and HLG10 recording paths, output validation, and a bounded RAW-still path. Metadata discovery alone must never be reported as tested device support. A green emulator test is proof of an emulator path only. Record the phone model, firmware/build, camera ID/physical route, codec, resolution, rate, controls, Android version, and app commit with each real-device result.

Current scope is video only (no microphone permission), WB presets/lock (not calibrated Kelvin), and sequential DNG stills (not RAW video). HLG10 is processed HDR, not Samsung's proprietary log pipeline or a custom log transform.

## Run on an S23 Ultra

1. Export complete diagnostics and retain JSON plus text. Unsupported, not reported, and failed queries must remain distinguishable. Confirm every output size is retained.
2. For every accessible lens, test preview, lens switching, front-camera mirroring, rotation, leaving/reopening the app, denied/revoked Camera permission, and camera-in-use errors. Never infer a camera ID from a lens marketing label.
3. Set supported ISO, shutter and focus, then confirm the **APPLIED** values and capture validation metadata. Check unsupported controls are unavailable. Video shutter is limited by the frame interval.
4. Record a supported SDR mode for at least 60 seconds, then 10 start/stop cycles. Play every file, run `scripts/check_video.py --min-duration 60` for the long sample, inspect frame timing and dropped-frame intervals, and confirm no unfinished gallery entries.
5. Record for several seconds, rotate or background the activity, then verify that finalization creates a playable file and preview can reopen. Stop immediately after Record to check that empty captures are rejected and deleted. Test nearly-full storage and a simulated write failure; retain error reports without claiming the output was saved.
6. If HLG10 is advertised, explicitly select it and record. Check actual SPS 10-bit luma/chroma, HEVC, BT.2020 primaries, HLG transfer, limited range, frame rate, and preview behavior. Unsupported combinations must show a reason, never silently produce SDR. Independently run `check_video.py --expect-hlg10` and inspect the clip in a color-managed editor.
7. If RAW_SENSOR is exposed, capture one DNG and five sequential DNGs. Open the DNGs in a RAW decoder, inspect pixel values, black/white levels and color metadata, and compare image/result timestamps. The app checks TIFF header and pairing, not full external RAW rendering. Retain the sequence timing report; file serialization makes this a sequential-still measurement, not sustainable RAW-video throughput.
8. For any advertised 4K mode, repeat the duration test and log temperature, sustained fps, file size, battery state and storage conditions. Long-run quality and thermal stability remain hardware tests.

## Implemented safeguards to check

- Results from closed camera/session generations are ignored and resources closed.
- Scans survive activity recreation; save errors do not discard a successful scan or leave Run disabled.
- Pending outputs are journaled before recording and cleaned after failure/process recovery. Completed MediaStore files are never removed by pending-output recovery.
- FileProvider exports only `files/exports/`; it is not an export of all app storage.
- Codec draining has no-frame and EOS deadlines. Sensor image ownership is bounded.
- HLG10 classification uses explicit profiles/capability, not every non-STANDARD profile.
- Session/camera frame-rate metadata is advisory until the actual file is inspected.

## Next milestone, after these capture paths are established

Choose a measured input path. A RAW-derived implementation needs black-level handling, demosaic, white balance, calibrated color conversion and a documented log encoding. An HLG-derived transform starts from processed HDR and must be labeled accordingly. Add an inverse transform/LUT, reference test vectors and controlled highlight/noise/color experiments. Merely flattening an SDR image does not establish additional captured dynamic range.
