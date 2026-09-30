package com.s23log.probe

import android.app.Activity
import android.app.AlertDialog
import android.hardware.camera2.CameraCharacteristics as C
import android.view.View
import android.widget.*
import android.text.Editable
import android.text.TextWatcher
import com.s23log.probe.camera.CameraTarget
import com.s23log.probe.core.ControlScale
import com.s23log.probe.core.ExposureCompensation
import com.s23log.probe.core.RecordingMode
import java.util.Locale
import kotlin.math.roundToInt

/** Edits bounded draft controls. Only the existing Apply action submits a camera request. */
class QuickControls(private val activity: Activity) {
    private fun text(id: Int) = activity.findViewById<TextView>(id)
    private fun seek(id: Int) = activity.findViewById<SeekBar>(id)
    private var isoScale: ControlScale? = null
    private var shutterScale: ControlScale? = null
    private var focusMaximum = 0f
    private var fps: Int? = null
    private var compensation: ExposureCompensation? = null
    var compensationSteps: Int = 0
        private set
    init {
        listOf(R.id.isoInput, R.id.shutterInput, R.id.focusInput).forEach { id ->
            text(id).addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) = Unit
                override fun afterTextChanged(s: Editable?) { sync() }
            })
        }
        listen(R.id.isoSlider) { p -> isoScale?.let { text(R.id.isoInput).text = it.value(p).toString(); labels() } }
        listen(R.id.shutterSlider) { p -> shutterScale?.let { text(R.id.shutterInput).text = String.format(Locale.US, "%.6f", it.value(p) / 1_000_000.0); labels() } }
        listen(R.id.focusSlider) { p -> text(R.id.focusInput).text = String.format(Locale.US, "%.3f", focusMaximum * p / ControlScale.STEPS); labels() }
        listen(R.id.compensationSlider) { p -> compensation?.let { compensationSteps = it.stepsAt(p); labels() } }
        activity.findViewById<CompoundButton>(R.id.numericControls).setOnCheckedChangeListener { _, checked ->
            listOf(R.id.isoInput, R.id.shutterInput, R.id.focusInput).forEach { text(it).visibility = if (checked) View.VISIBLE else View.GONE }
            if (!checked) {
                activity.currentFocus?.clearFocus()
                activity.getSystemService(android.view.inputmethod.InputMethodManager::class.java)
                    .hideSoftInputFromWindow(activity.window.decorView.windowToken, 0)
            }
        }
        activity.findViewById<Button>(R.id.shutterAngle).setOnClickListener {
            val rate = fps ?: return@setOnClickListener
            val scale = shutterScale ?: return@setOnClickListener
            val angles = listOf(90, 180, 270, 360)
            val values = angles.map { ControlScale.shutterForAngle(it, rate) }
            val labels = angles.indices.map { i ->
                val bounded = values[i].coerceIn(scale.minimum, scale.maximum)
                String.format(Locale.US, "%d° · %.3f ms%s", angles[i], bounded / 1_000_000.0,
                    if (bounded != values[i]) activity.getString(R.string.control_limited) else "")
            }
            AlertDialog.Builder(activity).setTitle(activity.getString(R.string.shutter_angle_title, rate))
                .setItems(labels.toTypedArray()) { _, index ->
                    val value = values[index].coerceIn(scale.minimum, scale.maximum)
                    text(R.id.shutterInput).text = String.format(Locale.US, "%.6f", value / 1_000_000.0)
                    sync()
                }.setNegativeButton(R.string.cancel, null).show()
        }
    }
    private fun listen(id: Int, changed: (Int) -> Unit) {
        seek(id).max = ControlScale.STEPS
        seek(id).setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(view: SeekBar?, progress: Int, fromUser: Boolean) { if (fromUser) changed(progress) }
            override fun onStartTrackingTouch(view: SeekBar?) = Unit
            override fun onStopTrackingTouch(view: SeekBar?) = Unit
        })
    }
    fun configure(target: CameraTarget, mode: RecordingMode?) {
        compensation = target.exposureCompensation
        seek(R.id.compensationSlider).max = compensation?.positions ?: 1
        isoScale = target.characteristics[C.SENSOR_INFO_SENSITIVITY_RANGE]?.let { ControlScale(it.lower.toLong(), it.upper.toLong()) }
        fps = mode?.fps
        shutterScale = target.characteristics[C.SENSOR_INFO_EXPOSURE_TIME_RANGE]?.let {
            val maximum = mode?.fps?.let { rate -> minOf(it.upper, 1_000_000_000L / rate) } ?: it.upper
            if (maximum >= it.lower && it.lower > 0) ControlScale(it.lower, maximum) else null
        }
        focusMaximum = target.minFocus
        sync()
    }
    fun sync() {
        seek(R.id.compensationSlider).progress = compensation?.positionOf(compensationSteps) ?: 0
        isoScale?.let { scale -> text(R.id.isoInput).text.toString().toLongOrNull()?.let { seek(R.id.isoSlider).progress = scale.progress(it) } }
        shutterScale?.let { scale -> text(R.id.shutterInput).text.toString().toDoubleOrNull()?.let { seek(R.id.shutterSlider).progress = scale.progress((it * 1_000_000).toLong()) } }
        val focus = text(R.id.focusInput).text.toString().toFloatOrNull() ?: 0f
        seek(R.id.focusSlider).progress = if (focusMaximum > 0 && focus.isFinite()) (focus / focusMaximum * ControlScale.STEPS).roundToInt().coerceIn(0, ControlScale.STEPS) else 0
        labels()
    }
    private fun labels() {
        text(R.id.compensationValue).text = compensation?.let {
            activity.getString(R.string.compensation_value, String.format(Locale.US, "%+.2f", it.ev(it.bounded(compensationSteps)))) +
                if (compensationSteps != it.bounded(compensationSteps)) activity.getString(R.string.control_limited) else ""
        } ?: activity.getString(R.string.compensation_unavailable)
        text(R.id.isoValue).text = activity.getString(R.string.control_iso_value, text(R.id.isoInput).text)
        text(R.id.shutterValue).text = activity.getString(R.string.control_shutter_value, text(R.id.shutterInput).text)
        text(R.id.focusValue).text = activity.getString(R.string.control_focus_value, text(R.id.focusInput).text)
    }
    fun setCompensation(steps: Int) { compensationSteps = steps; sync() }
    fun enabled(exposure: Boolean, focus: Boolean, automatic: Boolean) {
        seek(R.id.compensationSlider).isEnabled = automatic && compensation != null
        seek(R.id.isoSlider).isEnabled = exposure && isoScale != null
        seek(R.id.shutterSlider).isEnabled = exposure && shutterScale != null
        seek(R.id.focusSlider).isEnabled = focus && focusMaximum > 0
        activity.findViewById<Button>(R.id.shutterAngle).isEnabled = exposure && shutterScale != null && fps != null
    }
}
