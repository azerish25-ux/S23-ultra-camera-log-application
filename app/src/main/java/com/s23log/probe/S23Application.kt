package com.s23log.probe

import android.app.Application
import com.s23log.probe.diagnostics.ProbeStore
import com.s23log.probe.storage.PendingMedia
import com.s23log.probe.storage.ColourReferenceStore
import java.util.concurrent.Executors
import java.util.concurrent.Future

class S23Application : Application() {
    val liveLog by lazy { com.s23log.probe.live.LiveLogSession(this) }
    val rawDevelopment by lazy { com.s23log.probe.develop.RawDevelopmentStore(this) }
    val reports: ProbeStore by lazy { ProbeStore(this) }
    val colourReferences: ColourReferenceStore by lazy { ColourReferenceStore(this) }
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
