package com.s23log.probe

import com.s23log.probe.core.ManualResultPolicy as Policy
import org.junit.Assert.*
import org.junit.Test

class ManualResultPolicyTest {
    private fun assess(iso: Int? = 100, exposure: Long? = 10_000_000, frame: Long? = 40_000_000, off: Boolean = true) =
        Policy.assess(100, 10_000_000, 40_000_000, iso, exposure, frame, off)
    @Test fun exactAppliedValuesPass() { assertTrue(assess().matched) }
    @Test fun aeOffAloneIsNotConfirmation() { assertFalse(assess(iso = 400).matched); assertFalse(assess(exposure = 30_000_000).matched) }
    @Test fun autoExposureCannotPassWithMatchingNumbers() { assertEquals("auto_exposure_active", assess(off = false).status) }
    @Test fun missingValuesNeverPass() {
        assertEquals("missing_sensor_metadata", assess(iso = null).status)
        assertEquals("missing_sensor_metadata", assess(exposure = null).status)
        assertEquals("missing_sensor_metadata", assess(frame = null).status)
    }
    @Test fun toleranceBoundariesRemainExplicit() {
        assertTrue(assess(iso = 105, exposure = 10_500_000, frame = 41_200_000).matched)
        assertFalse(assess(iso = 106).matched); assertFalse(assess(exposure = 10_500_001).matched)
        assertFalse(assess(frame = 41_200_001).matched)
    }
    @Test fun twentyFiveFpsCannotConfirmTwentyFour() {
        assertFalse(Policy.assess(100, 10_000_000, 1_000_000_000L / 24, 100, 10_000_000, 40_000_000, true).matched)
    }
    @Test fun nonpositiveResultsAreRejected() { assertFalse(assess(iso = 0).matched); assertFalse(assess(exposure = -1).matched) }
    @Test fun optionalFrameTargetStaysUnmeasured() {
        val result = Policy.assess(100, 10_000_000, null, 100, 10_000_000, null, true)
        assertTrue(result.matched); assertNull(result.frameMatched)
    }
}
