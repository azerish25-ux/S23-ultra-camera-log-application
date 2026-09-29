package com.s23log.probe.core

import kotlin.math.abs
import kotlin.math.log10
import kotlin.math.max
import kotlin.math.sqrt

/** Audio is a deliberate recording choice; failures never change it to OFF. */
enum class AudioMode(val channels: Int) {
    OFF(0), MONO(1), STEREO(2);
    val enabled: Boolean get() = this != OFF
    val bitRate: Int get() = if (this == STEREO) 192_000 else 128_000
    companion object {
        const val SAMPLE_RATE = 48_000
        fun fromStored(value: String?): AudioMode = entries.firstOrNull { it.name == value } ?: MONO
    }
}

/** One immutable anchor for the AudioRecord sample-position clock. Never reset tracks separately. */
class PcmClock(private val sampleRate: Int) {
    init { require(sampleRate > 0) }
    var anchorFrame: Long? = null; private set
    var anchorNs: Long? = null; private set
    var source = "unavailable"; private set
    var observations = 0; private set
    var maxDriftUs = 0L; private set
    var regressions = 0; private set
    private var lastObservedFrame = -1L
    private var lastObservedNs = -1L
    val anchored: Boolean get() = anchorNs != null

    fun observe(frame: Long, ns: Long) {
        require(frame >= 0 && ns > 0) { "Invalid microphone timestamp" }
        if (frame == lastObservedFrame && ns == lastObservedNs) return
        if (frame < lastObservedFrame || ns < lastObservedNs) { regressions++; return }
        if (!anchored) { anchorFrame = frame; anchorNs = ns; source = "audio_timestamp_monotonic" }
        observations++
        maxDriftUs = max(maxDriftUs, abs(ns - timestampNs(frame)) / 1000)
        lastObservedFrame = frame; lastObservedNs = ns
    }

    /** Fallback is explicit, immutable and NOT proof of synchronization. */
    fun estimate(frame: Long, ns: Long) {
        require(frame >= 0 && ns > 0)
        if (!anchored) { anchorFrame = frame; anchorNs = ns; source = "read_completion_estimate_unverified" }
    }
    fun timestampNs(frame: Long): Long {
        require(frame >= 0)
        val delta = frame - requireNotNull(anchorFrame)
        // Avoid multiplying a long recording's entire sample count by a billion.
        return requireNotNull(anchorNs) + delta / sampleRate * 1_000_000_000L + delta % sampleRate * 1_000_000_000L / sampleRate
    }
    fun timestampUs(frame: Long): Long = timestampNs(frame) / 1000
    fun describe(): Map<String, Any?> = mapOf(
        "source" to source, "anchorFrame" to anchorFrame, "anchorNs" to anchorNs,
        "timestampObservations" to observations, "maxNominalClockDriftUs" to maxDriftUs,
        "timestampRegressions" to regressions, "resamplingApplied" to false,
        "physicalLipSyncVerified" to false
    )
}

data class ChannelLevel(val rmsDb: Double, val peakDb: Double, val clipped: Boolean) {
    val meter: Int get() = ((peakDb.coerceIn(-60.0, 0.0) + 60) * 100 / 60).toInt()
}
object PcmLevels {
    fun measure(samples: ShortArray, count: Int, channels: Int): List<ChannelLevel> {
        require(channels in 1..2 && count in 1..samples.size && count % channels == 0)
        return (0 until channels).map { channel ->
            var squares = 0.0; var peak = 0.0
            for (i in channel until count step channels) {
                val value = abs(samples[i].toDouble()) / 32768.0
                squares += value * value; peak = max(peak, value)
            }
            fun db(value: Double) = if (value <= 0) -96.0 else (20 * log10(value)).coerceAtLeast(-96.0)
            ChannelLevel(db(sqrt(squares / (count / channels))), db(peak), peak >= 32760.0 / 32768)
        }
    }
}

/** AAC-LC AudioSpecificConfig, restricted to ordinary mono/stereo for this milestone. */
object AacLcConfig {
    fun matches(bytes: ByteArray, sampleRate: Int, channels: Int): Boolean {
        if (bytes.size < 2) return false
        var offset = 0
        fun bits(n: Int): Int {
            require(offset + n <= bytes.size * 8)
            var v = 0
            repeat(n) { v = (v shl 1) or ((bytes[offset / 8].toInt() ushr (7 - offset % 8)) and 1); offset++ }
            return v
        }
        return runCatching {
            val objectType = bits(5)
            val frequencyIndex = bits(4)
            val frequencies = intArrayOf(96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000, 7350)
            val frequency = if (frequencyIndex == 15) bits(24) else frequencies.getOrNull(frequencyIndex)
            val config = bits(4)
            objectType == 2 && frequency == sampleRate && config == channels && bits(1) == 0 // 1024-frame LC, not 960
        }.getOrDefault(false)
    }
}
