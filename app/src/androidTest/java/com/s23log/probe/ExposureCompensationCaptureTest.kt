package com.s23log.probe

import android.Manifest
import android.content.Context
import android.hardware.camera2.CameraManager
import android.view.KeyEvent
import android.widget.*
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.camera.CameraCatalog
import com.s23log.probe.core.AudioMode
import com.s23log.probe.storage.CameraSettings
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean

@RunWith(AndroidJUnit4::class)
class ExposureCompensationCaptureTest {
    @get:Rule val permission: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private fun await(scenario: ActivityScenario<MainActivity>, label: String, condition: (MainActivity) -> Boolean) {
        val ready = AtomicBoolean()
        repeat(400) { scenario.onActivity { ready.set(condition(it)) }; if (ready.get()) return; Thread.sleep(150) }
        fail("Timed out waiting for $label")
    }
    @Test fun advertisedAeStepsAreSubmittedAndRetainedWithoutClaimingPhysicalBrightness() {
        val prefs = context.getSharedPreferences("camera_settings_v1", Context.MODE_PRIVATE)
        val before = prefs.all.filterValues { it is String }
        CameraSettings.saveAudio(context, AudioMode.OFF)
        try {
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                await(scenario, "recordable preview") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") && it.findViewById<Button>(R.id.record).isEnabled }
                val key = requireNotNull(CameraSettings.camera(context))
                val target = CameraCatalog.discover(context.getSystemService(CameraManager::class.java)).targets.single { it.key == key }
                val range = target.exposureCompensation
                val directory = File(context.filesDir, "exports/exposure-compensation").apply { mkdirs() }
                if (range == null) {
                    scenario.onActivity {
                        assertFalse(it.findViewById<SeekBar>(R.id.compensationSlider).isEnabled)
                        assertEquals(it.getString(R.string.compensation_unavailable), it.findViewById<TextView>(R.id.compensationValue).text.toString())
                    }
                    File(directory, "result.json").writeText(JSONObject().put("status", "unavailable").put("camera", key).put("physicalBrightnessCertified", false).toString(2))
                    return@use
                }
                val expected = if (range.maximum > 0) range.maximum else range.minimum
                scenario.onActivity {
                    val manual = it.findViewById<CompoundButton>(R.id.manualExposure)
                    manual.isChecked = true; assertFalse(it.findViewById<SeekBar>(R.id.compensationSlider).isEnabled)
                    manual.isChecked = false
                    val slider = it.findViewById<SeekBar>(R.id.compensationSlider)
                    assertTrue(slider.isEnabled)
                    slider.progress = if (expected > 0) slider.max - 1 else 1
                    val direction = if (expected > 0) KeyEvent.KEYCODE_DPAD_RIGHT else KeyEvent.KEYCODE_DPAD_LEFT
                    slider.dispatchKeyEvent(KeyEvent(KeyEvent.ACTION_DOWN, direction)); slider.dispatchKeyEvent(KeyEvent(KeyEvent.ACTION_UP, direction))
                    it.findViewById<Button>(R.id.applyControls).performClick()
                }
                await(scenario, "accepted compensation intent") { CameraSettings.controls(context, key).exposureCompensationSteps == expected }
                val previous = CaptureHistory.latest(context).report?.name
                scenario.onActivity { it.findViewById<Button>(R.id.record).performClick() }
                await(scenario, "recording samples") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Recording ") }
                Thread.sleep(3000)
                scenario.onActivity { it.findViewById<Button>(R.id.record).performClick() }
                await(scenario, "validated result") { CaptureHistory.latest(context).report?.name != previous && CaptureHistory.latest(context).message.startsWith("Saved ") }
                val report = JSONObject(requireNotNull(CaptureHistory.latest(context).report).readText())
                assertEquals(expected, report.getJSONObject("requested").getJSONObject("controls").getInt("exposureCompensationSteps"))
                assertEquals(expected, report.getJSONObject("latestApplied").getInt("exposureCompensationSteps"))
                assertTrue(report.getJSONObject("latestApplied").getBoolean("exposureCompensationActive"))
                File(directory, "result.json").writeText(JSONObject().put("status", "capture_result_matched").put("steps", expected)
                    .put("range", JSONObject(range.describe())).put("physicalBrightnessCertified", false).toString(2))
            }
        } finally { prefs.edit().clear().also { edit -> before.forEach { (key, value) -> edit.putString(key, value as String) } }.commit() }
    }
}
