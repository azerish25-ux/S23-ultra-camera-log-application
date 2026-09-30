package com.s23log.probe.storage

import com.s23log.probe.core.JournalCleanup
import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.ParcelFileDescriptor
import android.provider.MediaStore
import androidx.core.content.FileProvider
import java.io.File
import java.util.UUID

/** Video is staged privately; a verified gallery copy is committed before removing the original. */
class PendingMedia private constructor(
    private val app: Context,
    val uri: Uri,
    val descriptor: ParcelFileDescriptor,
    private val privateFile: File?,
    private val journalKey: String,
    private val stagedVideo: Boolean = false
) {
    private var closed = false
    private var settled = false
    fun stagedByteCount(): Long = if (stagedVideo) privateFile?.length()?.coerceAtLeast(0) ?: 0 else 0
    fun closeDescriptor() { if (!closed) { descriptor.close(); closed = true } }

    fun publish(): Uri {
        check(!settled)
        closeDescriptor()
        if (stagedVideo) {
            val file = requireNotNull(privateFile)
            val published: Uri
            if (Build.VERSION.SDK_INT >= 29) {
                val copy = createMediaStore(app, video = true)
                try {
                    // dup keeps ownership of the destination descriptor in PendingMedia.
                    ParcelFileDescriptor.AutoCloseOutputStream(ParcelFileDescriptor.dup(copy.descriptor.fileDescriptor)).use { sink ->
                        file.inputStream().use { source -> source.copyTo(sink) }
                        sink.flush()
                    }
                    copy.descriptor.fileDescriptor.sync()
                    published = copy.publish()
                } catch (e: Exception) {
                    runCatching { copy.abort() } // failed cleanup stays journaled for the next launch
                    throw e // the private original has never been touched
                }
                settled = true // a completed gallery copy must never be rolled back by cleanup
                runCatching {
                    if (file.delete()) forget(app, journalKey)
                    else markRetained(app, journalKey, "A published copy exists; this staging copy could not be removed")
                }
            } else {
                val directory = File(app.filesDir, "exports/captures")
                check(directory.isDirectory || directory.mkdirs())
                val completedFile = File(directory, file.name)
                published = fileUri(app, completedFile)
                check(!completedFile.exists() && file.renameTo(completedFile)) { "Could not move video into completed captures" }
                settled = true
                runCatching { forget(app, journalKey) }
            }
            return published
        }
        if (Build.VERSION.SDK_INT >= 29 && privateFile == null) {
            check(app.contentResolver.update(uri, ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) }, null, null) == 1) {
                "Could not publish recorded media"
            }
        }
        settled = true
        runCatching { forget(app, journalKey) }
        return uri
    }

    /** Keep nonempty video, including unverified/incomplete MP4s, out of the public gallery. */
    fun retain(reason: String): Uri {
        check(stagedVideo) { "Only staged video can be retained" }
        runCatching { closeDescriptor() }
        check(privateFile?.isFile == true && privateFile.length() > 0) { "Staged video is missing or empty" }
        markRetained(app, journalKey, reason)
        settled = true
        return uri
    }

    fun abort() {
        if (settled) return
        runCatching { closeDescriptor() }
        // Called for zero-sample videos or failed stills, never as a sidecar-error rollback.
        JournalCleanup.run(
            delete = { if (privateFile != null) !privateFile.exists() || privateFile.delete() else app.contentResolver.delete(uri, null, null) >= 0 },
            forget = { forget(app, journalKey) }
        )
        settled = true
    }

    companion object {
        private const val PREFS = "s23log_pending_outputs_v1"
        private const val RETAINED = "retained:"
        private val filePattern = Regex("S23Log-[0-9]+-[0-9a-f-]+\\.(mp4|dng)")
        private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        @Synchronized private fun remember(context: Context, key: String) {
            check(prefs(context).edit().putBoolean(key, true).commit()) { "Could not journal pending output" }
        }
        @Synchronized private fun forget(context: Context, key: String): Boolean =
            prefs(context).edit().remove(key).commit()
        private fun markRetained(context: Context, key: String, reason: String) {
            // Directory discovery at the next cold launch also recovers this file if preferences fail.
            prefs(context).edit().putString(key, RETAINED + reason.take(1000)).commit()
        }
        private fun fileUri(context: Context, file: File): Uri =
            FileProvider.getUriForFile(context, "${context.packageName}.files", file)

        fun create(context: Context, video: Boolean): PendingMedia {
            val app = context.applicationContext
            if (!video && Build.VERSION.SDK_INT >= 29) return createMediaStore(app, false)
            val extension = if (video) "mp4" else "dng"
            val name = "S23Log-${System.currentTimeMillis()}-${UUID.randomUUID()}.$extension"
            val dir = File(app.filesDir, if (video) "exports/recovery" else "exports/captures")
            check(dir.isDirectory || dir.mkdirs())
            val file = File(dir, name)
            val key = "${if (video) "video" else "file"}:${file.name}"
            var fd: ParcelFileDescriptor? = null
            try {
                remember(app, key)
                fd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_CREATE or ParcelFileDescriptor.MODE_READ_WRITE or ParcelFileDescriptor.MODE_TRUNCATE)
                return PendingMedia(app, fileUri(app, file), fd, file, key, video)
            } catch (e: Exception) {
                runCatching { fd?.close() }
                if (!file.exists() || file.delete()) forget(app, key)
                throw e
            }
        }

        @android.annotation.TargetApi(29)
        private fun createMediaStore(app: Context, video: Boolean): PendingMedia {
            val collection = if (video) MediaStore.Video.Media.EXTERNAL_CONTENT_URI else MediaStore.Images.Media.EXTERNAL_CONTENT_URI
            val name = "S23Log-${System.currentTimeMillis()}-${UUID.randomUUID()}.${if (video) "mp4" else "dng"}"
            val values = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, name)
                put(MediaStore.MediaColumns.MIME_TYPE, if (video) "video/mp4" else "image/x-adobe-dng")
                put(MediaStore.MediaColumns.RELATIVE_PATH, "${if (video) Environment.DIRECTORY_MOVIES else Environment.DIRECTORY_PICTURES}/S23Log")
                put(MediaStore.MediaColumns.IS_PENDING, 1)
            }
            val uri = requireNotNull(app.contentResolver.insert(collection, values)) { "MediaStore refused the output" }
            try {
                remember(app, uri.toString())
                val fd = requireNotNull(app.contentResolver.openFileDescriptor(uri, "rw")) { "Could not open output" }
                return PendingMedia(app, uri, fd, null, uri.toString())
            } catch (e: Exception) {
                val cleaned = JournalCleanup.run(
                    delete = { app.contentResolver.delete(uri, null, null) >= 0 }, forget = { forget(app, uri.toString()) })
                // Preserve a cleanup record even if the initial journal write failed.
                if (!cleaned) runCatching { remember(app, uri.toString()) }
                throw e
            }
        }

        data class Recovery(val file: File, val uri: Uri, val reason: String, internal val key: String)
        fun recoverable(context: Context): List<Recovery> = prefs(context).all.mapNotNull { (key, value) ->
            if (value !is String || !value.startsWith(RETAINED)) return@mapNotNull null
            val prefix = when { key.startsWith("video:") -> "video:"; key.startsWith("file:") -> "file:"; else -> return@mapNotNull null }
            val name = key.removePrefix(prefix)
            if (!name.matches(filePattern) || !name.endsWith(".mp4")) return@mapNotNull null
            val file = File(context.filesDir, "exports/${if (prefix == "video:") "recovery" else "captures"}/$name")
            if (!file.isFile || file.length() == 0L) return@mapNotNull null
            Recovery(file, fileUri(context, file), value.removePrefix(RETAINED), key)
        }.sortedByDescending { it.file.lastModified() }

        /** Only used after an explicit user confirmation; never deletes a completed gallery copy. */
        fun discardRecovery(context: Context, entry: Recovery) {
            val current = recoverable(context).firstOrNull { it.key == entry.key } ?: return
            check(current.file.delete()) { "Could not delete recovery file" }
            forget(context, current.key)
        }

        /** Runs once on cold start. Nonempty videos survive; unfinished stills/owned pending copies are cleaned. */
        fun recover(context: Context) {
            // Recover unjournaled files too (process death or failed preferences flush).
            File(context.filesDir, "exports/recovery").listFiles().orEmpty()
                .filter { it.isFile && it.name.matches(filePattern) && it.name.endsWith(".mp4") }
                .forEach { file ->
                    if (file.length() > 0 && prefs(context).all["video:${file.name}"] !is String)
                        markRetained(context, "video:${file.name}", "Interrupted capture; completeness and format are unverified")
                }
            prefs(context).all.keys.forEach { key ->
                val success = runCatching {
                    if (key.startsWith("file:") || key.startsWith("video:")) {
                        val name = key.substringAfter(':')
                        require(name.matches(filePattern))
                        val file = File(context.filesDir, "exports/${if (key.startsWith("video:")) "recovery" else "captures"}/$name")
                        if (name.endsWith(".mp4") && file.isFile && file.length() > 0) {
                            if (prefs(context).all[key] !is String) markRetained(context, key, "Interrupted capture; not verified")
                            return@forEach
                        }
                        check(!file.exists() || file.delete())
                    } else if (Build.VERSION.SDK_INT >= 29) {
                        val uri = Uri.parse(key)
                        require(uri.authority == "media" && uri.scheme == "content")
                        requireNotNull(context.contentResolver.query(uri, arrayOf(MediaStore.MediaColumns.IS_PENDING, MediaStore.MediaColumns.OWNER_PACKAGE_NAME), null, null, null)).use { cursor ->
                            if (cursor.moveToFirst() && cursor.getInt(0) == 1 && cursor.getString(1) == context.packageName) {
                                // Legacy pending video may be the only copy: preserve before cleanup.
                                if (uri.pathSegments.contains("video")) {
                                    val dir = File(context.filesDir, "exports/recovery")
                                    check(dir.isDirectory || dir.mkdirs())
                                    val file = File(dir, "S23Log-${System.currentTimeMillis()}-${UUID.randomUUID()}.mp4")
                                    try {
                                        requireNotNull(context.contentResolver.openInputStream(uri)).use { input ->
                                            java.io.FileOutputStream(file).use { output -> input.copyTo(output); output.fd.sync() }
                                        }
                                        if (file.length() > 0) markRetained(context, "video:${file.name}", "Recovered pending video; unverified; may duplicate a published copy")
                                        else file.delete()
                                    } catch (e: Exception) { file.delete(); throw e }
                                }
                                check(context.contentResolver.delete(uri, null, null) == 1)
                            }
                        }
                    }
                }.isSuccess
                if (success) forget(context, key)
            }
        }
    }
}
