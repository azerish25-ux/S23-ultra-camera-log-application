package com.s23log.probe

import android.app.Application
import com.s23log.probe.diagnostics.ProbeStore
import com.s23log.probe.storage.PendingMedia
import java.util.concurrent.Executors
import java.util.concurrent.Future

class S23Application : Application() {
    val reports: ProbeStore by lazy { ProbeStore(this) }
    private lateinit var recovery: Future<*>
    override fun onCreate() {
        super.onCreate()
        val worker = Executors.newSingleThreadExecutor()
        recovery = worker.submit { PendingMedia.recover(this) }
        worker.shutdown()
    }
    /** Called off the UI thread before camera discovery: startup recovery cannot race a new capture. */
    fun awaitMediaRecovery() { recovery.get() }
}
