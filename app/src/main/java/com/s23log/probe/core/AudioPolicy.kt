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

/** Startup observations may be qualified; once anchored, timestamps are never silently rewritten. */
class PcmClock(private val sampleRate: Int, private val stableStartup: Boolean = false) {
    init { require(sampleRate > 0) }
    @Volatile var anchorFrame: Long? = null; private set
    @Volatile var anchorNs: Long? = null; private set
    @Volatile var source = "unavailable"; private set
    @Volatile var observations = 0; private set
    @Volatile var maxDriftUs = 0L; private set
    @Volatile var regressions = 0; private set
    private var repeatedFrameTimes = 0
    private var jumps = 0
    private var lastObservedFrame = -1L
    private var lastObservedNs = -1L
    private var firstObservedFrame = -1L
    private var firstObservedNs = -1L
    // Bound storage, not observation count: fast HALs can report more than
    // eight progressive timestamps within the required 100 ms qualification.
    private var startupFirstNs = 0L
    private var startupMinOriginNs = 0L
    private var startupMaxOriginNs = 0L
    private var startupProgress = 0
    val anchored: Boolean get() = anchorNs != null
    private fun durationNs(frames: Long): Long = frames / sampleRate * 1_000_000_000L + frames % sampleRate * 1_000_000_000L / sampleRate

    @Synchronized fun observe(frame: Long, ns: Long) {
        require(frame >= 0 && ns > 0) { "Invalid microphone timestamp" }
        if (frame == lastObservedFrame && ns == lastObservedNs) return
        if (frame < lastObservedFrame || ns < lastObservedNs) { regressions++; return }
        // A changed time for the same frame is not a progressive clock observation.
        if (frame == lastObservedFrame || ns == lastObservedNs) { repeatedFrameTimes++; return }
        if (firstObservedFrame < 0) { firstObservedFrame = frame; firstObservedNs = ns }
        if (lastObservedFrame >= 0 && abs((ns - lastObservedNs) - durationNs(frame - lastObservedFrame)) > 20_000_000) jumps++
        observations++
        if (!anchored) {
            if (!stableStartup) {
                anchorFrame = frame; anchorNs = ns; source = "audio_timestamp_monotonic"
            } else {
                val origin = ns - durationNs(frame)
                if (startupProgress == 0 ||
                    maxOf(startupMaxOriginNs, origin) - minOf(startupMinOriginNs, origin) > 2_000_000) {
                    // A noisy origin starts a new qualification interval. Earlier
                    // unstable observations cannot satisfy the 100 ms minimum.
                    startupFirstNs = ns
                    startupMinOriginNs = origin; startupMaxOriginNs = origin
                    startupProgress = 1
                } else {
                    startupMinOriginNs = minOf(startupMinOriginNs, origin)
                    startupMaxOriginNs = maxOf(startupMaxOriginNs, origin)
                    startupProgress = minOf(3, startupProgress + 1)
                }
                if (startupProgress >= 3 && ns - startupFirstNs >= 100_000_000) {
                    anchorFrame = 0
                    anchorNs = startupMinOriginNs + (startupMaxOriginNs - startupMinOriginNs) / 2
                    source = "audio_timestamp_monotonic"
                }
            }
        }
        if (anchored) maxDriftUs = max(maxDriftUs, abs(ns - timestampNs(frame)) / 1000)
        lastObservedFrame = frame; lastObservedNs = ns
    }
    @Synchronized fun estimate(frame: Long, ns: Long) {
        require(frame >= 0 && ns > 0)
        if (!anchored) { anchorFrame = frame; anchorNs = ns; source = "read_completion_estimate_unverified" }
    }
    @Synchronized fun timestampNs(frame: Long): Long {
        require(frame >= 0)
        return requireNotNull(anchorNs) + durationNs(frame - requireNotNull(anchorFrame))
    }
    fun timestampUs(frame: Long): Long = timestampNs(frame) / 1000
    @Synchronized fun frameAt(ns: Long): Long {
        val delta = ns - requireNotNull(anchorNs)
        return (requireNotNull(anchorFrame) + delta / 1_000_000_000L * sampleRate + delta % 1_000_000_000L * sampleRate / 1_000_000_000L).coerceAtLeast(0)
    }
    @Synchronized fun quality(): String = when {
        regressions > 0 -> "timestamp_regression"
        jumps > 0 -> "timestamp_discontinuity_suspected"
        source != "audio_timestamp_monotonic" -> "clock_unverified"
        observations < 3 || lastObservedNs - firstObservedNs < 100_000_000 -> "clock_warming_up"
        maxDriftUs > 33_333 -> "clock_rate_deviation"
        else -> "stable_nominal_clock"
    }
    @Synchronized fun describe(): Map<String, Any?> = mapOf(
        "source" to source, "anchorFrame" to anchorFrame, "anchorNs" to anchorNs,
        "timestampObservations" to observations, "maxNominalClockDriftUs" to maxDriftUs,
        "timestampRegressions" to regressions, "nonProgressiveObservations" to repeatedFrameTimes,
        "abruptTimestampChanges" to jumps, "quality" to quality(), "stableStartupRequired" to stableStartup,
        "observedRateErrorPpm" to if (lastObservedNs - firstObservedNs >= 1_000_000_000 && lastObservedFrame > firstObservedFrame)
            ((lastObservedNs - firstObservedNs).toDouble() / durationNs(lastObservedFrame - firstObservedFrame) - 1.0) * 1_000_000 else null,
        "resamplingApplied" to false, "physicalLipSyncVerified" to false
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
