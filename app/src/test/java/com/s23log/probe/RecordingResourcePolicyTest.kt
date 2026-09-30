package com.s23log.probe

import com.s23log.probe.core.RecordingResourcePolicy as Policy
import org.junit.Assert.*
import org.junit.Test

class RecordingResourcePolicyTest {
    private fun assess(free: Long?, staged: Long = 0, copy: Boolean = true, thermal: Int? = 0) =
        Policy.assess(free, staged, 8_000_000, 0, copy, thermal)
    @Test fun reservesFinalizationCopyPlusThirtySecondsAndFloor() {
        val decision = assess(1_000_000_000, 100_000_000)
        assertEquals(100_000_000 + 30_000_000 + Policy.FLOOR_BYTES, decision.requiredFreeBytes)
        assertNull(decision.stopReason)
    }
    @Test fun olderPrivateMoveDoesNotReserveAnotherFullCopy() {
        assertEquals(30_000_000 + Policy.FLOOR_BYTES, assess(1_000_000_000, 100_000_000, false).requiredFreeBytes)
    }
    @Test fun rejectsInsufficientAndUnknownStorage() {
        assertEquals("storage_reserve_reached", assess(1).stopReason)
        assertEquals("storage_unavailable", assess(null).stopReason)
        assertEquals("storage_unavailable", assess(-1).stopReason)
    }
    @Test fun boundaryIsExplicit() {
        val threshold = assess(Long.MAX_VALUE).requiredFreeBytes
        assertNull(assess(threshold).stopReason)
        assertNotNull(assess(threshold - 1).stopReason)
        assertEquals(0L, assess(threshold).remainingSecondsEstimate)
    }
    @Test fun allSevereThermalLevelsStopButModerateDoesNot() {
        for (level in 3..6) assertEquals("thermal_severe", assess(Long.MAX_VALUE, thermal = level).stopReason)
        for (level in 0..2) assertNull(assess(Long.MAX_VALUE, thermal = level).stopReason)
        assertNull(assess(Long.MAX_VALUE, thermal = null).stopReason)
    }
    @Test fun remainingEstimateAccountsForGrowingPublicationDebt() {
        val threshold = assess(Long.MAX_VALUE).requiredFreeBytes
        assertEquals(5L, assess(threshold + 10_000_000).remainingSecondsEstimate)
        assertEquals(10L, assess(threshold + 10_000_000, copy = false).remainingSecondsEstimate)
    }
    @Test fun bitrateAndAudioChangeTheReserve() {
        val video = Policy.assess(Long.MAX_VALUE, 0, 200_000_000, 0, true, 0)
        val audio = Policy.assess(Long.MAX_VALUE, 0, 200_000_000, 192_000, true, 0)
        assertTrue(audio.requiredFreeBytes > video.requiredFreeBytes)
    }
    @Test fun copyDebtCannotOverflowIntoAnUnsafeApproval() {
        val decision = assess(1_000_000_000, Long.MAX_VALUE)
        assertEquals(Long.MAX_VALUE, decision.requiredFreeBytes)
        assertEquals("storage_reserve_reached", decision.stopReason)
        assertEquals("storage_reserve_reached", assess(Long.MAX_VALUE, Long.MAX_VALUE).stopReason)
    }
}
