package com.s23log.probe.core

/** Bound the initial DNG path; larger sensor modes remain visible in diagnostics. */
object RawLimits {
    const val MAX_PIXELS = 24_000_000L
    fun supports(width: Int, height: Int): Boolean =
        width > 0 && height > 0 && width.toLong() * height <= MAX_PIXELS
}
