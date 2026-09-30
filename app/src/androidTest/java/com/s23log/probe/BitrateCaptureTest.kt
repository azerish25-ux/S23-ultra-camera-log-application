package com.s23log.probe

import android.Manifest
import android.content.Context
import android.hardware.camera2.CameraManager
import android.media.MediaFormat
import android.widget.Button
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.camera.CameraCatalog
import com.s23log.probe.core.AudioMode
import com.s23log.probe.core.BitratePreset
import com.s23log.probe.storage.CameraSettings
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.atomic.AtomicBoolean

@RunWith(AndroidJUnit4::class)
class BitrateCaptureTest {
    @get:Rule val permission: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private fun await(scenario: ActivityScenario<MainActivity>, label: String, condition: (MainActivity) -> Boolean) {
        val ready = AtomicBoolean()
        repeat(400) {
            scenario.onActivity { ready.set(condition(it)) }
            if (ready.get()) return
            Thread.sleep(150)
        }
        fail("Timed out waiting for $label")
    }
    @Test fun bitrateSelectionNeverStartsCaptureOrChangesTheFormatSilently() {
        val prefs = context.getSharedPreferences("camera_settings_v1", Context.MODE_PRIVATE)
        val oldPreset = prefs.getString("bitratePreset", null); val oldAudio = prefs.getString("audioMode", null)
        CameraSettings.saveBitratePreset(context, BitratePreset.STANDARD); CameraSettings.saveAudio(context, AudioMode.OFF)
        try {
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                await(scenario, "recordable preview") { it.findViewById<Button>(R.id.record).isEnabled && it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") }
                val camera = requireNotNull(CameraSettings.camera(context))
                val key = requireNotNull(CameraSettings.mode(context, camera))
                val target = CameraCatalog.discover(context.getSystemService(CameraManager::class.java)).targets.single { it.key == camera }
                val high = CameraCatalog.plan(target, BitratePreset.HIGH).modes.firstOrNull { it.key == key }
                val previous = CaptureHistory.latest(context).report?.name
                scenario.onActivity { it.applyBitratePreset(BitratePreset.HIGH) }
                if (high != null) {
                    await(scenario, "accepted high target") { it.findViewById<Button>(R.id.record).isEnabled && it.findViewById<Button>(R.id.bitratePreset).text.contains(it.getString(R.string.bitrate_high)) }
                    assertEquals(high.bitRate, CameraCatalog.videoFormat(high).getInteger(MediaFormat.KEY_BIT_RATE))
                } else await(scenario, "explicit unsupported-preset rejection") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Bitrate preset rejected:") }
                assertEquals(key, CameraSettings.mode(context, camera))
                assertEquals(previous, CaptureHistory.latest(context).report?.name)
                scenario.onActivity { it.findViewById<Button>(R.id.record).performClick() }
                await(scenario, "written recording samples") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Recording ") }
                Thread.sleep(3000)
                scenario.onActivity { it.findViewById<Button>(R.id.record).performClick() }
                await(scenario, "validated result") { CaptureHistory.latest(context).report?.name != previous && CaptureHistory.latest(context).message.startsWith("Saved ") }
                val report = JSONObject(requireNotNull(CaptureHistory.latest(context).report).readText())
                val mode = report.getJSONObject("selectedMode")
                assertEquals(key, mode.getString("key"))
                assertEquals(if (high != null) "HIGH" else "STANDARD", mode.getString("bitratePreset"))
                if (high != null) assertEquals(high.bitRate, mode.getInt("bitrate"))
                val bounds = mode.getJSONObject("encoderBitrateRange")
                assertTrue(mode.getInt("bitrate") in bounds.getInt("minimum")..bounds.getInt("maximum"))
            }
        } finally {
            prefs.edit().also {
                if (oldPreset == null) it.remove("bitratePreset") else it.putString("bitratePreset", oldPreset)
                if (oldAudio == null) it.remove("audioMode") else it.putString("audioMode", oldAudio)
            }.commit()
        }
    }
}
