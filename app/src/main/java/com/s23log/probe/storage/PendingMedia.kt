package com.s23log.probe.storage

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

/** Transactional publication: own pending MediaStore rows are removed after any failure. */
class PendingMedia private constructor(
    private val app: Context,
    val uri: Uri,
    val descriptor: ParcelFileDescriptor,
    private val privateFile: File?,
    private val journalKey: String
) {
    private var closed = false
    private var settled = false
    fun closeDescriptor() { if (!closed) { closed = true; descriptor.close() } }
    fun publish(): Uri {
        check(!settled)
        closeDescriptor()
        if (Build.VERSION.SDK_INT >= 29 && privateFile == null) {
            check(app.contentResolver.update(uri, ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) }, null, null) == 1) { "Could not publish recorded media" }
        }
        // Private outputs have no MediaStore pending flag: clear the journal before publication.
        if (privateFile != null) check(forget(app, journalKey)) { "Could not commit private output publication" }
        else forget(app, journalKey)
        settled = true
        return uri
    }
    fun abort() {
        if (settled) return
        runCatching { closeDescriptor() }
        val deleted = runCatching {
            if (privateFile != null) !privateFile.exists() || privateFile.delete()
            else app.contentResolver.delete(uri, null, null) >= 0
        }.getOrDefault(false)
        if (deleted) forget(app, journalKey)
        settled = true
    }

    companion object {
        private const val PREFS = "s23log_pending_outputs_v1"
        @Synchronized private fun remember(context: Context, key: String) {
            check(context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(key, true).commit()) { "Could not journal pending output" }
        }
        @Synchronized private fun forget(context: Context, key: String): Boolean =
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().remove(key).commit()
        fun create(context: Context, video: Boolean): PendingMedia {
            val app = context.applicationContext
            val extension = if (video) "mp4" else "dng"
            val name = "S23Log-${System.currentTimeMillis()}-${UUID.randomUUID()}.$extension"
            if (Build.VERSION.SDK_INT >= 29) {
                val collection = if (video) MediaStore.Video.Media.EXTERNAL_CONTENT_URI else MediaStore.Images.Media.EXTERNAL_CONTENT_URI
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
                    runCatching { app.contentResolver.delete(uri, null, null) }
                    forget(app, uri.toString())
                    throw e
                }
            }
            // API 26–28: no broad storage permission; retain in app storage and share by grant.
            val dir = File(app.filesDir, "exports/captures")
            check(dir.isDirectory || dir.mkdirs())
            val file = File(dir, name)
            val key = "file:${file.name}"
            var fd: ParcelFileDescriptor? = null
            try {
                remember(app, key)
                fd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_CREATE or ParcelFileDescriptor.MODE_READ_WRITE or ParcelFileDescriptor.MODE_TRUNCATE)
                val uri = FileProvider.getUriForFile(app, "${app.packageName}.files", file)
                return PendingMedia(app, uri, fd, file, key)
            } catch (e: Exception) { runCatching { fd?.close() }; file.delete(); forget(app, key); throw e }
        }

        /** Runs once per process before capture; never deletes completed or somebody else's rows. */
        fun recover(context: Context) {
            val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            prefs.all.keys.forEach { key ->
                val success = runCatching {
                    if (key.startsWith("file:")) {
                        val name = key.removePrefix("file:")
                        require(name.matches(Regex("S23Log-[0-9]+-[0-9a-f-]+\\.(mp4|dng)")))
                        val file = File(context.filesDir, "exports/captures/$name")
                        check(!file.exists() || file.delete())
                    } else if (Build.VERSION.SDK_INT >= 29) {
                        val uri = Uri.parse(key)
                        require(uri.authority == "media" && uri.scheme == "content")
                        requireNotNull(context.contentResolver.query(uri, arrayOf(MediaStore.MediaColumns.IS_PENDING, MediaStore.MediaColumns.OWNER_PACKAGE_NAME), null, null, null)) { "Cannot inspect pending output" }.use { cursor ->
                            if (cursor.moveToFirst() && cursor.getInt(0) == 1 && cursor.getString(1) == context.packageName) {
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
