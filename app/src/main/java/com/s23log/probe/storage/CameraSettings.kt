package com.s23log.probe.storage

import android.content.Context
import com.s23log.probe.camera.CameraControls
import com.s23log.probe.core.AudioMode
import com.s23log.probe.core.BitratePreset
import org.json.JSONObject

/** Persist user settings per camera route; saved intent is revalidated against fresh capabilities. */
object CameraSettings {
    private fun prefs(context: Context) = context.getSharedPreferences("camera_settings_v1", Context.MODE_PRIVATE)
    fun audio(context: Context): AudioMode = AudioMode.fromStored(prefs(context).getString("audioMode", null))
    fun saveAudio(context: Context, mode: AudioMode) { prefs(context).edit().putString("audioMode", mode.name).apply() }
    fun bitratePreset(context: Context): BitratePreset = BitratePreset.fromStored(prefs(context).getString("bitratePreset", null))
    fun saveBitratePreset(context: Context, preset: BitratePreset) { prefs(context).edit().putString("bitratePreset", preset.name).apply() }
    fun camera(context: Context): String? = prefs(context).getString("selected", null)
    fun select(context: Context, key: String) { prefs(context).edit().putString("selected", key).apply() }
    fun mode(context: Context, key: String): String? = prefs(context).getString("mode:$key", null)
    fun saveMode(context: Context, key: String, mode: String?) { prefs(context).edit().putString("mode:$key", mode).apply() }
    fun controls(context: Context, key: String): CameraControls = runCatching {
        val json = JSONObject(prefs(context).getString("controls:$key", "{}")!!)
        CameraControls(json.optBoolean("manualExposure"), json.optInt("iso", 100), json.optLong("exposureNs", 16_666_667),
            if (json.has("focusDiopters") && !json.isNull("focusDiopters")) json.getDouble("focusDiopters").toFloat() else null,
            json.optInt("awbMode", 1), json.optBoolean("awbLock"))
    }.getOrDefault(CameraControls())
    fun saveControls(context: Context, key: String, controls: CameraControls) {
        prefs(context).edit().putString("controls:$key", JSONObject(controls.describe()).toString()).apply()
    }
}
