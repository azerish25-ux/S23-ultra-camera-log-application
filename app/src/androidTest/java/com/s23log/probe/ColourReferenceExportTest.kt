package com.s23log.probe

import androidx.core.content.FileProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.s23log.probe.core.ColourReferenceBundle
import com.s23log.probe.core.MediaIdentity
import com.s23log.probe.storage.ColourReferenceStore
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

@RunWith(AndroidJUnit4::class)
class ColourReferenceExportTest {
    @Test fun appOwnedReferenceExportSurvivesObserverDetachAndMatchesShareableBytes() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val ready = CountDownLatch(1)
        val store = ColourReferenceStore(context)
        var files = emptyList<File>()
        var failure: String? = null
        val detached: (ColourReferenceStore.State) -> Unit = { }
        val observer: (ColourReferenceStore.State) -> Unit = { state ->
            if (!state.running && (state.files.isNotEmpty() || state.error != null)) { files = state.files; failure = state.error; ready.countDown() }
        }
        instrumentation.runOnMainSync {
            store.observe(detached); store.prepare(); store.remove(detached); store.observe(observer)
        }
        assertTrue(ready.await(30, TimeUnit.SECONDS))
        instrumentation.runOnMainSync { store.remove(observer) }
        assertNull(failure); assertEquals(5, files.size)
        val manifest = JSONObject(files.single { it.name == "manifest.json" }.readText())
        assertEquals(ColourReferenceBundle.VERSION, manifest.getString("referenceVersion"))
        assertFalse(manifest.getBoolean("customLogRecordingEnabled")); assertFalse(manifest.getBoolean("physicalCameraCertified"))
        val identities = manifest.getJSONArray("files")
        assertEquals(4, identities.length())
        for (i in 0 until identities.length()) {
            val entry = identities.getJSONObject(i)
            val file = files.single { it.name == entry.getString("name") }
            val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", file)
            val actual = requireNotNull(context.contentResolver.openInputStream(uri)).use(MediaIdentity::read)
            assertEquals(entry.getJSONObject("identity").getString("sha256"), actual.sha256)
            assertEquals(entry.getJSONObject("identity").getLong("byteCount"), actual.byteCount)
        }
    }
}
