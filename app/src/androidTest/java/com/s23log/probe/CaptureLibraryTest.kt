package com.s23log.probe

import android.content.Context
import android.content.ContextWrapper
import android.net.Uri
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import com.s23log.probe.storage.CaptureLibrary
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class CaptureLibraryTest {
    private lateinit var context: Context
    private lateinit var root: File
    @Before fun isolatedLibrary() {
        val app = InstrumentationRegistry.getInstrumentation().targetContext
        root = File(app.cacheDir, "library-test-${UUID.randomUUID()}").apply { mkdirs() }
        context = object : ContextWrapper(app) { override fun getFilesDir() = root }
    }
    @After fun removeTestFixture() { root.deleteRecursively() }
    private fun uri(index: Int) = Uri.parse("content://media/external/video/media/$index")
    private fun report() = File(root, "exports/validation/recording-${UUID.randomUUID()}.json").apply {
        parentFile!!.mkdirs(); writeText("{\"status\":\"checked\"}")
    }

    @Test fun retainsMultipleCapturesAndDeduplicatesCompletion() {
        val first = report(); val second = report()
        CaptureLibrary.remember(context, listOf(uri(1)), first, "First capture")
        CaptureLibrary.remember(context, listOf(uri(2)), second, "Second capture")
        CaptureLibrary.remember(context, listOf(uri(1)), first, "Repeated completion")
        val entries = CaptureLibrary.read(context).entries
        assertEquals(2, entries.size)
        assertEquals(setOf("First capture", "Second capture"), entries.map { it.message }.toSet())
        assertTrue(entries.all { it.report!!.isFile })
    }

    @Test fun missingReportsAndMediaNeverDeleteTheCaptureRecord() {
        val report = report()
        CaptureLibrary.remember(context, listOf(uri(2147483647)), report, "Original evidence status")
        assertTrue(report.delete())
        val record = CaptureLibrary.read(context).entries.single()
        assertNull(record.report)
        assertFalse(CaptureLibrary.accessible(context, record.uris.single()))
        assertEquals(1, CaptureLibrary.read(context).entries.size)
    }

    @Test fun malformedRecordDoesNotHideOtherCaptures() {
        CaptureLibrary.remember(context, listOf(uri(1)), report(), "Retained good record")
        File(root, "capture-library/${"0".repeat(64)}.json").writeText("not json")
        val read = CaptureLibrary.read(context)
        assertEquals(1, read.entries.size)
        assertEquals(1, read.unreadableRecords)
        assertEquals("Retained good record", read.entries.single().message)
    }

    @Test fun rejectsForeignProvidersAndFileUris() {
        for (uri in listOf(Uri.parse("file:///private/file"), Uri.parse("content://other.provider/private"))) {
            assertFalse(CaptureLibrary.accessible(context, uri))
            try { CaptureLibrary.remember(context, listOf(uri), null, "Invalid"); fail("Must reject $uri") }
            catch (_: IllegalArgumentException) { }
        }
        assertTrue(CaptureLibrary.read(context).entries.isEmpty())
    }

    @Test fun emptyAttemptsAreNotIndexedAndUnverifiedLabelsStayUnchanged() {
        CaptureLibrary.remember(context, emptyList(), report(), "Rejected empty attempt")
        assertTrue(CaptureLibrary.read(context).entries.isEmpty())
        CaptureLibrary.remember(context, listOf(uri(1)), null, "NOT a verified recording")
        assertEquals("NOT a verified recording", CaptureLibrary.read(context).entries.single().message)
    }

    @Test fun libraryReloadsAfterRecreationWithoutCameraPermission() {
        ActivityScenario.launch(CaptureLibraryActivity::class.java).use { scenario ->
            fun loaded() {
                val ready = java.util.concurrent.atomic.AtomicBoolean(false)
                repeat(100) {
                    scenario.onActivity { activity ->
                        ready.set(activity.findViewById<android.widget.TextView>(R.id.captureLibraryStatus).text.toString() != activity.getString(R.string.library_loading))
                    }
                    if (ready.get()) return
                    Thread.sleep(50)
                }
                fail("Library did not finish loading")
            }
            loaded(); scenario.recreate(); loaded()
            scenario.onActivity {
                val list = it.findViewById<android.widget.ListView>(R.id.captureLibraryList)
                assertTrue(list.isShown)
                assertNotNull("Successful load must bind the adapter; an error message is not success", list.adapter)
            }
            val instrumentation = InstrumentationRegistry.getInstrumentation()
            fun screenshot(name: String) {
                val thumbnailReady = java.util.concurrent.atomic.AtomicBoolean(false)
                for (attempt in 0 until 200) {
                    scenario.onActivity { activity ->
                        val list = activity.findViewById<android.widget.ListView>(R.id.captureLibraryList)
                        val hasVideos = (0 until list.adapter.count).any {
                            (list.adapter.getItem(it) as CaptureLibrary.Entry).mimeType == "video/mp4"
                        }
                        val visibleThumbnailsReady = list.childCount > 0 && (0 until list.childCount).all {
                            val entry = list.adapter.getItem(list.firstVisiblePosition + it) as CaptureLibrary.Entry
                            entry.mimeType != "video/mp4" ||
                                list.getChildAt(it).findViewById<android.widget.ImageView>(R.id.libraryThumbnail)?.contentDescription == activity.getString(R.string.library_thumbnail)
                        }
                        thumbnailReady.set(!hasVideos || visibleThumbnailsReady)
                    }
                    if (thumbnailReady.get()) break
                    Thread.sleep(50)
                }
                assertTrue("Saved video thumbnail did not render", thumbnailReady.get())
                val drawn = java.util.concurrent.CountDownLatch(1)
                scenario.onActivity { activity ->
                    val view = activity.window.decorView
                    view.postOnAnimation { view.postOnAnimation { drawn.countDown() } }
                }
                assertTrue("Updated library frame was not drawn", drawn.await(10, java.util.concurrent.TimeUnit.SECONDS))
                instrumentation.waitForIdleSync()
                val image = instrumentation.uiAutomation.takeScreenshot()
                assertNotNull(image)
                val destination = File(instrumentation.targetContext.filesDir, "exports/library-ui/$name.png")
                destination.parentFile!!.mkdirs()
                destination.outputStream().use { assertTrue(image.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, it)) }
                image.recycle()
            }
            screenshot("library")
            scenario.onActivity { it.requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE }
            val landscape = java.util.concurrent.atomic.AtomicBoolean(false)
            for (attempt in 0 until 100) {
                scenario.onActivity { landscape.set(it.resources.configuration.orientation == android.content.res.Configuration.ORIENTATION_LANDSCAPE) }
                if (landscape.get()) break
                Thread.sleep(50)
            }
            assertTrue("Library did not rotate", landscape.get())
            loaded(); screenshot("library-landscape")
        }
    }
}
