package com.s23log.probe

import com.s23log.probe.core.*
import org.junit.Assert.*
import org.junit.Test

class BitratePolicyTest {
    private fun mode() = RecordingMode(1920, 1080, 30, DynamicRange.SDR, "encoder", "video/avc", 10_000_000,
        true, true, minimumBitRate = 3_000_000, maximumBitRate = 12_000_000)
    @Test fun targetsAreBoundedAndClampingIsVisible() {
        assertEquals(5_000_000, BitratePolicy.select(10_000_000, 3_000_000, 12_000_000, BitratePreset.LOW).effective)
        val high = BitratePolicy.select(10_000_000, 3_000_000, 12_000_000, BitratePreset.HIGH)
        assertEquals(15_000_000L, high.requested); assertEquals(12_000_000, high.effective); assertTrue(high.limited)
    }
    @Test fun selectionDoesNotCompoundOrChangeCaptureFormat() {
        val original = mode(); val changed = original.withBitratePreset(BitratePreset.HIGH).withBitratePreset(BitratePreset.LOW)
        assertEquals(original.withBitratePreset(BitratePreset.LOW), changed)
        assertEquals(original.key, changed.key); assertEquals(original.colour, changed.colour)
        assertNotEquals(original, changed) // Same compatibility key is not the same complete start intent.
    }
    @Test fun returningToStandardRestoresTheExactBaseline() {
        val original = mode(); assertEquals(original, original.withBitratePreset(BitratePreset.HIGH).withBitratePreset(BitratePreset.STANDARD))
    }
    @Test fun highTargetCannotOverflow() {
        val high = BitratePolicy.select(Int.MAX_VALUE, 1, Int.MAX_VALUE, BitratePreset.HIGH)
        assertTrue(high.requested > Int.MAX_VALUE); assertEquals(Int.MAX_VALUE, high.effective)
    }
    @Test(expected = IllegalArgumentException::class) fun rejectsInvalidCapabilityBounds() {
        BitratePolicy.select(10, 20, 5, BitratePreset.STANDARD)
    }
    @Test fun unknownSavedPresetUsesTheExistingStandardDefault() {
        assertEquals(BitratePreset.STANDARD, BitratePreset.fromStored(null)); assertEquals(BitratePreset.STANDARD, BitratePreset.fromStored("unknown"))
    }
    @Test fun manualIntentCannotBypassReadinessOnAnOrdinaryAeMode() {
        assertFalse(ModePlanning.recordingAllowed(EngineState.PREVIEW, mode(), false, true))
        assertTrue(ModePlanning.recordingAllowed(EngineState.PREVIEW, mode(), true, true))
        assertTrue(ModePlanning.recordingAllowed(EngineState.PREVIEW, mode(), false, false))
    }
}
