# Phase 3A scope and validation

This change is capture-integrity work, not the Phase 3B automated phone acceptance runner or Phase 3C Log transform. It does not claim new sensor, HDR, RAW, audio or thermal support.

## Media state boundaries

`VideoFinalizer` independently tracks publication/recovery and report persistence. Only a successful verification with no capture/finalization error can publish. A reporting failure is a warning; it never invokes discard. Failed format checks, encoding interruption, and publication failure preserve nonempty staged video with an explicit recovery label. Retention failure does not trigger additional destructive cleanup. Private files and pending-copy journals survive until cleanup is confirmed. Uninstalling the app remains destructive to private files.

A successful gallery copy briefly requires roughly twice the video's storage. This favours retention over a zero-copy publish. There is no guarantee an interrupted MP4 is decodable; export is provided for inspection/recovery, not as a claim of completeness. Recovery UI requires confirmation to delete. Startup recovery runs off the UI thread and finishes before camera discovery/new captures.

## Controls

Preview and recording read the same selected-mode frame rate. Preview sizes must match its aspect ratio and advertised timing. Unknown timing remains advisory. Reopening checks fresh capabilities; recorded results remain the source of actual settings.

Manual exposure first establishes AE and, where needed, a triggered AF lock and converged AWB. It then fixes focus and waits for AWB lock/preset acknowledgement while AE is still on, and finally waits for manual sensor result acknowledgement. Every stage has a five-second deadline; request/session generations invalidate obsolete callbacks. Absent metadata and focus failure cannot count as confirmation. A failed transition restores an explicit auto-exposure state. Changing exposure strategy during recording is rejected rather than temporarily metering within a clip.

The logical camera's physical override key list gates independent sensor/focus control. Requests including overrides use the physical-ID-set builder. Keys not individually overridable remain common logical settings; no independent WB calibration is claimed.

## Tests

JVM regression tests exercise finalization order and fault handling, cleanup retry policy, each transition gate/deadline, stream-query isolation, and nested error counts. Instrumented tests add real private-file retention/recovery, path containment, an actual recording whose sidecar directory is blocked, and selected mode/control-intent restoration. The report-failure test decodes retained published video and cleans only its own temporary outputs. The original twelve-recording acceptance gate remains in place. ADB video evidence transfer retries at most three times into separate temporary directories; a failed or empty transfer cannot count as acceptance, and capture tests are never retried or bypassed by this transport helper.

Hardware acceptance remains separate: verify 24/30-fps long-shutter behaviour, focus/WB locks, logical/physical routes, and low-storage recovery on the actual phone. Emulator/policy tests are not Galaxy S23 Ultra certification.

## API contracts

- https://developer.android.com/reference/android/hardware/camera2/CaptureRequest (AF trigger, AWB lock, AE-off recommendations)
- https://developer.android.com/reference/android/hardware/camera2/CaptureResult (lock and applied-setting acknowledgement)
- https://developer.android.com/reference/android/hardware/camera2/CameraCharacteristics#getAvailablePhysicalCameraRequestKeys()
- https://developer.android.com/reference/android/hardware/camera2/CaptureRequest.Builder#setPhysicalCameraKey(android.hardware.camera2.CaptureRequest.Key,T,java.lang.String)
