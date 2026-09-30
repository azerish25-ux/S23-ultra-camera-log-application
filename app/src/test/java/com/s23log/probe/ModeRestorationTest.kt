package com.s23log.probe

import com.s23log.probe.core.*
import org.junit.Assert.*
import org.junit.Test

class ModeRestorationTest {
    private val auto = RecordingMode(1280,720,30,DynamicRange.SDR,"codec","video/avc",4_000_000,true,true)
    private val manual = auto.copy(fps=24, ratePlan=RatePlan(RateControl.MANUAL_SENSOR))
    @Test fun firstRunChoosesAnOrdinaryDefault() { assertEquals(auto, ModePlanning.restore(listOf(manual,auto),null)) }
    @Test fun existingIntentMustMatchExactlyOrItsRecognizedLegacyKey() {
        assertEquals(manual, ModePlanning.restore(listOf(auto,manual),manual.key))
        assertEquals(manual, ModePlanning.restore(listOf(auto,manual),manual.legacyKey))
    }
    @Test fun missingSavedModeCannotSilentlyBecomeAnotherFormat() { assertNull(ModePlanning.restore(listOf(auto),manual.key)) }
    @Test fun emptyCatalogHasNoDefault() { assertNull(ModePlanning.restore(emptyList(),null)) }
    @Test fun ambiguousLegacyIntentDoesNotGuessACodec() {
        val other = auto.copy(mime="video/hevc")
        assertNull(ModePlanning.restore(listOf(auto, other), auto.legacyKey))
        assertEquals(other, ModePlanning.restore(listOf(auto, other), other.key))
    }
}
