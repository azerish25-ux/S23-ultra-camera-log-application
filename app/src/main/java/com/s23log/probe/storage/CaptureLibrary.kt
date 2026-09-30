package com.s23log.probe.storage

import android.content.Context
import android.net.Uri
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest

/** Private, append-per-capture index. Media and validation evidence keep their existing owners. */
object CaptureLibrary {
    data class Entry(val id: String, val createdAt: Long, val uris: List<Uri>, val report: File?,
        val message: String, val mimeType: String)
    data class Snapshot(val entries: List<Entry>, val unreadableRecords: Int)

    private val reportName = Regex("(recording|raw)-[0-9a-f-]+\\.json")
    private val recordName = Regex("[0-9a-f]{64}\\.json")
    private fun directory(context: Context) = File(context.filesDir, "capture-library")
    private fun allowed(context: Context, uri: Uri): Boolean = uri.scheme == "content" &&
        (uri.authority == "media" || uri.authority == "${context.packageName}.files")

    @Synchronized fun remember(context: Context, uris: List<Uri>, report: File?, message: String) {
        if (uris.isEmpty()) return // Rejected attempts remain in latest-result/recovery UI, not saved media.
        require(uris.all { allowed(context, it) }) { "Capture URI is outside app media storage" }
        val reportBase = report?.name?.takeIf { reportName.matches(it) }
        val identity = reportBase ?: uris.joinToString("\n")
        val id = MessageDigest.getInstance("SHA-256").digest(identity.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
        val dir = directory(context)
        check(dir.isDirectory || dir.mkdirs()) { "Capture library is unavailable" }
        val file = File(dir, "$id.json")
        if (file.exists()) return // Repeated completion/recreation does not reorder or duplicate a capture.
        val providerMime = runCatching { context.contentResolver.getType(uris.first()) }.getOrNull()
        val mime = when {
            reportBase?.startsWith("raw-") == true || providerMime == "image/x-adobe-dng" -> "image/x-adobe-dng"
            reportBase?.startsWith("recording-") == true || providerMime?.startsWith("video/") == true -> "video/mp4"
            else -> "application/octet-stream"
        }
        val json = JSONObject().put("schema", 1).put("id", id).put("createdAt", System.currentTimeMillis())
            .put("uris", JSONArray(uris.map(Uri::toString))).put("report", reportBase ?: JSONObject.NULL)
            .put("message", message).put("mimeType", mime)
        val atomic = AtomicFile(file)
        val stream = atomic.startWrite()
        try { stream.write(json.toString().toByteArray(Charsets.UTF_8)); atomic.finishWrite(stream) }
        catch (e: Exception) { atomic.failWrite(stream); throw e }
    }

    @Synchronized fun read(context: Context): Snapshot {
        var unreadable = 0
        val entries = directory(context).listFiles().orEmpty().filter { recordName.matches(it.name) }.mapNotNull { file ->
            try {
                val json = AtomicFile(file).openRead().use { input ->
                    val bytes = ByteArray(128 * 1024 + 1)
                    var count = 0
                    while (count < bytes.size) {
                        val read = input.read(bytes, count, bytes.size - count)
                        if (read < 0) break
                        count += read
                    }
                    require(count <= 128 * 1024) { "Oversized capture record" }
                    JSONObject(String(bytes, 0, count, Charsets.UTF_8))
                }
                require(json.getInt("schema") == 1 && json.getString("id") == file.name.removeSuffix(".json"))
                val timestamp = json.getLong("createdAt"); require(timestamp >= 0)
                val array = json.getJSONArray("uris"); require(array.length() in 1..100)
                val uris = (0 until array.length()).map { Uri.parse(array.getString(it)) }
                require(uris.all { allowed(context, it) })
                val reportBase = if (json.isNull("report")) null else json.getString("report").also { require(reportName.matches(it)) }
                val report = reportBase?.let { File(context.filesDir, "exports/validation/$it").takeIf(File::isFile) }
                val mime = json.getString("mimeType"); require(mime in setOf("video/mp4", "image/x-adobe-dng", "application/octet-stream"))
                Entry(json.getString("id"), timestamp, uris, report, json.getString("message"), mime)
            } catch (_: Exception) { unreadable++; null }
        }.sortedWith(compareByDescending<Entry> { it.createdAt }.thenBy { it.id })
        return Snapshot(entries, unreadable)
    }

    fun accessible(context: Context, uri: Uri): Boolean = allowed(context, uri) && runCatching {
        context.contentResolver.openFileDescriptor(uri, "r")?.use { true } ?: false
    }.getOrDefault(false)
}
