package com.s23log.probe

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import java.io.File
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val executor = Executors.newSingleThreadExecutor()
    private lateinit var status: TextView
    private lateinit var reportView: TextView
    private lateinit var runButton: Button
    private lateinit var shareButton: Button
    private var latestReport: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        status = findViewById(R.id.status)
        reportView = findViewById(R.id.report)
        runButton = findViewById(R.id.runProbe)
        shareButton = findViewById(R.id.shareReport)

        runButton.setOnClickListener { ensurePermissionAndRun() }
        shareButton.setOnClickListener { shareLatestReport() }
    }

    private fun ensurePermissionAndRun() {
        if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            runProbe()
        } else {
            requestPermissions(arrayOf(Manifest.permission.CAMERA), REQUEST_CAMERA)
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CAMERA) {
            if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
                runProbe()
            } else {
                status.text = "Camera permission denied. Grant it to run the complete probe."
            }
        }
    }

    private fun runProbe() {
        runButton.isEnabled = false
        shareButton.isEnabled = false
        status.text = "Inspecting cameras, RAW paths, manual controls, dynamic range and codecs…"
        reportView.text = "Running capability probe…"

        executor.execute {
            val result = runCatching { CameraCapabilityProbe(this).run() }
            runOnUiThread {
                result.onSuccess { report ->
                    latestReport = report
                    reportView.text = report
                    status.text = "Probe complete. Report saved in app files."
                    shareButton.isEnabled = true
                    File(filesDir, "s23log-capability-report.txt").writeText(report)
                }.onFailure { error ->
                    latestReport = "Probe failed: ${error.stackTraceToString()}"
                    reportView.text = latestReport
                    status.text = "Probe failed: ${error.javaClass.simpleName}"
                    shareButton.isEnabled = true
                }
                runButton.isEnabled = true
            }
        }
    }

    private fun shareLatestReport() {
        if (latestReport.isBlank()) return
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, "S23Log camera capability report")
            putExtra(Intent.EXTRA_TEXT, latestReport)
        }
        startActivity(Intent.createChooser(send, "Share S23Log report"))
    }

    override fun onDestroy() {
        executor.shutdownNow()
        super.onDestroy()
    }

    companion object {
        private const val REQUEST_CAMERA = 1001
    }
}
