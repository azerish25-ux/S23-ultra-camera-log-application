package com.s23log.probe.storage

import android.content.Context
import android.os.Handler
import android.os.Looper
import com.s23log.probe.BuildConfig
import com.s23log.probe.core.ColourReferenceBundle
import com.s23log.probe.core.MediaIdentity
import com.s23log.probe.diagnostics.atomicWrite
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.Executors

/** Application-owned bounded export; completing preparation never opens a share target. */
class ColourReferenceStore(context: Context) {
    data class State(val running: Boolean = false, val files: List<File> = emptyList(), val error: String? = null)
    private val directory = File(context.applicationContext.filesDir, "exports/colour-reference-v0-1")
    private val worker = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private val observers = linkedSetOf<(State) -> Unit>()
    var state = State(); private set
    fun observe(observer: (State) -> Unit) { observers += observer; observer(state) }
    fun remove(observer: (State) -> Unit) { observers -= observer }
    private fun update(next: State) { state = next; observers.toList().forEach { it(next) } }
    fun prepare() {
        if (state.running) return
        update(State(running = true))
        worker.execute {
            val result = runCatching { writeBundle(directory) }
            main.post { update(result.fold({ State(files = it) }, { State(error = it.message ?: it.javaClass.simpleName) })) }
        }
    }
    companion object {
        internal fun writeBundle(directory: File): List<File> {
            check(directory.isDirectory || directory.mkdirs()) { "Cannot create colour-reference export folder" }
            val files = ColourReferenceBundle.files().map { (name, contents) -> File(directory, name).also { atomicWrite(it, contents) } }
            val manifest = JSONObject().put("schemaVersion", 1).put("referenceVersion", ColourReferenceBundle.VERSION)
                .put("appCommit", BuildConfig.SOURCE_REVISION).put("customLogRecordingEnabled", false)
                .put("physicalCameraCertified", false).put("lutSize", ColourReferenceBundle.SIZE).put("interpolation", "linear")
                .put("domain", JSONArray(listOf(0, 1))).put("primaries", "BT2020")
                .put("input", "normalized linear BT2020 components; inverse expects this exact reference curve")
                .put("files", JSONArray().also { array -> files.forEach { file ->
                    val identity = file.inputStream().use(MediaIdentity::read)
                    array.put(JSONObject().put("name", file.name).put("identity", JSONObject(identity.describe())))
                } })
            val manifestFile = File(directory, "manifest.json").also { atomicWrite(it, manifest.toString(2)) }
            return files + manifestFile
        }
    }
}
