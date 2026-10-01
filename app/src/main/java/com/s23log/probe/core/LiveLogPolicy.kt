package com.s23log.probe.core

import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs

/** Live timestamps are relative sensor timestamps, never frame-number/CFR replacements. */
class LiveLogClock(val fps: Int, private val maximumFrames: Int = 18_000) {
    init { require(fps in listOf(24, 30) && maximumFrames >= 2) }
    private var epoch: Long? = null
    private var previousNs = 0L
    private val timestamps = ArrayList<Long>()
    var largeGaps = 0; private set
    var maximumGapNs = 0L; private set
    fun submit(sensorNs: Long): Long {
        require(sensorNs > 0 && (timestamps.isEmpty() || sensorNs > previousNs)) { "Live sensor timestamps repeated or regressed" }
        require(timestamps.size < maximumFrames) { "Live recording reached its bounded timestamp-index limit" }
        val first = epoch ?: sensorNs.also { epoch = it }
        val pts = (sensorNs - first) / 1000
        require(timestamps.isEmpty() || pts > timestamps.last()) { "Distinct sensor frames collapse to the same microsecond timestamp" }
        if (timestamps.isNotEmpty()) {
            val gap = sensorNs - previousNs
            maximumGapNs = maxOf(maximumGapNs, gap)
            if (gap > 1_500_000_000L / fps) largeGaps++
        }
        previousNs = sensorNs; timestamps += pts
        return pts
    }
    fun presentationTimes(): List<Long> = timestamps.toList()
    val count: Int get() = timestamps.size
    val durationNs: Long get() = epoch?.let { previousNs - it } ?: 0
    val measuredFps: Double? get() = if (count >= 2 && durationNs > 0) (count - 1) * 1e9 / durationNs else null
    val withinTolerance: Boolean get() = durationNs >= 2_000_000_000L && largeGaps == 0 && measuredFps?.let { abs(it / fps - 1) <= .03 } == true
}

/** Explicit source crop and output size. No upscaling or hidden substitution. */
data class LiveLogOutput(val left: Int, val top: Int, val cropWidth: Int, val cropHeight: Int, val divisor: Int) {
    init {
        require(listOf(left, top, cropWidth, cropHeight).all { it >= 0 && it % 2 == 0 })
        require(divisor in listOf(1, 2, 4) && cropWidth >= 4 && cropHeight >= 4)
        require(cropWidth % (2 * divisor) == 0 && cropHeight % (2 * divisor) == 0)
        require(width <= 1920 && height <= 1080) { "First live milestone is limited to 1920×1080 output" }
    }
    val width: Int get() = cropWidth / divisor
    val height: Int get() = cropHeight / divisor
    fun crop() = intArrayOf(left, top, cropWidth, cropHeight)
    val label: String get() = "$width × $height · source crop $cropWidth × $cropHeight at $left,$top · reduction 1/$divisor"
    companion object {
        fun choices(crop: IntArray): List<LiveLogOutput> {
            require(crop.size == 4 && crop.all { it >= 0 && it % 2 == 0 })
            val result = mutableListOf<LiveLogOutput>()
            for (divisor in listOf(2, 1)) {
                val w = 1920 * divisor; val h = 1080 * divisor
                if (crop[2] >= w && crop[3] >= h) result += LiveLogOutput(
                    crop[0] + ((crop[2] - w) / 2 and -2), crop[1] + ((crop[3] - h) / 2 and -2), w, h, divisor)
            }
            for (d in listOf(1, 2, 4)) if (crop[2] >= 4 && crop[3] >= 4 && crop[2] % (2*d) == 0 && crop[3] % (2*d) == 0 && crop[2]/d <= 1920 && crop[3]/d <= 1080)
                result += LiveLogOutput(crop[0], crop[1], crop[2], crop[3], d)
            return result.distinct()
        }
        fun memoryBytes(rawWidth: Int, rawHeight: Int, output: LiveLogOutput): Long {
            require(rawWidth > 0 && rawHeight > 0 && rawWidth.toLong()*rawHeight <= 16_000_000L) { "First GPU RAW backend allows at most 16 MP sensor input; higher modes remain research work" }
            require(output.left.toLong() + output.cropWidth <= rawWidth && output.top.toLong() + output.cropHeight <= rawHeight)
            // 3 ImageReader buffers + 3 copied RAW buffers + GPU RAW texture; include the optional uint32 readback repack.
            return rawWidth.toLong()*rawHeight*14 + output.width.toLong()*output.height*28 + 16L*1024*1024
        }
    }
}

/** Small, pure policy shared by actual route probes and tests. An unavailable route is not a pass. */
object LivePrecision {
    data class Result(val mean: Double, val peak: Double, val levels: Int) {
        val passed: Boolean get() = mean <= .75 && peak <= 2.0 && levels >= 600
    }
    fun assess(values: DoubleArray, expected: DoubleArray): Result {
        require(values.size == expected.size && values.size >= 600 && values.all { it.isFinite() } && expected.all { it.isFinite() })
        val errors = values.indices.map { abs(values[it] - expected[it]) }
        return Result(errors.average(), errors.max(), values.map { kotlin.math.round(it).toInt() }.toSet().size)
    }
}

/** GPU output is tightly packed P010: Y plane then interleaved Cb/Cr, no implicit colour conversion. */
object LiveP010 {
    fun rows(bytes: ByteBuffer, width: Int, height: Int): P010Rows {
        require(width > 0 && height > 0 && width % 2 == 0 && height % 2 == 0)
        require(width.toLong()*height*3 <= bytes.remaining())
        val base = bytes.position(); val uv = base + width*height*2
        fun view(offset: Int) = bytes.duplicate().order(ByteOrder.LITTLE_ENDIAN).apply { position(offset) }
        return P010Rows(TenBitPlane(view(base), width, height, width*2, 2),
            TenBitPlane(view(uv), width/2, height/2, width*2, 4), TenBitPlane(view(uv+2), width/2, height/2, width*2, 4))
    }
    fun copy(source: P010Rows, target: P010Rows) {
        require(source.y.width == target.y.width && source.y.height == target.y.height)
        for (y in 0 until source.y.height) for (x in 0 until source.y.width) target.y.put(x,y,source.y.get(x,y))
        for (y in 0 until source.u.height) for (x in 0 until source.u.width) {
            target.u.put(x,y,source.u.get(x,y)); target.v.put(x,y,source.v.get(x,y))
        }
    }
}
