package com.s23log.probe.diagnostics

import android.content.Context
import android.os.Handler
import android.os.Looper
import com.s23log.probe.CameraCapabilityProbe
import com.s23log.probe.core.scanAndSave
import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.util.UUID
import java.util.concurrent.Executors

/** Application-owned work survives Activity recreation; observers only live while visible. */
class ProbeStore(context: Context) {
    data class State(val running: Boolean = false, val text: String = "No report yet.", val message: String = "Ready", val shareable: Boolean = false)
    private val app = context.applicationContext
    private val worker = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private val observers = linkedSetOf<(State) -> Unit>()
    private val directory = File(app.filesDir, "exports/reports")
    private var report: ProbeReport? = null
    private var savedFiles: List<File> = emptyList()
    var state = State()
        private set

    init {
        worker.execute {
            val restored = runCatching {
                val name = File(directory, "latest").readText().trim()
                require(name.matches(Regex("report-[0-9a-f-]+")))
                val files = listOf(File(directory, "$name.json"), File(directory, "$name.txt"))
                require(files.all { it.isFile })
                files to files[1].readText()
            }.getOrNull()
            main.post {
                if (restored != null && !state.running && report == null) {
                    savedFiles = restored.first
                    update(State(text = restored.second, message = "Restored saved report", shareable = true))
                }
            }
        }
    }

    fun observe(observer: (State) -> Unit) { observers += observer; observer(state) }
    fun remove(observer: (State) -> Unit) { observers -= observer }
    private fun update(value: State) { state = value; observers.toList().forEach { it(value) } }

    fun start() {
        if (state.running) return
        update(state.copy(running = true, message = "Inspecting advertised camera and encoder capabilities…"))
        worker.execute {
            var files: List<File> = emptyList()
            val result = scanAndSave({ CameraCapabilityProbe(app).run() }) { files = persist(it) }
            main.post {
                val value = result.value
                if (value != null) {
                    report = value
                    savedFiles = files
                    update(State(text = value.text(), shareable = true, message =
                        if (result.saveError != null) "Scan retained in memory; save failed: ${result.saveError}"
                        else "Report saved. ${value.errorCount} property errors retained."))
                } else update(state.copy(running = false, message = "Scan failed: ${result.scanError}"))
            }
        }
    }

    fun export(callback: (Result<List<File>>) -> Unit) {
        val current = report
        val existing = savedFiles
        worker.execute {
            val result = runCatching {
                if (existing.isNotEmpty() && existing.all { it.isFile }) existing
                else persist(requireNotNull(current) { "No report is available" })
            }
            main.post { result.getOrNull()?.let { savedFiles = it }; callback(result) }
        }
    }

    private fun persist(value: ProbeReport): List<File> {
        check(directory.isDirectory || directory.mkdirs()) { "Cannot create reports directory" }
        val name = "report-${UUID.randomUUID()}"
        val json = File(directory, "$name.json")
        val text = File(directory, "$name.txt")
        try {
            atomicWrite(json, value.json())
            atomicWrite(text, value.text())
            atomicWrite(File(directory, "latest"), name)
            return listOf(json, text)
        } catch (e: Exception) { json.delete(); text.delete(); throw e }
    }
}

fun atomicWrite(file: File, text: String) {
    val temp = File(file.parentFile, ".${file.name}.${UUID.randomUUID()}.tmp")
    try {
        temp.outputStream().use { out -> out.write(text.toByteArray(Charsets.UTF_8)); out.fd.sync() }
        Files.move(temp.toPath(), file.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
    } finally { temp.delete() }
}
