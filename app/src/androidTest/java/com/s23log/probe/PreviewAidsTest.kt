package com.s23log.probe

import android.Manifest
import android.content.Context
import android.graphics.Bitmap
import android.widget.Button
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.core.AudioMode
import com.s23log.probe.core.PreviewAid
import com.s23log.probe.storage.CameraSettings
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

@RunWith(AndroidJUnit4::class)
class PreviewAidsTest {
    @get:Rule val permission: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private fun await(scenario: ActivityScenario<MainActivity>, label: String, condition: (MainActivity) -> Boolean) {
        val ready = AtomicBoolean()
        for (attempt in 0 until 400) {
            scenario.onActivity { ready.set(condition(it)) }
            if (ready.get()) return
            Thread.sleep(150)
        }
        fail("Timed out waiting for $label")
    }
    @Test fun displayAnalysisPersistsAndCoexistsWithARealRecording() {
        val settings = context.getSharedPreferences("camera_settings_v1", Context.MODE_PRIVATE)
        val oldAudio = settings.getString("audioMode", null)
        val prefs = context.getSharedPreferences("preview_aids_v1", Context.MODE_PRIVATE)
        val oldAids = prefs.getStringSet("selected", null)?.toSet()
        CameraSettings.saveAudio(context, AudioMode.OFF)
        try {
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                await(scenario, "live preview") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") }
                scenario.onActivity { it.applyPreviewAids(PreviewAid.entries.toSet()) }
                await(scenario, "bounded fresh display analysis") {
                    val evidence = it.findViewById<PreviewAidsView>(R.id.previewAidsOverlay).evidence()
                    evidence["fresh"] == true && (evidence["validPixels"] as? Int ?: 0) > 0
                }
                val directory = File(context.filesDir, "exports/preview-aids").apply { mkdirs() }
                scenario.onActivity {
                    assertFalse(it.findViewById<android.view.TextureView>(R.id.preview).isOpaque)
                    val evidence = it.findViewById<PreviewAidsView>(R.id.previewAidsOverlay).evidence()
                    assertEquals(160, evidence["sampleWidth"]); assertEquals(90, evidence["sampleHeight"])
                    assertEquals(false, evidence["sensorExposureCalibration"])
                    File(directory, "display-analysis.json").writeText(JSONObject(evidence).toString(2))
                }
                val drawn = CountDownLatch(1)
                scenario.onActivity { it.window.decorView.postOnAnimation { it.window.decorView.postOnAnimation { drawn.countDown() } } }
                assertTrue(drawn.await(10, TimeUnit.SECONDS))
                val instrumentation = InstrumentationRegistry.getInstrumentation()
                instrumentation.waitForIdleSync()
                val screenshot = requireNotNull(instrumentation.uiAutomation.takeScreenshot())
                File(directory, "preview-aids.png").outputStream().use { assertTrue(screenshot.compress(Bitmap.CompressFormat.PNG, 100, it)) }
                screenshot.recycle()
                val previous = CaptureHistory.latest(context).report?.name
                scenario.onActivity { assertTrue(it.findViewById<Button>(R.id.record).isEnabled); it.findViewById<Button>(R.id.record).performClick() }
                await(scenario, "first written recording sample") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Recording ") }
                Thread.sleep(1500)
                scenario.onActivity { it.applyPreviewAids(setOf(PreviewAid.GRID)) }
                Thread.sleep(1500)
                scenario.onActivity { it.findViewById<Button>(R.id.record).performClick() }
                await(scenario, "new validated capture") {
                    val entry = CaptureHistory.latest(context)
                    entry.report != null && entry.report.name != previous && entry.message.startsWith("Saved ")
                }
                val report = JSONObject(requireNotNull(CaptureHistory.latest(context).report).readText())
                assertFalse(report.getBoolean("customLog")); assertTrue(report.getBoolean("videoOnly"))
                val aids = report.getJSONObject("previewAids")
                assertEquals(7, aids.getJSONArray("initial").length())
                assertTrue(aids.getJSONArray("changes").length() >= 1); assertEquals(0, aids.getInt("changesDropped"))
                scenario.recreate()
                await(scenario, "restored preview") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") }
                scenario.onActivity {
                    val view = it.findViewById<PreviewAidsView>(R.id.previewAidsOverlay)
                    assertEquals(setOf(PreviewAid.GRID), view.features())
                    assertEquals(0L, view.evidence()["sampleCount"])
                }
            }
        } finally {
            settings.edit().also { if (oldAudio == null) it.remove("audioMode") else it.putString("audioMode", oldAudio) }.commit()
            prefs.edit().also { if (oldAids == null) it.remove("selected") else it.putStringSet("selected", oldAids) }.commit()
        }
    }
}
