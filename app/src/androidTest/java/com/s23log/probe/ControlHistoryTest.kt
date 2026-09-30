package com.s23log.probe

import android.Manifest
import android.content.Context
import android.widget.Button
import android.widget.CompoundButton
import android.widget.EditText
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.core.AudioMode
import com.s23log.probe.storage.CameraSettings
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.atomic.AtomicBoolean

@RunWith(AndroidJUnit4::class)
class ControlHistoryTest {
    @get:Rule val permission: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private fun await(scenario: ActivityScenario<MainActivity>, label: String, condition: (MainActivity) -> Boolean) {
        val ready = AtomicBoolean()
        repeat(400) { scenario.onActivity { ready.set(condition(it)) }; if (ready.get()) return; Thread.sleep(150) }
        fail("Timed out waiting for $label")
    }
    @Test fun originalReportRetainsMidTakeIntentAndSampledSensorEvidence() {
        val prefs = context.getSharedPreferences("camera_settings_v1", Context.MODE_PRIVATE)
        val before = prefs.all.filterValues { it is String }
        CameraSettings.saveAudio(context, AudioMode.OFF)
        try {
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                await(scenario, "live preview") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") && it.findViewById<Button>(R.id.record).isEnabled }
                val key = requireNotNull(CameraSettings.camera(context))
                val changedIso = if (CameraSettings.controls(context, key).iso == 250) 300 else 250
                val previous = CaptureHistory.latest(context).report?.name
                scenario.onActivity { it.findViewById<Button>(R.id.record).performClick() }
                await(scenario, "recording samples") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Recording ") }
                Thread.sleep(1200)
                scenario.onActivity {
                    // Change retained AUTO intent, not a claim that the sensor applied this ISO.
                    it.findViewById<CompoundButton>(R.id.manualExposure).isChecked = false
                    it.findViewById<EditText>(R.id.isoInput).setText(changedIso.toString())
                    it.findViewById<Button>(R.id.applyControls).performClick()
                }
                await(scenario, "accepted changed intent") { CameraSettings.controls(context, key).iso == changedIso }
                Thread.sleep(1500)
                scenario.onActivity { it.findViewById<Button>(R.id.record).performClick() }
                await(scenario, "validated recording") { CaptureHistory.latest(context).report?.name != previous && CaptureHistory.latest(context).message.startsWith("Saved ") }
                val report = JSONObject(requireNotNull(CaptureHistory.latest(context).report).readText())
                val history = report.getJSONObject("controlHistory")
                val requests = history.getJSONArray("requests")
                assertTrue(requests.length() >= 2)
                val latest = history.getJSONObject("latestRequest").getJSONObject("controls").getJSONObject("requested")
                assertEquals(changedIso, latest.getInt("iso")); assertFalse(latest.getBoolean("manualExposure"))
                val samples = history.getJSONArray("appliedSamples")
                assertTrue(samples.length() >= 2)
                for (i in 0 until samples.length()) {
                    val sample = samples.getJSONObject(i)
                    assertTrue(sample.getLong("observedMonotonicNs") > 0)
                    assertTrue(sample.getJSONObject("values").getLong("sensorTimestampNs") > 0)
                    if (i > 0) assertTrue(sample.getLong("observedMonotonicNs") - samples.getJSONObject(i - 1).getLong("observedMonotonicNs") >= history.getLong("sampleIntervalNs"))
                }
                assertEquals(0L, history.getLong("samplesDropped")); assertEquals(0L, history.getLong("requestsDropped"))
                assertEquals(0L, history.getLong("invalidClockObservations"))
            }
        } finally {
            prefs.edit().clear().also { edit -> before.forEach { (key, value) -> edit.putString(key, value as String) } }.commit()
        }
    }
}
