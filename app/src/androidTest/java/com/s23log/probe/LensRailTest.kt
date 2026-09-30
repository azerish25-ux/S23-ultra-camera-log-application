package com.s23log.probe

import android.Manifest
import android.content.Context
import android.content.pm.ActivityInfo
import android.content.res.Configuration
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.AdaptiveIconDrawable
import android.os.Build
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
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
class LensRailTest {
    @get:Rule val permission: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private fun await(scenario: ActivityScenario<MainActivity>, label: String, condition: (MainActivity) -> Boolean) {
        val ready = AtomicBoolean()
        repeat(400) { scenario.onActivity { ready.set(condition(it)) }; if (ready.get()) return; Thread.sleep(150) }
        fail("Timed out waiting for $label")
    }
    private fun screenshot(scenario: ActivityScenario<MainActivity>, file: File) {
        val drawn = CountDownLatch(1)
        scenario.onActivity { it.window.decorView.postOnAnimation { it.window.decorView.postOnAnimation { drawn.countDown() } } }
        assertTrue(drawn.await(10, TimeUnit.SECONDS))
        val instrumentation = InstrumentationRegistry.getInstrumentation(); instrumentation.waitForIdleSync()
        val bitmap = requireNotNull(instrumentation.uiAutomation.takeScreenshot())
        file.outputStream().use { assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)) }; bitmap.recycle()
    }
    @Test fun explicitRouteSwitchClosesRecordReadinessAndSurvivesRecreation() {
        val prefs = context.getSharedPreferences("camera_settings_v1", Context.MODE_PRIVATE)
        val before = prefs.all.filterValues { it is String }
        val directory = File(context.filesDir, "exports/lens-ui").apply { mkdirs() }
        try {
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                scenario.onActivity { it.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_PORTRAIT }
                await(scenario, "live portrait route rail") { it.resources.configuration.orientation == Configuration.ORIENTATION_PORTRAIT && it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") && it.findViewById<LinearLayout>(R.id.lensRail).childCount > 0 }
                var expected = requireNotNull(CameraSettings.camera(context))
                scenario.onActivity { activity ->
                    val rail = activity.findViewById<LinearLayout>(R.id.lensRail)
                    val other = (0 until rail.childCount).map { rail.getChildAt(it) as Button }.firstOrNull { it.tag != expected }
                    if (other != null) {
                        expected = other.tag as String
                        other.performClick()
                        assertFalse(activity.findViewById<Button>(R.id.record).isEnabled)
                        for (i in 0 until rail.childCount) assertFalse(rail.getChildAt(i).isEnabled)
                    }
                }
                await(scenario, "chosen camera route") { CameraSettings.camera(context) == expected && it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") }
                scenario.onActivity { activity ->
                    val rail = activity.findViewById<LinearLayout>(R.id.lensRail)
                    val selected = (0 until rail.childCount).map { rail.getChildAt(it) as Button }.filter { it.isSelected }
                    assertEquals(1, selected.size); assertEquals(expected, selected.single().tag)
                    assertTrue(selected.single().contentDescription.startsWith("Advertised camera route:"))
                }
                screenshot(scenario, File(directory, "lens-rail-portrait.png"))
                scenario.recreate()
                await(scenario, "restored route") { CameraSettings.camera(context) == expected && it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") }
                scenario.onActivity { it.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE }
                await(scenario, "landscape route") { it.resources.configuration.orientation == Configuration.ORIENTATION_LANDSCAPE && it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") }
                screenshot(scenario, File(directory, "lens-rail-landscape.png"))
                scenario.onActivity { activity ->
                    for (id in listOf(R.id.record, R.id.openControls, R.id.modeDetails, R.id.testMode, R.id.previewAids)) {
                        val view = activity.findViewById<Button>(id); val rect = android.graphics.Rect()
                        assertTrue(view.getGlobalVisibleRect(rect)); assertEquals("${view.text} must not be clipped", view.height, rect.height())
                    }
                }
                scenario.onActivity { it.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED }
            }
        } finally { prefs.edit().clear().also { edit -> before.forEach { (key, value) -> edit.putString(key, value as String) } }.commit() }
    }
    @Test fun packagedAdaptiveIconRendersActualAppArtwork() {
        assertTrue(context.applicationInfo.icon != 0)
        val drawable = context.packageManager.getApplicationIcon(context.applicationInfo)
        val bitmap = Bitmap.createBitmap(288, 288, Bitmap.Config.ARGB_8888)
        drawable.setBounds(0, 0, 288, 288); drawable.draw(Canvas(bitmap))
        val pixels = IntArray(288 * 288); bitmap.getPixels(pixels, 0, 288, 0, 0, 288, 288)
        assertTrue(pixels.toSet().size > 3)
        val directory = File(context.filesDir, "exports/lens-ui").apply { mkdirs() }
        File(directory, "launcher-icon.png").outputStream().use { assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)) }; bitmap.recycle()
        if (Build.VERSION.SDK_INT >= 33) {
            val monochrome = requireNotNull((drawable as AdaptiveIconDrawable).monochrome)
            val themed = Bitmap.createBitmap(288, 288, Bitmap.Config.ARGB_8888)
            monochrome.setBounds(0, 0, 288, 288); monochrome.draw(Canvas(themed))
            val themedPixels = IntArray(288 * 288); themed.getPixels(themedPixels, 0, 288, 0, 0, 288, 288)
            assertTrue(themedPixels.any { android.graphics.Color.alpha(it) > 0 })
            File(directory, "launcher-monochrome.png").outputStream().use { assertTrue(themed.compress(Bitmap.CompressFormat.PNG, 100, it)) }; themed.recycle()
        }
    }
}
