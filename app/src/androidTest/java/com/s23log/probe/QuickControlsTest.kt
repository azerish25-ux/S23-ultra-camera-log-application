package com.s23log.probe

import android.Manifest
import android.content.Context
import android.graphics.Bitmap
import android.view.KeyEvent
import android.view.TextureView
import android.view.View
import android.widget.*
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.storage.CameraSettings
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

@RunWith(AndroidJUnit4::class)
class QuickControlsTest {
    @get:Rule val permission: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private fun await(scenario: ActivityScenario<MainActivity>, label: String, condition: (MainActivity) -> Boolean) {
        val ready = AtomicBoolean()
        repeat(400) { scenario.onActivity { ready.set(condition(it)) }; if (ready.get()) return; Thread.sleep(150) }
        fail("Timed out waiting for $label")
    }
    @Test fun boundedDraftSlidersKeepPreviewAndRecordVisibleWithoutOpeningAKeyboard() {
        val prefs = context.getSharedPreferences("camera_settings_v1", Context.MODE_PRIVATE)
        val before = prefs.all.filterValues { it is String }
        try {
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                await(scenario, "live preview") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") && it.findViewById<Button>(R.id.record).isEnabled }
                val key = requireNotNull(CameraSettings.camera(context))
                val initial = CameraSettings.controls(context, key)
                var changedIso = 0
                scenario.onActivity { it.findViewById<Button>(R.id.openControls).performClick() }
                await(scenario, "laid-out partial controls drawer") { it.findViewById<ScrollView>(R.id.controlsPanel).height > 0 }
                scenario.onActivity { activity ->
                    val panel = activity.findViewById<ScrollView>(R.id.controlsPanel)
                    val preview = activity.findViewById<TextureView>(R.id.preview)
                    assertTrue(panel.height < preview.height)
                    assertTrue(panel.height > 0)
                    assertEquals(View.GONE, activity.findViewById<EditText>(R.id.isoInput).visibility)
                    assertTrue(activity.findViewById<CompoundButton>(R.id.manualExposure).isEnabled)
                    activity.findViewById<CompoundButton>(R.id.manualExposure).isChecked = true
                    val slider = activity.findViewById<SeekBar>(R.id.isoSlider)
                    assertTrue(slider.isEnabled)
                    slider.progress = 0
                    slider.dispatchKeyEvent(KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_DPAD_RIGHT))
                    slider.dispatchKeyEvent(KeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_DPAD_RIGHT))
                    changedIso = activity.findViewById<EditText>(R.id.isoInput).text.toString().toInt()
                    assertTrue(slider.progress > 0)
                    assertTrue(activity.findViewById<TextView>(R.id.isoValue).text.contains(changedIso.toString()))
                    assertEquals(initial, CameraSettings.controls(context, key)) // Draft did not submit a request.
                    activity.findViewById<CompoundButton>(R.id.manualExposure).isChecked = false
                    activity.findViewById<Button>(R.id.applyControls).performClick()
                }
                await(scenario, "explicitly applied draft") { CameraSettings.controls(context, key).iso == changedIso && it.findViewById<Button>(R.id.record).isEnabled }
                val drawn = CountDownLatch(1)
                scenario.onActivity { activity ->
                    val rect = android.graphics.Rect()
                    val record = activity.findViewById<Button>(R.id.record)
                    assertTrue(record.getGlobalVisibleRect(rect)); assertEquals(record.height, rect.height())
                    assertFalse(activity.currentFocus is EditText)
                    activity.window.decorView.postOnAnimation { activity.window.decorView.postOnAnimation { drawn.countDown() } }
                }
                assertTrue(drawn.await(10, TimeUnit.SECONDS))
                val instrumentation = InstrumentationRegistry.getInstrumentation(); instrumentation.waitForIdleSync()
                val bitmap = requireNotNull(instrumentation.uiAutomation.takeScreenshot())
                val directory = File(context.filesDir, "exports/quick-controls").apply { mkdirs() }
                File(directory, "quick-controls.png").outputStream().use { assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)) }; bitmap.recycle()
                scenario.recreate()
                await(scenario, "restored draft intent") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") && it.findViewById<EditText>(R.id.isoInput).text.toString() == changedIso.toString() }
                scenario.onActivity { assertEquals(View.GONE, it.findViewById<EditText>(R.id.isoInput).visibility) }
            }
        } finally {
            prefs.edit().clear().also { edit -> before.forEach { (key, value) -> edit.putString(key, value as String) } }.commit()
        }
    }
}
