package com.s23log.probe

import android.content.Context
import android.os.ParcelFileDescriptor
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.s23log.probe.storage.PendingMedia
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

/** These byte fixtures test storage ownership, not codec validity or image quality. */
@RunWith(AndroidJUnit4::class)
class StorageIntegrityTest {
    private val context: Context get() = InstrumentationRegistry.getInstrumentation().targetContext.also {
        (it.applicationContext as S23Application).awaitMediaRecovery()
    }
    private fun write(output: PendingMedia) {
        ParcelFileDescriptor.AutoCloseOutputStream(ParcelFileDescriptor.dup(output.descriptor.fileDescriptor)).use { it.write(byteArrayOf(1, 2, 3, 4)) }
        output.closeDescriptor()
    }
    private fun cleanup(uri: android.net.Uri) {
        PendingMedia.recoverable(context).filter { it.uri == uri }.forEach { PendingMedia.discardRecovery(context, it) }
    }
    @Test fun retainedVideoSurvivesAbortAndRecovery() {
        val output = PendingMedia.create(context, true)
        try {
            write(output)
            output.retain("injected verifier failure")
            output.abort()
            PendingMedia.recover(context)
            val entry = PendingMedia.recoverable(context).single { it.uri == output.uri }
            assertEquals(4L, entry.file.length())
            assertTrue(entry.reason.contains("verifier failure"))
            context.contentResolver.openInputStream(entry.uri).use { assertEquals(1, it!!.read()) }
        } finally { cleanup(output.uri) }
    }
    @Test fun interruptedNonemptyVideoIsNeverSweptAway() {
        val output = PendingMedia.create(context, true)
        try {
            write(output)
            assertFalse(PendingMedia.recoverable(context).any { it.uri == output.uri })
            PendingMedia.recover(context)
            assertTrue(PendingMedia.recoverable(context).any { it.uri == output.uri })
        } finally { cleanup(output.uri) }
    }
    @Test fun emptyVideoCanBeAborted() {
        val output = PendingMedia.create(context, true)
        output.abort()
        PendingMedia.recover(context)
        assertFalse(PendingMedia.recoverable(context).any { it.uri == output.uri })
    }
    @Test fun legacyPrivateVideoIsRetained() {
        val name = "S23Log-1-${UUID.randomUUID()}.mp4"
        val file = File(context.filesDir, "exports/captures/$name")
        file.parentFile!!.mkdirs(); file.writeBytes(byteArrayOf(5, 6))
        context.getSharedPreferences("s23log_pending_outputs_v1", Context.MODE_PRIVATE).edit().putBoolean("file:$name", true).commit()
        try {
            PendingMedia.recover(context)
            val entry = PendingMedia.recoverable(context).single { it.file == file }
            assertEquals(2L, entry.file.length())
            PendingMedia.discardRecovery(context, entry)
            assertFalse(file.exists())
        } finally { file.delete(); context.getSharedPreferences("s23log_pending_outputs_v1", Context.MODE_PRIVATE).edit().remove("file:$name").commit() }
    }
    @Test fun recoveryRejectsTraversalKeys() {
        val prefs = context.getSharedPreferences("s23log_pending_outputs_v1", Context.MODE_PRIVATE)
        prefs.edit().putString("video:../private.mp4", "retained:fixture").commit()
        try { assertFalse(PendingMedia.recoverable(context).any { it.file.name == "private.mp4" }) }
        finally { prefs.edit().remove("video:../private.mp4").commit() }
    }
}
