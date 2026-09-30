package com.s23log.probe

import android.Manifest
import android.content.pm.ActivityInfo
import android.content.res.Configuration
import android.graphics.Bitmap
import android.os.ParcelFileDescriptor
import android.provider.Settings
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

/** Emulator UI acceptance. Temporarily adjusts font scale and restores its original value. */
@RunWith(AndroidJUnit4::class)
class LargeTextLayoutTest {
    @get:Rule val permission: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private fun shell(command: String) {
        ParcelFileDescriptor.AutoCloseInputStream(instrumentation.uiAutomation.executeShellCommand(command)).use { it.readBytes() }
    }
    private fun await(scenario: ActivityScenario<MainActivity>, orientation: Int) {
        val ready = AtomicBoolean()
        repeat(400) {
            scenario.onActivity { ready.set(it.resources.configuration.orientation == orientation && it.resources.configuration.fontScale >= 1.29f &&
                it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") && it.findViewById<Button>(R.id.record).height > 0) }
            if (ready.get()) return
            Thread.sleep(150)
        }
        fail("Large-text live layout did not become ready")
    }
    @Test fun largeTextKeepsCaptureActionsFullyVisibleAndUnclippedInBothOrientations() {
        val context = instrumentation.targetContext
        val previous = Settings.System.getString(context.contentResolver, Settings.System.FONT_SCALE)?.toFloatOrNull()
        require(previous == null || previous.isFinite())
        try {
            shell("settings put system font_scale 1.3")
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                val directory = File(context.filesDir, "exports/accessibility-ui").apply { mkdirs() }
                for ((requested, expected, name) in listOf(
                    Triple(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT, Configuration.ORIENTATION_PORTRAIT, "large-text-portrait.png"),
                    Triple(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE, Configuration.ORIENTATION_LANDSCAPE, "large-text-landscape.png"))) {
                    scenario.onActivity { it.requestedOrientation = requested }; await(scenario, expected)
                    val drawn = CountDownLatch(1)
                    scenario.onActivity { activity ->
                        activity.window.decorView.postOnAnimation { activity.window.decorView.postOnAnimation { drawn.countDown() } }
                    }
                    assertTrue(drawn.await(10, TimeUnit.SECONDS)); instrumentation.waitForIdleSync()
                    val bitmap = requireNotNull(instrumentation.uiAutomation.takeScreenshot())
                    File(directory, name).outputStream().use { assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)) }; bitmap.recycle()
                    scenario.onActivity { activity ->
                        for (id in listOf(R.id.record, R.id.openControls, R.id.modeDetails, R.id.testMode, R.id.previewAids)) {
                            val button = activity.findViewById<Button>(id); val rect = android.graphics.Rect()
                            assertTrue(button.getGlobalVisibleRect(rect)); assertEquals(button.height, rect.height()); assertEquals(button.width, rect.width())
                            val layout = requireNotNull(button.layout)
                            assertTrue("${button.text} text is vertically clipped", layout.height <= button.height - button.compoundPaddingTop - button.compoundPaddingBottom)
                            for (line in 0 until layout.lineCount) assertEquals("${button.text} is ellipsized", 0, layout.getEllipsisCount(line))
                        }
                    }
                }
                scenario.onActivity { it.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED }
            }
        } finally {
            if (previous == null) shell("settings delete system font_scale") else shell("settings put system font_scale $previous")
        }
    }
}
