# Auto-exposure compensation

The Controls drawer offers integer camera-advertised AE compensation steps, labelled with the exact advertised rational EV step. Only routes with independently settable compensation, a valid nonzero range spanning zero, and a positive rational step expose the slider. A physical route does not inherit unsupported logical-camera adjustment and claim independent control.

The control is a draft until Apply. It is disabled in manual-exposure drafts because AE compensation does not control brightness with AE off. Camera requests bound saved intent to fresh capabilities; an unsupported nonzero request is explicitly rejected. Per-camera persistence defaults older settings to zero. Requested and effective step counts are retained separately.

Current capture-result step count and AE state are shown independently, and the recording journal retains them. A reported result is never clipped to the advertised range for display. Missing metadata remains unknown. Searching/converged/locked describe the camera algorithm's state, not a calibrated brightness or image-quality test. A camera may take multiple frames to settle after a change.

Pure tests cover rational conversion, discrete round trips, bounds, overflow-safe slider positions and invalid capability rejection. The native test asserts disabled UI on an unavailable route; when advertised, it submits a nonzero draft, records, and checks the result metadata in the original report. The artifact explicitly distinguishes unavailable from capture-result-matched, and never certifies physical brightness.

API semantics: [Android CaptureResult AE compensation](https://developer.android.com/reference/android/hardware/camera2/CaptureResult#CONTROL_AE_EXPOSURE_COMPENSATION).
