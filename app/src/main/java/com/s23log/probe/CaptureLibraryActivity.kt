package com.s23log.probe

import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.core.content.FileProvider
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import com.s23log.probe.storage.CaptureHistory
import com.s23log.probe.storage.CaptureLibrary
import com.s23log.probe.core.CapturePairing
import com.s23log.probe.core.MediaIdentity
import org.json.JSONObject
import java.text.DateFormat
import java.util.Date
import java.util.concurrent.Executors

/** App-owned media only. Selected URI grants never require broad storage permission. */
class CaptureLibraryActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    private lateinit var list: ListView
    private lateinit var status: TextView
    private var entries = emptyList<CaptureLibrary.Entry>()
    @Volatile private var generation = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setBackgroundColor(0xff0c1016.toInt()) }
        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout())
            val pad = (16 * resources.displayMetrics.density).toInt()
            view.setPadding(pad + bars.left, pad + bars.top, pad + bars.right, pad + bars.bottom); insets
        }
        root.addView(Button(this).apply { setText(R.string.library_back); setOnClickListener { finish() } })
        root.addView(TextView(this).apply { setText(R.string.capture_library); textSize = 24f; setTextColor(0xfff4f6fa.toInt()) })
        status = TextView(this).apply { id = R.id.captureLibraryStatus; setText(R.string.library_loading); accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE }
        root.addView(status)
        list = ListView(this).apply {
            id = R.id.captureLibraryList
            setOnItemClickListener { _, _, position, _ -> entries.getOrNull(position)?.let(::details) }
        }
        root.addView(list, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
    }

    override fun onResume() {
        super.onResume()
        val request = ++generation
        worker.execute {
            val latest = CaptureHistory.latest(this)
            val migrated = runCatching { CaptureLibrary.remember(this, latest.uris, latest.report, latest.message) }
            val snapshot = runCatching { CaptureLibrary.read(this) }
            runOnUiThread {
                if (isDestroyed || isFinishing || request != generation) return@runOnUiThread
                snapshot.onSuccess { result ->
                    val scroll = list.onSaveInstanceState()
                    entries = result.entries
                    val dates = DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT)
                    list.adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, entries.map {
                        "${getString(R.string.library_added, dates.format(Date(it.createdAt)))} · ${if (it.mimeType == "video/mp4") getString(R.string.library_video) else getString(R.string.library_raw)}\n${it.message}"
                    })
                    list.onRestoreInstanceState(scroll)
                    status.text = if (entries.isEmpty()) getString(R.string.library_empty) else getString(R.string.library_scope, entries.size)
                    if (result.unreadableRecords > 0 || migrated.isFailure) status.append("\n" + getString(R.string.library_index_warning))
                }.onFailure { status.setText(R.string.library_load_failed) }
            }
        }
    }

    override fun onPause() { generation++; super.onPause() }
    override fun onDestroy() { worker.shutdown(); super.onDestroy() }

    private fun details(entry: CaptureLibrary.Entry) {
        val items = arrayOf(getString(R.string.library_open), getString(R.string.library_share), getString(R.string.share_validation), getString(R.string.library_share_pair))
        AlertDialog.Builder(this).setTitle(R.string.library_actions).setItems(items) { _, choice ->
            if (choice == 3) {
                sharePair(entry)
            } else if (choice == 2) {
                val file = entry.report
                if (file == null || !file.isFile) { notice(R.string.library_report_missing); return@setItems }
                val uri = FileProvider.getUriForFile(this, "$packageName.files", file)
                launch(Intent(Intent.ACTION_SEND).setType("application/json").putExtra(Intent.EXTRA_STREAM, uri), listOf(uri), true)
            } else if (entry.uris.size > 1 && choice == 0) {
                AlertDialog.Builder(this).setTitle(R.string.library_choose_file)
                    .setItems(entry.uris.indices.map { getString(R.string.library_file_number, it + 1) }.toTypedArray()) { _, index ->
                        open(entry, listOf(entry.uris[index]), false)
                    }.setNegativeButton(android.R.string.cancel, null).show()
            } else open(entry, entry.uris, choice == 1)
        }.setNegativeButton(R.string.close, null).show()
    }

    private fun sharePair(entry: CaptureLibrary.Entry) {
        val request = generation
        status.setText(R.string.library_checking_pair)
        worker.execute {
            val pair = runCatching {
                require(entry.uris.size == 1 && entry.mimeType == "video/mp4")
                val report = requireNotNull(entry.report)
                require(report.isFile && report.length() in 1..(4 * 1024 * 1024))
                val data = JSONObject(report.readText())
                val actual = requireNotNull(contentResolver.openInputStream(entry.uris.single())).use { input ->
                    MediaIdentity.read(input) { request == generation }
                }
                require(CapturePairing.matches(data, actual))
                listOf(entry.uris.single(), FileProvider.getUriForFile(this, "$packageName.files", report))
            }
            runOnUiThread {
                if (isDestroyed || isFinishing || request != generation) return@runOnUiThread
                status.setText(if (pair.isSuccess) R.string.library_pair_checked else R.string.library_pair_unavailable)
                pair.onSuccess { uris ->
                    val intent = Intent(Intent.ACTION_SEND_MULTIPLE).setType("*/*")
                        .putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(uris))
                    launch(intent, uris, true)
                }.onFailure { notice(R.string.library_pair_unavailable) }
            }
        }
    }

    private fun open(entry: CaptureLibrary.Entry, uris: List<Uri>, share: Boolean) {
        val request = generation
        worker.execute {
            val available = uris.all { CaptureLibrary.accessible(this, it) }
            runOnUiThread {
                if (isDestroyed || isFinishing || request != generation) return@runOnUiThread
                if (!available) { notice(R.string.library_media_missing); return@runOnUiThread }
                val intent = when {
                    !share -> Intent(Intent.ACTION_VIEW).setDataAndType(uris.first(), entry.mimeType)
                    uris.size == 1 -> Intent(Intent.ACTION_SEND).setType(entry.mimeType).putExtra(Intent.EXTRA_STREAM, uris.first())
                    else -> Intent(Intent.ACTION_SEND_MULTIPLE).setType(entry.mimeType).putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(uris))
                }
                launch(intent, uris, share)
            }
        }
    }

    private fun launch(intent: Intent, uris: List<Uri>, chooser: Boolean) {
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        intent.clipData = ClipData.newRawUri("S23Log capture", uris.first()).apply { uris.drop(1).forEach { addItem(ClipData.Item(it)) } }
        runCatching { startActivity(if (chooser) Intent.createChooser(intent, getString(R.string.library_share)) else intent) }
            .onFailure { notice(R.string.library_no_viewer) }
    }
    private fun notice(message: Int) { Toast.makeText(this, message, Toast.LENGTH_LONG).show() }
}
