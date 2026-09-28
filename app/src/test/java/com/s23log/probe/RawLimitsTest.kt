package com.s23log.probe

import com.s23log.probe.core.RawLimits
import org.junit.Assert.*
import org.junit.Test

class RawLimitsTest {
    @Test fun acceptsBoundedSensorModes() {
        assertTrue(RawLimits.supports(4000, 3000))
        assertTrue(RawLimits.supports(6000, 4000))
    }
    @Test fun rejectsOversizedRawInsteadOfFallingBackToIt() {
        assertFalse(RawLimits.supports(6001, 4000))
        assertFalse(RawLimits.supports(16320, 12240))
    }
    @Test fun rejectsInvalidSizesAndAvoidsIntegerOverflow() {
        assertFalse(RawLimits.supports(0, 4000))
        assertFalse(RawLimits.supports(-1, 4000))
        assertFalse(RawLimits.supports(Int.MAX_VALUE, Int.MAX_VALUE))
    }
}
