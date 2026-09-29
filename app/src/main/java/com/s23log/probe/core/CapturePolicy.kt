package com.s23log.probe.core

/** Pure policies shared by the camera engine, diagnostics and regression tests. */
enum class DynamicRange { SDR, HLG10 }
enum class EngineState { CLOSED, OPENING, PREVIEW, ADJUSTING, STARTING, RECORDING, STOPPING, RAW, ERROR }

data class RecordingMode(
    val width: Int,
    val height: Int,
    val fps: Int,
    val range: DynamicRange,
    val encoder: String,
    val mime: String,
    val bitRate: Int,
    val previewDuringRecording: Boolean,
    val timingAdvertised: Boolean,
    val ratePlan: RatePlan = RatePlan(RateControl.AE_FIXED, FpsRange(fps, fps))
) {
    val label: String get() = "${width}×${height} / $fps / ${if (mime == "video/hevc") "HEVC" else "AVC"} / ${range.name} / ${ratePlan.control.label} · $encoder"
    val key: String get() = "$width:$height:$fps:${range.name}:$encoder:$mime:${ratePlan.control.name}"
    val legacyKey: String get() = "$width:$height:$fps:${range.name}:$encoder"
    fun describe(): Map<String, Any?> = mapOf("key" to key, "width" to width, "height" to height, "fps" to fps,
        "dynamicRange" to range.name, "mime" to mime, "encoder" to encoder, "bitrate" to bitRate,
        "rateControl" to ratePlan.control.name, "aeRange" to ratePlan.aeRange?.let { listOf(it.lower, it.upper) },
        "requiresManualExposure" to ratePlan.requiresManual, "timingAdvertised" to timingAdvertised,
        "previewDuringRecording" to previewDuringRecording, "evidence" to "advertised_candidate", "customLog" to false)
}

object CapturePolicy {
    // Android's public profile identifiers. Explicit bit depth, never `profile != STANDARD`.
    private val tenBitProfiles = setOf(2L, 4L, 8L, 16L, 32L, 64L, 128L)
    fun isTenBitProfile(profile: Long): Boolean = profile in tenBitProfiles
    fun supportsHlg(tenBitCapability: Boolean, profiles: Set<Long>): Boolean =
        tenBitCapability && 2L in profiles

    fun nominalRateFits(minFrameDurationNs: Long, fps: Int): Boolean =
        fps > 0 && minFrameDurationNs >= 0 &&
            (minFrameDurationNs == 0L || minFrameDurationNs <= 1_000_000_000L / fps + 1L)

    fun allowsPair(firstConstraints: Set<Long>, secondConstraints: Set<Long>, first: Long, second: Long): Boolean =
        (firstConstraints.isEmpty() || second in firstConstraints) &&
            (secondConstraints.isEmpty() || first in secondConstraints)

    fun orientation(sensor: Int, display: Int, front: Boolean): Int {
        require(sensor % 90 == 0 && display % 90 == 0)
        return ((sensor + if (front) display else -display) % 360 + 360) % 360
    }

    fun exposureForRate(requestedNs: Long, minNs: Long, maxNs: Long, fps: Int): Long {
        require(minNs > 0 && maxNs >= minNs && fps > 0)
        val limit = minOf(maxNs, 1_000_000_000L / fps)
        require(limit >= minNs) { "Sensor minimum exposure exceeds the selected frame interval" }
        return requestedNs.coerceIn(minNs, limit)
    }

    fun canStartRecording(state: EngineState): Boolean = state == EngineState.PREVIEW
    fun canChangeCamera(state: EngineState): Boolean =
        state in setOf(EngineState.CLOSED, EngineState.PREVIEW, EngineState.ERROR)
}

/** Invalidates callbacks belonging to a closed device or superseded capture session. */
class SessionEpoch {
    private var value = 0L
    fun next(): Long = ++value
    fun current(): Long = value
    fun isCurrent(token: Long): Boolean = token == value
}

/** Sensor images and capture results arrive in either order; timestamps, not order, pair them. */
class TimestampMatcher<A, B>(
    private val capacity: Int,
    private val dispose: (A) -> Unit
) {
    private val images = linkedMapOf<Long, A>()
    private val results = linkedMapOf<Long, B>()
    init { require(capacity > 0) }
    fun image(timestamp: Long, image: A): Pair<A, B>? {
        results.remove(timestamp)?.let { return image to it }
        images.put(timestamp, image)?.let(dispose)
        while (images.size > capacity) dispose(images.remove(images.keys.first())!!)
        return null
    }
    fun result(timestamp: Long, result: B): Pair<A, B>? {
        images.remove(timestamp)?.let { return it to result }
        results[timestamp] = result
        while (results.size > capacity) results.remove(results.keys.first())
        return null
    }
    fun clear() {
        images.values.forEach(dispose)
        images.clear()
        results.clear()
    }
}

data class FrameSummary(val frames: Int, val durationUs: Long, val measuredFps: Double?, val largeGaps: Int, val invalidTimestamps: Int)
class FrameStatistics(private val nominalFps: Int) {
    private var frames = 0
    private var first = 0L
    private var last = 0L
    private var gaps = 0
    private var invalid = 0
    init { require(nominalFps > 0) }
    fun add(ptsUs: Long) {
        if (frames == 0) { first = ptsUs; last = ptsUs; frames = 1; return }
        if (ptsUs <= last) invalid++
        else if (ptsUs - last > (1_000_000L / nominalFps) * 3 / 2) gaps++
        last = ptsUs
        frames++
    }
    fun summary(): FrameSummary {
        val duration = if (frames > 1) last - first else 0L
        return FrameSummary(frames, duration, if (duration > 0 && invalid == 0) (frames - 1) * 1_000_000.0 / duration else null, gaps, invalid)
    }
}

/** Preserve the scan even when persistence fails; the UI must always leave its busy state. */
data class WorkResult<T>(val value: T?, val scanError: String?, val saveError: String?)
fun <T> scanAndSave(scan: () -> T, save: (T) -> Unit): WorkResult<T> {
    val value = try { scan() } catch (error: Exception) {
        return WorkResult(null, "${error.javaClass.simpleName}: ${error.message}", null)
    }
    return try { save(value); WorkResult(value, null, null) } catch (error: Exception) {
        WorkResult(value, null, "${error.javaClass.simpleName}: ${error.message}")
    }
}
