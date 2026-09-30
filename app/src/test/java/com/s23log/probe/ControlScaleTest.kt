package com.s23log.probe

import com.s23log.probe.core.ControlScale
import org.junit.Assert.*
import org.junit.Test

class ControlScaleTest {
    @Test fun endpointsAndOutOfRangeProgressAreExact() {
        val scale = ControlScale(50, 6400)
        assertEquals(50L, scale.value(-1)); assertEquals(50L, scale.value(0))
        assertEquals(6400L, scale.value(1000)); assertEquals(6400L, scale.value(1001))
        assertEquals(0, scale.progress(1)); assertEquals(1000, scale.progress(Long.MAX_VALUE))
    }
    @Test fun allSliderPositionsAreBoundedAndMonotonic() {
        for (scale in listOf(ControlScale(50, 6400), ControlScale(1000, 33_333_333), ControlScale(1, Long.MAX_VALUE))) {
            var last = scale.minimum
            for (p in 0..1000) { val value = scale.value(p); assertTrue(value in last..scale.maximum); last = value }
        }
    }
    @Test fun fixedValueRangesDoNotDivideByZero() {
        val scale = ControlScale(100, 100)
        assertEquals(100L, scale.value(800)); assertEquals(0, scale.progress(100))
    }
    @Test fun photographicStopsHaveUsefulResolution() {
        val scale = ControlScale(100, 6400)
        assertEquals(800L, scale.value(500)); assertEquals(500, scale.progress(800))
        for (p in 0..1000) assertTrue(kotlin.math.abs(scale.progress(scale.value(p)) - p) <= 2)
    }
    @Test fun shutterAnglesUseTheSelectedRateAndDoNotClaimAppliedTiming() {
        assertEquals(20_833_333L, ControlScale.shutterForAngle(180, 24))
        assertEquals(16_666_667L, ControlScale.shutterForAngle(180, 30))
        assertEquals(4_166_667L, ControlScale.shutterForAngle(90, 60))
        assertEquals(33_333_333L, ControlScale.shutterForAngle(360, 30))
    }
    @Test fun invalidCapabilitiesAndRatesAreRejected() {
        assertThrows(IllegalArgumentException::class.java) { ControlScale(0, 10) }
        assertThrows(IllegalArgumentException::class.java) { ControlScale(10, 1) }
        assertThrows(IllegalArgumentException::class.java) { ControlScale.shutterForAngle(0, 30) }
        assertThrows(IllegalArgumentException::class.java) { ControlScale.shutterForAngle(361, 30) }
        assertThrows(IllegalArgumentException::class.java) { ControlScale.shutterForAngle(180, 0) }
    }
}
