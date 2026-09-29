package com.s23log.probe.core

/** Forget a pending output only after its removal was confirmed. */
object JournalCleanup {
    fun run(delete: () -> Boolean, forget: () -> Boolean): Boolean {
        if (!try { delete() } catch (_: Exception) { false }) return false
        return try { forget() } catch (_: Exception) { false }
    }
}
