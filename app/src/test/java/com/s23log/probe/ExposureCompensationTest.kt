package com.s23log.probe

import com.s23log.probe.core.ExposureCompensation
import org.junit.Assert.*
import org.junit.Test

class ExposureCompensationTest {
    @Test fun rationalStepsAndZeroMapExactly() {
        val range = ExposureCompensation(-6, 6, 1, 3)
        assertEquals(-2.0, range.ev(-6), 1e-9); assertEquals(1.0, range.ev(3), 1e-9)
        assertEquals(6, range.positionOf(0)); assertEquals(0, range.stepsAt(6))
        for (step in -6..6) assertEquals(step, range.stepsAt(range.positionOf(step)))
    }
    @Test fun submittedStepsAreBoundedButReportedValuesAreNeverSilentlyClipped() {
        val range = ExposureCompensation(-2, 2, 1, 2)
        assertEquals(-2, range.bounded(Int.MIN_VALUE)); assertEquals(2, range.bounded(Int.MAX_VALUE))
        assertEquals(2.0, range.ev(4), 0.0)
        assertEquals(-2, range.stepsAt(-1)); assertEquals(2, range.stepsAt(999))
    }
    @Test fun hugeAdvertisedRangesCannotOverflowOrAllocateHugeSliders() {
        val range = ExposureCompensation(Int.MIN_VALUE, Int.MAX_VALUE, 1, 3)
        assertEquals(1000, range.positions); assertEquals(Int.MIN_VALUE, range.stepsAt(0)); assertEquals(Int.MAX_VALUE, range.stepsAt(1000))
        assertEquals(0, range.positionOf(Int.MIN_VALUE)); assertEquals(1000, range.positionOf(Int.MAX_VALUE))
    }
    @Test fun fixedUnsupportedAndInvalidRangesFailClosed() {
        for (values in listOf(listOf(0,0,1,3), listOf(1,3,1,3), listOf(-3,-1,1,3), listOf(-3,3,0,3), listOf(-3,3,1,0)))
            assertThrows(IllegalArgumentException::class.java) { ExposureCompensation(values[0],values[1],values[2],values[3]) }
    }
}
