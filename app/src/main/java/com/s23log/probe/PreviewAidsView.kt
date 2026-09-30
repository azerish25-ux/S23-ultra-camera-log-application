package com.s23log.probe

import android.content.Context
import android.graphics.*
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.SystemClock
import android.util.AttributeSet
import android.view.TextureView
import android.view.View
import com.s23log.probe.core.PreviewAid
import com.s23log.probe.core.PreviewAnalysis
import com.s23log.probe.core.PreviewAnalyzer
import com.s23log.probe.core.PreviewLevel
import java.util.Locale
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.abs

/** Foreground-only display aids. Nothing drawn here belongs to a camera/encoder output surface. */
class PreviewAidsView(context: Context, attributes: AttributeSet? = null) : View(context, attributes), SensorEventListener {
    private val prefs = context.getSharedPreferences("preview_aids_v1", Context.MODE_PRIVATE)
    private val worker = Executors.newSingleThreadExecutor()
    private val busy = AtomicBoolean()
    private val sensors = context.getSystemService(SensorManager::class.java)
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val destinationBounds = RectF()
    private val chartBounds = RectF()
    private val scale = resources.displayMetrics.density
    private val expireFrame = Runnable { invalidate() }
    private data class Frame(val result: PreviewAnalysis, val observedAt: Long, val zebra: Bitmap,
        val falseColour: Bitmap, val peaking: Bitmap, val waveform: Bitmap)
    private var frame: Frame? = null
    private var selected = prefs.getStringSet("selected", emptySet()).orEmpty().mapNotNull { value -> PreviewAid.entries.find { it.name == value } }.toSet()
    private var active = false
    private var closed = false
    @Volatile private var generation = 0
    private var lastSampleAt = -250L
    private var sampleCount = 0L
    private var level: Float? = null
    private var gravity: FloatArray? = null
    private var contentBounds: RectF? = null

    fun setContentBounds(left: Float, top: Float, right: Float, bottom: Float) {
        contentBounds = if (listOf(left, top, right, bottom).all { it.isFinite() } && right > left && bottom > top)
            RectF(left, top, right, bottom) else null
        invalidate()
    }

    fun features(): Set<PreviewAid> = selected.toSet()
    fun setFeatures(features: Set<PreviewAid>) {
        if (closed) return
        selected = features.toSet()
        prefs.edit().putStringSet("selected", selected.map { it.name }.toSet()).apply()
        clearFrame(); configureSensors(); invalidate()
        contentDescription = context.getString(R.string.preview_aids_description)
    }
    fun setActive(value: Boolean) {
        if (closed || active == value) return
        active = value; clearFrame(); configureSensors(); invalidate()
    }
    fun clearFrame() {
        generation++; frame = null
        removeCallbacks(expireFrame); invalidate()
    }
    fun close() {
        if (closed) return
        setActive(false); clearFrame(); closed = true; worker.shutdownNow()
    }
    override fun onDetachedFromWindow() { setActive(false); super.onDetachedFromWindow() }
    private fun hasPixelAids() = selected.any { it !in setOf(PreviewAid.GRID, PreviewAid.LEVEL) }

    /** Called only after TextureView reports an updated frame; at most four 160x90 reads per second. */
    fun sample(texture: TextureView) {
        val now = SystemClock.elapsedRealtime()
        if (closed || !active || !hasPixelAids() || !texture.isAvailable || now - lastSampleAt < 250 || !busy.compareAndSet(false, true)) return
        lastSampleAt = now
        val bitmap = runCatching { texture.getBitmap(160, 90) }.getOrNull()
        if (bitmap == null) { busy.set(false); return }
        val pixels = try {
            IntArray(160 * 90).also { bitmap.getPixels(it, 0, 160, 0, 0, 160, 90) }
        } catch (_: Exception) { busy.set(false); return }
        finally { bitmap.recycle() }
        val request = generation
        worker.execute {
            try {
                if (request != generation) return@execute
                val result = PreviewAnalyzer.analyze(pixels, 160, 90)
                val wavePixels = IntArray(result.waveform.size) { i ->
                    val count = result.waveform[i]
                    if (count == 0) 0 else ((64 + count * 16).coerceAtMost(255) shl 24) or 0x67dfaa
                }
                val rendered = Frame(result, now,
                    Bitmap.createBitmap(result.zebras, 160, 90, Bitmap.Config.ARGB_8888),
                    Bitmap.createBitmap(result.falseColour, 160, 90, Bitmap.Config.ARGB_8888),
                    Bitmap.createBitmap(result.peaking, 160, 90, Bitmap.Config.ARGB_8888),
                    Bitmap.createBitmap(wavePixels, 160, 64, Bitmap.Config.ARGB_8888))
                post {
                    if (!closed && active && request == generation) {
                        frame = rendered; sampleCount++; invalidate()
                        removeCallbacks(expireFrame); postDelayed(expireFrame, 800)
                    }
                }
            } catch (_: Exception) {
                post { if (request == generation) { frame = null; invalidate() } }
            } finally { busy.set(false) }
        }
    }

    fun evidence(): Map<String, Any?> = mapOf("active" to active, "sampleCount" to sampleCount,
        "sampleWidth" to frame?.result?.width, "sampleHeight" to frame?.result?.height,
        "validPixels" to frame?.result?.validPixels, "fresh" to (frame?.let { it.result.validPixels > 0 && SystemClock.elapsedRealtime() - it.observedAt <= 750 } ?: false),
        "maximumSamplesPerSecond" to 4, "input" to "TextureView_display_RGB8", "sensorExposureCalibration" to false,
        "levelAvailable" to (level != null), "features" to selected.map { it.name })

    private fun configureSensors() {
        sensors?.unregisterListener(this); gravity = null; level = null
        if (active && PreviewAid.LEVEL in selected) {
            val sensor = sensors?.getDefaultSensor(Sensor.TYPE_GRAVITY) ?: sensors?.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
            if (sensor != null) sensors?.registerListener(this, sensor, SensorManager.SENSOR_DELAY_UI)
        }
    }
    override fun onSensorChanged(event: SensorEvent) {
        if (!active || PreviewAid.LEVEL !in selected || event.values.size < 3) return
        if (event.accuracy <= SensorManager.SENSOR_STATUS_UNRELIABLE) { level = null; invalidate(); return }
        val values = event.values.copyOf(3)
        if (event.sensor.type == Sensor.TYPE_ACCELEROMETER) gravity?.let { old -> for (i in 0..2) values[i] = old[i] * 0.8f + values[i] * 0.2f }
        gravity = values
        level = PreviewLevel.degrees(values[0], values[1], values[2], display?.rotation ?: 0)
        invalidate()
    }
    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        if (accuracy <= SensorManager.SENSOR_STATUS_UNRELIABLE) { level = null; invalidate() }
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (!active || selected.isEmpty() || width == 0 || height == 0) return
        val destination = destinationBounds.apply { set(0f, 0f, width.toFloat(), height.toFloat()) }
        val framing = contentBounds ?: destination
        val current = frame?.takeIf { SystemClock.elapsedRealtime() - it.observedAt <= 750 && it.result.validPixels > 0 }
        paint.style = Paint.Style.FILL; paint.alpha = 255
        if (current != null) {
            if (PreviewAid.FALSE_COLOUR in selected) canvas.drawBitmap(current.falseColour, null, destination, paint)
            if (PreviewAid.ZEBRAS in selected) canvas.drawBitmap(current.zebra, null, destination, paint)
            if (PreviewAid.PEAKING in selected) canvas.drawBitmap(current.peaking, null, destination, paint)
        }
        if (PreviewAid.GRID in selected) {
            paint.color = 0x88ffffff.toInt(); paint.strokeWidth = scale
            for (i in 1..2) {
                val x = framing.left + framing.width() * i / 3f
                val y = framing.top + framing.height() * i / 3f
                canvas.drawLine(x, framing.top, x, framing.bottom, paint)
                canvas.drawLine(framing.left, y, framing.right, y, paint)
            }
        }
        if (PreviewAid.LEVEL in selected) {
            paint.textSize = 11 * scale; paint.strokeWidth = 2 * scale
            val value = level
            paint.color = if (value != null && abs(value) <= 1) 0xff67dfaa.toInt() else Color.WHITE
            if (value != null) {
                canvas.save(); canvas.rotate(-value, width / 2f, height / 2f)
                canvas.drawLine(width / 2f - 44 * scale, height / 2f, width / 2f + 44 * scale, height / 2f, paint); canvas.restore()
            }
            canvas.drawText(if (value == null) context.getString(R.string.preview_level_unknown) else context.getString(R.string.preview_level, String.format(Locale.US, "%.1f", value)),
                width / 2f - 44 * scale, height / 2f + 18 * scale, paint)
        }
        val bottom = (height - 52 * scale).coerceAtLeast(90 * scale)
        val chartHeight = 46 * scale
        val chartWidth = (width - 36 * scale) / 2
        fun chart(left: Float, title: String, draw: (RectF) -> Unit) {
            val rect = chartBounds.apply { set(left, bottom - chartHeight, left + chartWidth, bottom) }
            paint.color = 0xd00c1016.toInt(); canvas.drawRect(rect, paint)
            draw(rect)
            paint.color = Color.WHITE; paint.textSize = 10 * scale
            canvas.drawText(title, left + 4 * scale, rect.top - 5 * scale, paint)
        }
        if (current != null && PreviewAid.HISTOGRAM in selected) chart(12 * scale, context.getString(R.string.preview_histogram)) { rect ->
            val maximum = current.result.histogram.maxOrNull()?.coerceAtLeast(1) ?: 1
            paint.color = 0xff67dfaa.toInt()
            current.result.histogram.forEachIndexed { i, count ->
                val left = rect.left + rect.width() * i / 64
                canvas.drawRect(left, rect.bottom - rect.height() * count / maximum, left + rect.width() / 64, rect.bottom, paint)
            }
        }
        if (current != null && PreviewAid.WAVEFORM in selected) chart(width / 2f + 6 * scale, context.getString(R.string.preview_waveform)) { rect ->
            paint.color = Color.WHITE; canvas.drawBitmap(current.waveform, null, rect, paint)
        }
        paint.color = Color.WHITE; paint.textSize = 10 * scale
        canvas.drawText(context.getString(if (hasPixelAids() && current == null) R.string.preview_aids_waiting else R.string.preview_aids_scope), 12 * scale, bottom + 14 * scale, paint)
    }
}
