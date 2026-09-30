package com.s23log.probe.core

/** Sensor timing and codec selection are independent from colour encoding. */
enum class RateControl(val label: String) {
    AE_FIXED("fixed AE"), AE_VARIABLE("variable AE"), MANUAL_SENSOR("manual timing")
}
data class FpsRange(val lower: Int, val upper: Int) {
    init { require(lower > 0 && upper >= lower) }
}
data class RatePlan(val control: RateControl, val aeRange: FpsRange? = null) {
    val requiresManual: Boolean get() = control == RateControl.MANUAL_SENSOR
    init { require((aeRange == null) == requiresManual) }
}
data class VideoSize(val width: Int, val height: Int) {
    init { require(width > 0 && height > 0) }
    val pixels: Long get() = width.toLong() * height
}
data class ModeRejection(val size: VideoSize, val fps: Int, val range: DynamicRange, val mime: String, val reason: String, val processing: ProcessingPath = ProcessingPath.DIRECT) {
    fun describe(): Map<String, Any> = mapOf("width" to size.width, "height" to size.height, "fps" to fps,
        "dynamicRange" to range.name, "mime" to mime, "reason" to reason, "evidence" to "advertised_rejection", "processingPath" to processing.name)
}

object ModePlanning {
    /** First-run defaults are allowed; a missing saved format must be explicitly reselected. */
    fun restore(modes: List<RecordingMode>, savedKey: String?): RecordingMode? =
        if (savedKey == null) modes.firstOrNull { !it.ratePlan.requiresManual } ?: modes.firstOrNull()
        else modes.firstOrNull { it.key == savedKey } ?: modes.filter { it.legacyKey == savedKey }.singleOrNull()
    val eightK = VideoSize(7680, 4320)
    // Ordinary sessions only. High-speed request lists/session types are a separate feature.
    fun rates(ranges: List<FpsRange>): List<Int> =
        (listOf(30, 24, 25, 60, 50) + ranges.map { it.upper }).filter { it in 1..60 }.distinct()
    fun sizes(advertised: List<VideoSize>): List<VideoSize> =
        (listOf(VideoSize(1920, 1080), VideoSize(1280, 720), VideoSize(3840, 2160), eightK) + advertised).distinct()
    fun mimes(range: DynamicRange): List<String> = when (range) {
        DynamicRange.SDR -> listOf("video/avc", "video/hevc")
        DynamicRange.HLG10 -> listOf("video/hevc")
    }

    /** A containing AE range does not establish a fixed target. Never relabel 30 fps as 24. */
    fun timing(fps: Int, ranges: List<FpsRange>, manualSensor: Boolean,
               maxFrameDurationNs: Long?, minimumExposureNs: Long?): RatePlan? {
        require(fps > 0)
        ranges.firstOrNull { it.lower == fps && it.upper == fps }?.let { return RatePlan(RateControl.AE_FIXED, it) }
        ranges.filter { it.upper == fps }.maxByOrNull { it.lower }?.let { return RatePlan(RateControl.AE_VARIABLE, it) }
        val interval = 1_000_000_000L / fps
        return if (manualSensor && maxFrameDurationNs != null && maxFrameDurationNs >= interval &&
            minimumExposureNs != null && minimumExposureNs in 1..interval) RatePlan(RateControl.MANUAL_SENSOR) else null
    }

    fun recordingAllowed(state: EngineState, mode: RecordingMode?, manualApplied: Boolean, manualRequested: Boolean = false): Boolean =
        state == EngineState.PREVIEW && mode != null && (!mode.ratePlan.requiresManual || manualApplied) && (!manualRequested || manualApplied)
}

/** One acknowledgement, only after a sample was written; Stop is terminal for this recording. */
class RecordingStartGate {
    private var acknowledged = false
    private var stopped = false
    @Synchronized fun sampleWritten(bytes: Int, codecConfig: Boolean, ptsUs: Long): Boolean {
        if (stopped || acknowledged || bytes <= 0 || codecConfig || ptsUs < 0) return false
        acknowledged = true
        return true
    }
    @Synchronized fun stop() { stopped = true }
}

/** Cadence warnings do not invalidate or delete otherwise readable footage. */
fun FrameSummary.cadenceStatus(requestedFps: Int): String {
    require(requestedFps > 0)
    if (invalidTimestamps > 0) return "invalid_timestamps"
    if (durationUs < 2_000_000L || measuredFps == null) return "insufficient_duration"
    return if (kotlin.math.abs(measuredFps / requestedFps - 1.0) <= 0.03 && largeGaps == 0) "within_tolerance" else "warning"
}
