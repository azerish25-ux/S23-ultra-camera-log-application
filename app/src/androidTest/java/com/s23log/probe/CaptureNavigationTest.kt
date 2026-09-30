package com.s23log.probe

import android.Manifest
import android.graphics.Bitmap
import android.view.View
import android.widget.Button
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

@RunWith(AndroidJUnit4::class)
class CaptureNavigationTest {
    @get:Rule val permission: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private fun live(scenario: ActivityScenario<MainActivity>) {
        val ready = AtomicBoolean()
        repeat(400) { scenario.onActivity { ready.set(it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview")) }; if (ready.get()) return; Thread.sleep(150) }
        fail("Preview did not resume after navigation")
    }
    private fun capture(scenario: ActivityScenario<MainActivity>, name: String) {
        val drawn = CountDownLatch(1)
        scenario.onActivity { it.window.decorView.postOnAnimation { it.window.decorView.postOnAnimation { drawn.countDown() } } }
        assertTrue(drawn.await(10, TimeUnit.SECONDS)); instrumentation.waitForIdleSync()
        val bitmap = requireNotNull(instrumentation.uiAutomation.takeScreenshot())
        val directory = File(instrumentation.targetContext.filesDir, "exports/navigation-ui").apply { mkdirs() }
        File(directory, name).outputStream().use { assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)) }; bitmap.recycle()
    }
    @Test fun manualSettingsAndClipsHaveSeparateEntriesAndPreviewResumes() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            live(scenario)
            scenario.onActivity {
                it.findViewById<Button>(R.id.openControls).performClick()
                it.findViewById<Button>(R.id.openSettings).performClick()
                assertEquals(View.VISIBLE, it.findViewById<View>(R.id.settingsFields).visibility)
                assertEquals(View.GONE, it.findViewById<View>(R.id.manualControlFields).visibility)
                assertTrue(it.findViewById<Button>(R.id.record).isEnabled)
            }
            capture(scenario, "settings-pane.png")
            scenario.onActivity {
                it.findViewById<Button>(R.id.backToManual).performClick()
                assertEquals(View.VISIBLE, it.findViewById<View>(R.id.manualControlFields).visibility)
                assertEquals(View.GONE, it.findViewById<View>(R.id.settingsFields).visibility)
                it.findViewById<Button>(R.id.closeControls).performClick()
            }
            val monitor = instrumentation.addMonitor(CaptureLibraryActivity::class.java.name, null, false)
            try {
                scenario.onActivity { it.findViewById<Button>(R.id.clipsTab).performClick() }
                val library = instrumentation.waitForMonitorWithTimeout(monitor, 10000)
                assertNotNull("Clips must open the capture library", library)
                instrumentation.runOnMainSync { requireNotNull(library).finish() }
                live(scenario)
            } finally { instrumentation.removeMonitor(monitor) }
            scenario.onActivity {
                it.findViewById<Button>(R.id.openControls).performClick()
                assertEquals(View.VISIBLE, it.findViewById<View>(R.id.manualControlFields).visibility)
            }
            capture(scenario, "manual-pane.png")
        }
    }
}
