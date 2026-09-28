package com.s23log.probe.storage

import android.content.Context
import android.net.Uri
import org.json.JSONArray
import java.io.File

object CaptureHistory {
    data class Entry(val uris: List<Uri>, val report: File?, val message: String)
    fun save(context: Context, uris: List<Uri>, report: File?, message: String) {
        context.getSharedPreferences("capture_history", Context.MODE_PRIVATE).edit()
            .putString("uris", JSONArray(uris.map { it.toString() }).toString())
            .putString("report", report?.name).putString("message", message).commit()
    }
    fun latest(context: Context): Entry {
        val prefs = context.getSharedPreferences("capture_history", Context.MODE_PRIVATE)
        val uris = runCatching {
            val array = JSONArray(prefs.getString("uris", "[]"))
            (0 until array.length()).map { Uri.parse(array.getString(it)) }
        }.getOrDefault(emptyList())
        val name = prefs.getString("report", null)
        val file = if (name != null && name.matches(Regex("(recording|raw)-[0-9a-f-]+\\.json")))
            File(context.filesDir, "exports/validation/$name").takeIf { it.isFile } else null
        return Entry(uris, file, prefs.getString("message", "") ?: "")
    }
}
