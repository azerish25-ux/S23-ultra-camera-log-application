package com.s23log.probe.core

import kotlin.math.roundToLong

/** Camera-advertised integer AE steps, with rational EV labels and bounded UI positions. */
data class ExposureCompensation(val minimum: Int, val maximum: Int, val stepNumerator: Int, val stepDenominator: Int) {
    init { require(minimum <= 0 && maximum >= 0 && maximum > minimum && stepNumerator > 0 && stepDenominator > 0) }
    private val span = maximum.toLong() - minimum
    val positions = minOf(span, 1000L).toInt()
    fun bounded(steps: Int) = steps.coerceIn(minimum, maximum)
    fun ev(steps: Int): Double = steps.toDouble() * stepNumerator / stepDenominator
    fun stepsAt(position: Int): Int = (minimum.toLong() + (span.toDouble() * position.coerceIn(0, positions) / positions).roundToLong()).toInt()
    fun positionOf(steps: Int): Int = ((bounded(steps).toLong() - minimum).toDouble() * positions / span).roundToLong().toInt()
    fun describe(): Map<String, Any> = mapOf("minimumSteps" to minimum, "maximumSteps" to maximum,
        "stepNumerator" to stepNumerator, "stepDenominator" to stepDenominator, "units" to "EV per integer AE compensation step")
}
