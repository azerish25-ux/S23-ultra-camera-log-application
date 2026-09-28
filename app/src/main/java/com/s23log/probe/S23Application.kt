package com.s23log.probe

import android.app.Application
import com.s23log.probe.diagnostics.ProbeStore
import com.s23log.probe.storage.PendingMedia

class S23Application : Application() {
    val reports: ProbeStore by lazy { ProbeStore(this) }
    override fun onCreate() {
        super.onCreate()
        PendingMedia.recover(this)
    }
}
