package com.s23log.probe.camera

import android.hardware.camera2.CameraCharacteristics as C
import android.hardware.camera2.CaptureRequest as R
import com.s23log.probe.core.CapturePolicy
import com.s23log.probe.core.RatePlan
import android.util.Range

/** WB presets/lock are supported; calibrated Kelvin-to-sensor-gain conversion is not claimed. */
data class CameraControls(
    val manualExposure: Boolean = false,
    val iso: Int = 100,
    val exposureNs: Long = 16_666_667L,
    val focusDiopters: Float? = null,
    val wbMode: Int = R.CONTROL_AWB_MODE_AUTO,
    val wbLock: Boolean = false,
    internal val afModeOverride: Int? = null,
    val exposureCompensationSteps: Int = 0
) {
    fun describe(): Map<String, Any?> = mapOf("manualExposure" to manualExposure, "iso" to iso,
        "exposureNs" to exposureNs, "focusDiopters" to focusDiopters, "awbMode" to wbMode, "awbLock" to wbLock, "afModeOverride" to afModeOverride,
        "exposureCompensationSteps" to exposureCompensationSteps)

    fun effective(target: CameraTarget, fps: Int?): CameraControls {
        val c = target.characteristics
        val sensitivity = c[C.SENSOR_INFO_SENSITIVITY_RANGE]
        val exposure = c[C.SENSOR_INFO_EXPOSURE_TIME_RANGE]
        return copy(iso = if (manualExposure && sensitivity != null) iso.coerceIn(sensitivity.lower, sensitivity.upper) else iso,
            exposureNs = if (manualExposure && exposure != null) {
                if (fps != null) CapturePolicy.exposureForRate(exposureNs, exposure.lower, exposure.upper, fps)
                else exposureNs.coerceIn(exposure.lower, exposure.upper)
            } else exposureNs, focusDiopters = focusDiopters?.coerceIn(0f, target.minFocus),
            exposureCompensationSteps = if (manualExposure) 0 else target.exposureCompensation?.bounded(exposureCompensationSteps) ?: 0)
    }

    fun apply(builder: R.Builder, target: CameraTarget, fps: Int?, ratePlan: RatePlan? = null) {
        val c = target.characteristics
        fun <T> set(key: R.Key<T>, value: T) = target.set(builder, key, value)
        require(iso > 0 && exposureNs > 0) { "ISO and shutter must be positive" }
        require(wbMode in target.wbModes || (target.wbModes.isEmpty() && wbMode == R.CONTROL_AWB_MODE_AUTO)) { "White-balance preset unavailable on this route" }
        if (manualExposure) require(wbMode != R.CONTROL_AWB_MODE_AUTO || wbLock) { "Lock automatic white balance before disabling AE" }
        if (manualExposure && target.minFocus > 0) require(focusDiopters != null) { "Freeze or set manual focus before disabling AE" }
        if (wbLock && wbMode == R.CONTROL_AWB_MODE_AUTO) require(target.wbLockAvailable) { "White-balance lock unavailable on this route" }
        set(R.CONTROL_MODE, R.CONTROL_MODE_AUTO)
        if (manualExposure) {
            require(target.manualSensor) { "Manual exposure is not advertised for this camera" }
            val isoRange = requireNotNull(c[C.SENSOR_INFO_SENSITIVITY_RANGE])
            val exposureRange = requireNotNull(c[C.SENSOR_INFO_EXPOSURE_TIME_RANGE])
            val exposure = if (fps != null) CapturePolicy.exposureForRate(exposureNs, exposureRange.lower, exposureRange.upper, fps)
                else exposureNs.coerceIn(exposureRange.lower, exposureRange.upper)
            set(R.CONTROL_AE_MODE, R.CONTROL_AE_MODE_OFF)
            set(R.SENSOR_SENSITIVITY, iso.coerceIn(isoRange.lower, isoRange.upper))
            set(R.SENSOR_EXPOSURE_TIME, exposure)
            set(R.SENSOR_FRAME_DURATION, if (fps != null) 1_000_000_000L / fps else exposure)
        } else {
            set(R.CONTROL_AE_MODE, R.CONTROL_AE_MODE_ON)
            val compensation = target.exposureCompensation
            require(compensation != null || exposureCompensationSteps == 0) { "Exposure compensation is unavailable on this camera route" }
            compensation?.let { set(R.CONTROL_AE_EXPOSURE_COMPENSATION, it.bounded(exposureCompensationSteps)) }
            if (fps != null) {
                val planned = ratePlan?.aeRange?.let { Range(it.lower, it.upper) }
                val chosen = planned ?: c[C.CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES]?.filter { it.upper == fps }?.maxByOrNull { it.lower }
                require(chosen != null) { "This rate needs manual exposure; a containing AE range is not fixed-rate proof" }
                set(R.CONTROL_AE_TARGET_FPS_RANGE, chosen)
            }
        }
        val afModes = c[C.CONTROL_AF_AVAILABLE_MODES]?.toSet().orEmpty()
        if (focusDiopters != null) {
            require(target.manualFocus && R.CONTROL_AF_MODE_OFF in afModes) { "Manual focus is unavailable" }
            require(focusDiopters.isFinite())
            set(R.CONTROL_AF_MODE, R.CONTROL_AF_MODE_OFF)
            set(R.LENS_FOCUS_DISTANCE, focusDiopters.coerceIn(0f, target.minFocus))
        } else if (afModeOverride != null) {
            require(afModeOverride in afModes) { "Requested focus mode unavailable" }
            set(R.CONTROL_AF_MODE, afModeOverride)
        } else {
            listOf(R.CONTROL_AF_MODE_CONTINUOUS_VIDEO, R.CONTROL_AF_MODE_CONTINUOUS_PICTURE, R.CONTROL_AF_MODE_AUTO, R.CONTROL_AF_MODE_OFF)
                .firstOrNull { it in afModes }?.let { set(R.CONTROL_AF_MODE, it) }
        }
        val modes = c[C.CONTROL_AWB_AVAILABLE_MODES]?.toList().orEmpty()
        if (wbMode in modes) set(R.CONTROL_AWB_MODE, wbMode)
        else require(wbMode == R.CONTROL_AWB_MODE_AUTO) { "Selected white-balance preset is unavailable" }
        if (target.wbLockAvailable) set(R.CONTROL_AWB_LOCK, wbLock)
    }
}
