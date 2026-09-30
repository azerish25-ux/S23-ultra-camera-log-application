package com.s23log.probe.core

import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.roundToLong

/** Bounded logarithmic UI scale; camera-result verification is deliberately separate. */
data class ControlScale(val minimum: Long, val maximum: Long) {
    init { require(minimum > 0 && maximum >= minimum) }
    fun value(progress: Int): Long {
        val p = progress.coerceIn(0, STEPS)
        if (p == 0 || minimum == maximum) return minimum
        if (p == STEPS) return maximum
        return exp(ln(minimum.toDouble()) + ln(maximum.toDouble() / minimum) * p / STEPS).roundToLong().coerceIn(minimum, maximum)
    }
    fun progress(value: Long): Int {
        if (minimum == maximum) return 0
        return (ln(value.coerceIn(minimum, maximum).toDouble() / minimum) / ln(maximum.toDouble() / minimum) * STEPS).roundToLong().toInt().coerceIn(0, STEPS)
    }
    companion object {
        const val STEPS = 1000
        fun shutterForAngle(degrees: Int, fps: Int): Long {
            require(degrees in 1..360 && fps > 0)
            return (1_000_000_000.0 * degrees / (360.0 * fps)).roundToLong().coerceAtLeast(1)
        }
    }
}
