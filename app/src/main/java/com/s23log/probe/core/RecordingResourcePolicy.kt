package com.s23log.probe.core

/** Conservative estimates, not a guarantee against VBR bursts, other writers or sudden shutdown. */
object RecordingResourcePolicy {
    const val FLOOR_BYTES = 64L * 1024 * 1024
    private const val HEADROOM_SECONDS = 30L
    data class Decision(val requiredFreeBytes: Long, val remainingSecondsEstimate: Long?, val stopReason: String?)

    fun assess(freeBytes: Long?, stagedBytes: Long, bitRate: Int, audioBitRate: Int,
               publicationCopy: Boolean, thermalStatus: Int?): Decision {
        require(stagedBytes >= 0 && bitRate > 0 && audioBitRate >= 0)
        val bytesPerSecond = (bitRate.toLong() + audioBitRate + 7) / 8
        val margin = FLOOR_BYTES + bytesPerSecond * HEADROOM_SECONDS
        val debt = if (publicationCopy) stagedBytes else 0L
        val overflow = debt > Long.MAX_VALUE - margin
        val required = if (overflow) Long.MAX_VALUE else debt + margin
        val reason = when {
            thermalStatus != null && thermalStatus >= 3 -> "thermal_severe"
            freeBytes == null || freeBytes < 0 -> "storage_unavailable"
            overflow -> "storage_reserve_reached"
            freeBytes < required -> "storage_reserve_reached"
            else -> null
        }
        val remaining = freeBytes?.takeIf { it >= 0 }?.let {
            (it - minOf(it, required)) / (bytesPerSecond * if (publicationCopy) 2 else 1)
        }
        return Decision(required, remaining, reason)
    }
}
