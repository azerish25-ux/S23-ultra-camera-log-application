package com.s23log.probe.core

import kotlin.math.*

/** Input capture profile, working space, file encoding and monitor are separate contracts. */
enum class ProcessingPath { DIRECT, GPU_HLG10 }
enum class MonitorTransform { SDR_TONEMAP, HLG_SIGNAL }
data class ColourPipelineSpec(
    val inputProfile: DynamicRange,
    val workingSpace: String,
    val recordingTransfer: String,
    val recordingPrimaries: String,
    val recordingBitDepth: Int,
    val processing: ProcessingPath
) {
    fun describe(): Map<String, Any> = mapOf(
        "schemaVersion" to 1, "inputProfile" to inputProfile.name, "workingSpace" to workingSpace,
        "recordingTransfer" to recordingTransfer, "recordingPrimaries" to recordingPrimaries,
        "recordingBitDepth" to recordingBitDepth, "processingPath" to processing.name,
        "customLog" to false, "sensorRaw" to false, "precisionCertifiedOnCamera" to false)
    companion object {
        fun forMode(mode: RecordingMode) = ColourPipelineSpec(mode.range,
            if (mode.processing == ProcessingPath.GPU_HLG10) "linearized_HLG_BT2020_RGBA16F" else "camera_direct",
            if (mode.range == DynamicRange.HLG10) "HLG" else "SDR_VIDEO",
            if (mode.range == DynamicRange.HLG10) "BT2020" else "BT709",
            if (mode.range == DynamicRange.HLG10) 10 else 8, mode.processing)
    }
}

/** Conservative first milestone. Direct 4K/8K modes are never filtered by this policy. */
object ProcessingPolicy {
    fun rejection(api: Int, mode: RecordingMode, surfaceSizeAndRate: Boolean,
                  hdrEditing: Boolean, hlgEditing: Boolean): String? = when {
        api < 33 -> "GPU HLG requires Android API 33 or newer"
        mode.range != DynamicRange.HLG10 || mode.mime != "video/hevc" -> "GPU input/output must be HLG10 HEVC"
        mode.width > 1920 || mode.height > 1080 || mode.fps !in listOf(24, 30) ->
            "Phase 3E.1 GPU path is limited to at most 1080p at 24/30 fps; direct modes are unchanged"
        !surfaceSizeAndRate -> "Size/rate not exposed for the camera SurfaceTexture input"
        !hdrEditing && !(api >= 35 && hlgEditing) -> "Encoder does not advertise rendered 10-bit RGB input (HDR/HLG editing)"
        else -> null
    }
}

/** BT.2100 HLG signal math. Linearized HLG is NOT unprocessed sensor light. */
object ColourMath {
    const val A = 0.17883277
    const val B = 0.28466892
    const val C = 0.55991073
    // Signed extension retains out-of-gamut intermediates; RGB10 output is limited to [0,1].
    fun hlgDecode(v: Double): Double {
        require(v.isFinite()); val x = abs(v)
        return sign(v) * if (x <= 0.5) x * x / 3.0 else (exp((x - C) / A) + B) / 12.0
    }
    fun hlgEncode(v: Double): Double {
        require(v.isFinite()); val x = abs(v)
        return sign(v) * if (x <= 1.0 / 12.0) sqrt(3.0 * x) else A * ln(12.0 * x - B) + C
    }
    fun limitedYuv10ToHlg(y: Double, cb: Double, cr: Double, fullRange: Boolean = false): DoubleArray {
        require(listOf(y, cb, cr).all { it.isFinite() })
        val l = if (fullRange) y else (y * 1023.0 - 64.0) / 876.0
        val scale = if (fullRange) 1023.0 else 896.0
        val u = (cb * 1023.0 - 512.0) / scale
        val v = (cr * 1023.0 - 512.0) / scale
        return doubleArrayOf(l + 1.4746 * v, l - 0.16455312684365778 * u - 0.5713531268436578 * v, l + 1.8814 * u)
    }
    fun hlgToLimitedYuv10(r: Double, g: Double, b: Double): DoubleArray {
        val y = 0.2627 * r + 0.6780 * g + 0.0593 * b
        return doubleArrayOf((64 + 876 * y) / 1023, (512 + 896 * (b - y) / 1.8814) / 1023,
            (512 + 896 * (r - y) / 1.4746) / 1023)
    }
    /** Reference-only S23Log/0.1. Not exposed as a recording format or tagged as HLG. */
    fun referenceLogEncode(linear: Double): Double {
        require(linear.isFinite() && linear in 0.0..1.0)
        return ln1p(63.0 * linear) / ln(64.0)
    }
    fun referenceLogDecode(encoded: Double): Double {
        require(encoded.isFinite() && encoded in 0.0..1.0)
        return expm1(encoded * ln(64.0)) / 63.0
    }
    fun sdrMonitor(linear2020: DoubleArray): DoubleArray {
        require(linear2020.size == 3 && linear2020.all { it.isFinite() })
        val (r, g, b) = linear2020
        val rgb = doubleArrayOf(1.660491*r - 0.587641*g - 0.072850*b,
            -0.124550*r + 1.132900*g - 0.008349*b, -0.018151*r - 0.100579*g + 1.118730*b)
        return rgb.map { v ->
            val x = max(0.0, v) * 4.0; val t = x / (1 + x)
            if (t <= 0.0031308) 12.92*t else 1.055*t.pow(1/2.4) - 0.055
        }.toDoubleArray()
    }
}

/** Small GPU ramp test, not a claim about the camera or lossy encoder's full precision. */
data class PrecisionResult(val maximumError: Double, val distinctLevels: Int, val monotonic: Boolean,
                           val passed: Boolean) {
    fun describe(): Map<String, Any> = mapOf("maximumError" to maximumError, "distinctLevels" to distinctLevels,
        "monotonic" to monotonic, "passed" to passed, "minimumDistinctLevels" to 768, "tolerance" to 1.25 / 1023.0)
}
object ColourPrecision {
    fun assessRamp(values: DoubleArray): PrecisionResult {
        require(values.size == 1024 && values.all { it.isFinite() })
        val error = values.indices.maxOf { abs(values[it] - it / 1023.0) }
        val distinct = values.map { (it * 1023).roundToInt() }.toSet().size
        val monotonic = (1 until values.size).all { values[it] >= values[it - 1] - 1e-6 }
        return PrecisionResult(error, distinct, monotonic, error <= 1.25/1023.0 && distinct >= 768 && monotonic)
    }
}

/** Explicit camera OutputConfiguration MONOTONIC -> EGL presentation ns, with no re-epoching. */
class ProcessingFrameClock(private val fps: Int) {
    init { require(fps > 0) }
    private var first: Long? = null
    private var last: Long? = null
    private var stopped = false
    var frames = 0L; private set
    var largeIntervals = 0L; private set
    var maximumAgeNs = 0L; private set
    fun accept(timestampNs: Long, monotonicNowNs: Long): Boolean {
        if (stopped) return false
        require(timestampNs > 0 && monotonicNowNs > 0)
        require(timestampNs <= monotonicNowNs + 100_000_000L && monotonicNowNs - timestampNs <= 5_000_000_000L) {
            "GPU input is not on the requested monotonic camera clock, or is over five seconds stale"
        }
        last?.let {
            require(timestampNs > it) { "GPU camera timestamp repeated or regressed" }
            if (timestampNs - it > 1_500_000_000L / fps) largeIntervals++
        }
        if (first == null) first = timestampNs
        maximumAgeNs = max(maximumAgeNs, monotonicNowNs - timestampNs)
        last = timestampNs; frames++; return true
    }
    fun stop() { stopped = true }
    fun describe(): Map<String, Any?> = mapOf("source" to "camera_explicit_monotonic",
        "presentationTimestampsRewritten" to false, "firstNs" to first, "lastNs" to last,
        "frames" to frames, "largeInputIntervals" to largeIntervals, "maximumInputAgeNs" to maximumAgeNs,
        "surfaceTextureMayCoalesceFrames" to true, "physicalSyncVerified" to false)
}
