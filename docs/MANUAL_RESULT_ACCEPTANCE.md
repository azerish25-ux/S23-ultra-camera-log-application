# Manual sensor-result acceptance

Manual exposure is confirmed only when current capture-result metadata matches the effective, camera-clamped request. Turning AE off and receiving any positive ISO/shutter values is no longer sufficient.

The application requires reported ISO and exposure time within 5% of their effective targets (at least one integer unit), and the requested sensor frame duration within 3%. A missing required field, nonpositive value, active AE or out-of-tolerance result cannot pass. These are application acceptance tolerances, not a calibration claim or a guarantee that every sensor supports the same precision. Focus/WB convergence, lock evidence and deadlines remain unchanged.

The controller rejects recording startup while requested manual settings are unconfirmed, including on modes whose original plan also allowed auto exposure. The UI separately displays actual applied values, effective manual targets and clamping. Updates during recording preserve footage and expose mismatches instead of falsely marking the new settings confirmed. Validation evidence retains the current comparison, its tolerances, requested values and actual sensor metadata.

Session/request generation changes clear confirmation, and stale callbacks cannot restore it. Both the UI gate and the controller enforce readiness. Actual output cadence is still checked independently after capture; matching frame-duration metadata alone is not a sustained-capture proof.

`ManualResultPolicyTest` covers exact settings, positive-but-wrong results, AE-on, missing metadata, tolerance boundaries, a 25-vs-24-fps mismatch and optional/unmeasured frame timing. Real-phone manual calibration and complete time-varying control history remain separate acceptance work.
