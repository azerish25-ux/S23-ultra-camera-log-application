package com.s23log.probe

import android.Manifest
import android.content.Context
import android.hardware.camera2.CameraManager
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.camera.CameraCatalog
import com.s23log.probe.storage.CameraSettings
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.atomic.AtomicBoolean

@RunWith(AndroidJUnit4::class)
class ModeRestorationCaptureTest {
    @get:Rule val permission: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private fun await(scenario: ActivityScenario<MainActivity>, label: String, condition: (MainActivity) -> Boolean) {
        val ready = AtomicBoolean()
        repeat(400) { scenario.onActivity { ready.set(condition(it)) }; if (ready.get()) return; Thread.sleep(150) }
        fail("Timed out waiting for $label")
    }
    @Test fun unavailableSavedFormatRequiresExplicitSelectionAcrossRecreation() {
        val prefs = context.getSharedPreferences("camera_settings_v1", Context.MODE_PRIVATE)
        val before = prefs.all.filterValues { it is String }
        val target = CameraCatalog.discover(context.getSystemService(CameraManager::class.java)).targets.first()
        val choice = CameraCatalog.plan(target, CameraSettings.bitratePreset(context)).modes.first { !it.ratePlan.requiresManual }
        val missing = "unavailable-format-for-regression"
        CameraSettings.select(context, target.key); CameraSettings.saveMode(context, target.key, missing)
        try {
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                fun blocked() {
                    await(scenario, "preview without hidden format fallback") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") }
                    scenario.onActivity {
                        assertFalse(it.findViewById<Button>(R.id.record).isEnabled)
                        assertEquals(it.getString(R.string.choose_format), it.findViewById<Spinner>(R.id.modeSelector).selectedItem.toString())
                        assertEquals(missing, CameraSettings.mode(context, target.key))
                    }
                }
                blocked(); scenario.recreate(); blocked()
                scenario.onActivity {
                    val spinner = it.findViewById<Spinner>(R.id.modeSelector)
                    spinner.setSelection((0 until spinner.count).first { index -> spinner.getItemAtPosition(index).toString() == choice.label })
                }
                await(scenario, "explicitly selected recording format") { CameraSettings.mode(context, target.key) == choice.key && it.findViewById<Button>(R.id.record).isEnabled }
            }
        } finally { prefs.edit().clear().also { edit -> before.forEach { (key, value) -> edit.putString(key, value as String) } }.commit() }
    }
}
