package com.s23log.probe.core

import kotlin.math.abs

/** Application acceptance tolerances for reported sensor settings, not physical calibration. */
object ManualResultPolicy {
    const val EXPOSURE_TOLERANCE = 0.05
    const val ISO_TOLERANCE = 0.05
    const val FRAME_TOLERANCE = 0.03
    data class Result(val matched: Boolean, val status: String, val targetIso: Int, val targetExposureNs: Long,
        val targetFrameDurationNs: Long?, val isoMatched: Boolean, val exposureMatched: Boolean, val frameMatched: Boolean?) {
        fun describe(): Map<String, Any?> = mapOf("matched" to matched, "status" to status, "targetIso" to targetIso,
            "targetExposureNs" to targetExposureNs, "targetFrameDurationNs" to targetFrameDurationNs,
            "isoMatched" to isoMatched, "exposureMatched" to exposureMatched, "frameDurationMatched" to frameMatched,
            "isoToleranceFraction" to ISO_TOLERANCE, "exposureToleranceFraction" to EXPOSURE_TOLERANCE,
            "frameDurationToleranceFraction" to FRAME_TOLERANCE, "physicalCalibrationVerified" to false)
    }
    fun assess(targetIso: Int, targetExposureNs: Long, targetFrameDurationNs: Long?,
               actualIso: Int?, actualExposureNs: Long?, actualFrameDurationNs: Long?, aeOff: Boolean): Result {
        require(targetIso > 0 && targetExposureNs > 0 && (targetFrameDurationNs == null || targetFrameDurationNs > 0))
        fun near(actual: Long?, target: Long, tolerance: Double) = actual != null && actual > 0 &&
            abs(actual.toDouble() - target.toDouble()) <= maxOf(1.0, target * tolerance)
        val iso = near(actualIso?.toLong(), targetIso.toLong(), ISO_TOLERANCE)
        val exposure = near(actualExposureNs, targetExposureNs, EXPOSURE_TOLERANCE)
        val frame = targetFrameDurationNs?.let { near(actualFrameDurationNs, it, FRAME_TOLERANCE) }
        val missing = actualIso == null || actualExposureNs == null || (targetFrameDurationNs != null && actualFrameDurationNs == null)
        val status = when {
            !aeOff -> "auto_exposure_active"
            missing -> "missing_sensor_metadata"
            !iso || !exposure || frame == false -> "outside_tolerance"
            else -> "within_tolerance"
        }
        return Result(status == "within_tolerance", status, targetIso, targetExposureNs, targetFrameDurationNs, iso, exposure, frame)
    }
}
