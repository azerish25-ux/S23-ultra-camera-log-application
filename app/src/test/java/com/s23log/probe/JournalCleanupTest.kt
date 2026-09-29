package com.s23log.probe
import com.s23log.probe.core.JournalCleanup
import org.junit.Assert.*
import org.junit.Test

class JournalCleanupTest {
    @Test fun failedDeleteKeepsJournal() {
        var forgotten = false
        assertFalse(JournalCleanup.run({ false }, { forgotten = true; true }))
        assertFalse(forgotten)
    }
    @Test fun thrownDeleteKeepsJournal() {
        var forgotten = false
        assertFalse(JournalCleanup.run({ error("provider offline") }, { forgotten = true; true }))
        assertFalse(forgotten)
    }
    @Test fun confirmedDeleteForgetsJournal() {
        var deleted = false
        assertTrue(JournalCleanup.run({ deleted = true; true }, { assertTrue(deleted); true }))
    }
    @Test fun failedForgetIsRetriable() { assertFalse(JournalCleanup.run({ true }, { false })) }
    @Test fun thrownForgetIsRetriable() { assertFalse(JournalCleanup.run({ true }, { error("preferences full") })) }
}
