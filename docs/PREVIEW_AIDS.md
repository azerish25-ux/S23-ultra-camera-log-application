# Preview monitoring aids

The capture screen's **Aids** control offers a thirds grid, advisory level, histogram, waveform, 95% display-code zebras, display false colour and low-resolution edge peaking. Selections persist across recreation. Everything is off by default.

These tools inspect the displayed preview, not sensor RAW, scene-linear exposure, encoded HLG precision or a calibrated Log signal. Changing the display transform can change these scopes. Zebras mark RGB8 display codes at or above 243/255; they do not prove sensor highlight clipping. False-colour bands and edge peaking are display aids, not exposure stops, skin-tone calibration or optical-focus certification.

## Bounded execution and lifecycle

Only pixel-based aids sample the TextureView, at most four 160×90 RGB8 copies per second. One bounded worker analyzes the samples. The grid follows the aspect-fit image bounds rather than the outer view. Preview padding is transparent and excluded, and images older than 750 ms are not shown as fresh scopes. Grid and level alone do not read pixels. Missing display frames and unavailable/flat/unreliable level data remain explicit.

The level uses the device gravity sensor, falling back to filtered accelerometer input, with Android display-axis remapping. It is advisory and not physically calibrated. Sensor listeners and analysis stop when the capture view is inactive; stale callbacks cannot repopulate a stopped/recreated view. No full-resolution CPU frame readbacks are introduced.

The overlays are a separate native View above TextureView. They are never submitted as camera/encoder surfaces. The recording colour path is unchanged, but added preview work can still affect performance; complete mode-plus-aids throughput must be measured on the actual phone. The GPU processor's zero-readback count describes that recording processor only; these optional reduced-resolution display copies are separate.

Recording reports retain the initial aid selection and up to 128 subsequent selection changes with monotonic timestamps. Overflow is counted explicitly rather than implying a complete history. These configuration records are not measurements of optical colour quality or sustained performance.

## Verification scope

Pure tests cover histogram/waveform counts, padding, zebra boundaries, unchanged input pixels, edge detection, bounded dimensions, display-axis transforms and unavailable gravity. Android instrumentation exercises fresh analysis of the real emulated preview, captures its UI, records a real video while changing aids, checks the retained configuration and recreates the activity. A grid-only restored state performs no pixel reads.

Physical accuracy, sensor calibration, scene colour and sustained 4K/8K performance remain device gates. The framework camera/encoder tests and exact media/report identity checks remain required.

API basis: [TextureView bitmap and transform contracts](https://developer.android.com/reference/android/view/TextureView).
