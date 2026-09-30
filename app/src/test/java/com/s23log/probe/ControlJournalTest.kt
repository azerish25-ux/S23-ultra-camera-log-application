package com.s23log.probe

import com.s23log.probe.core.ControlJournal
import org.junit.Assert.*
import org.junit.Test

class ControlJournalTest {
    private fun list(journal: ControlJournal, key: String) = journal.describe()[key] as List<*>
    @Test fun appliedMetadataIsSampledWithSeparateObservedAndSensorClocks() {
        val journal = ControlJournal(sampleIntervalNs = 100)
        journal.noteApplied(1000, mapOf("sensorTimestampNs" to 50L))
        journal.noteApplied(1050, mapOf("sensorTimestampNs" to 100L))
        journal.noteApplied(1100, mapOf("sensorTimestampNs" to 150L))
        assertEquals(2, list(journal, "appliedSamples").size)
        val first = list(journal, "appliedSamples").first() as Map<*, *>
        assertEquals(1000L, first["observedMonotonicNs"])
        assertEquals(50L, (first["values"] as Map<*, *>)["sensorTimestampNs"])
    }
    @Test fun capsExposeLossAndRetainLatestEvidence() {
        val journal = ControlJournal(2, 1, 100)
        for (i in 1..5) { journal.noteApplied(i * 100L, mapOf("iso" to i)); journal.noteRequest(i * 100L, mapOf("iso" to i)) }
        assertEquals(2, list(journal, "appliedSamples").size); assertEquals(1, list(journal, "requests").size)
        val result = journal.describe()
        assertEquals(3L, result["samplesDropped"]); assertEquals(4L, result["requestsDropped"])
        assertEquals(5, (((result["latestApplied"] as Map<*, *>)["values"]) as Map<*, *>)["iso"])
        assertEquals(5, (((result["latestRequest"] as Map<*, *>)["controls"]) as Map<*, *>)["iso"])
    }
    @Test fun duplicateRequestsAreDeduplicatedButReturningToOldIntentIsAChange() {
        val journal = ControlJournal()
        journal.noteRequest(1, mapOf("iso" to 100)); journal.noteRequest(2, mapOf("iso" to 100))
        journal.noteRequest(3, mapOf("iso" to 200)); journal.noteRequest(4, mapOf("iso" to 100))
        assertEquals(3, list(journal, "requests").size)
    }
    @Test fun externallyMutableNestedValuesCannotRewriteCapturedEvidence() {
        val inner = mutableMapOf<String, Any?>("iso" to 100)
        val journal = ControlJournal()
        journal.noteRequest(1, mapOf("requested" to inner)); inner["iso"] = 900
        val event = list(journal, "requests").single() as Map<*, *>
        assertEquals(100, (((event["controls"] as Map<*, *>)["requested"]) as Map<*, *>)["iso"])
    }
    @Test fun invalidAndRegressedSampleClocksAreCountedAndRejected() {
        val journal = ControlJournal()
        journal.noteApplied(100, emptyMap()); journal.noteApplied(50, emptyMap()); journal.noteRequest(0, emptyMap())
        assertEquals(2L, journal.describe()["invalidClockObservations"]); assertEquals(1, list(journal, "appliedSamples").size)
    }
    @Test fun oldSnapshotsDoNotGainLaterEvents() {
        val journal = ControlJournal(); val old = journal.describe()
        journal.noteRequest(1, emptyMap()); assertTrue((old["requests"] as List<*>).isEmpty())
    }
}
