package com.s23log.probe

import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.Intent
import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import android.media.MediaFormat
import android.net.Uri
import android.os.Bundle
import android.os.Build
import android.util.LruCache
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.core.content.FileProvider
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import com.s23log.probe.storage.CaptureHistory
import com.s23log.probe.storage.CaptureLibrary
import com.s23log.probe.storage.CapturePairing
import com.s23log.probe.core.MediaIdentity
import com.s23log.probe.storage.ClipDetails
import org.json.JSONObject
import java.text.DateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors

/** App-owned media only. Selected URI grants never require broad storage permission. */
class CaptureLibraryActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    private lateinit var list: ListView
    private lateinit var status: TextView
    private var entries = emptyList<CaptureLibrary.Entry>()
    private var detailsById = emptyMap<String, ClipDetails>()
    private val thumbnails = object : LruCache<String, Bitmap>(4 * 1024 * 1024) {
        override fun sizeOf(key: String, value: Bitmap) = value.byteCount
    }
    private val pendingThumbnails = mutableSetOf<String>()
    private val missingThumbnails = mutableSetOf<String>()
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
            dividerHeight = (8 * resources.displayMetrics.density).toInt()
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
            val detailMap = mutableMapOf<String, ClipDetails>()
            val snapshot = runCatching {
                CaptureLibrary.read(this).also { result -> result.entries.forEach { entry ->
                    val report = runCatching {
                        entry.report?.takeIf { it.isFile && it.length() in 1..(4 * 1024 * 1024) }?.let { JSONObject(it.readText()) }
                    }.getOrNull()
                    detailMap[entry.id] = ClipDetails.from(report)
                } }
            }
            runOnUiThread {
                if (isDestroyed || isFinishing || request != generation) return@runOnUiThread
                snapshot.onSuccess { result ->
                    val scroll = list.onSaveInstanceState()
                    entries = result.entries
                    detailsById = detailMap.toMap()
                    val dates = DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT)
                    list.adapter = object : BaseAdapter() {
                        override fun getCount() = entries.size
                        override fun getItem(position: Int) = entries[position]
                        override fun getItemId(position: Int) = position.toLong()
                        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
                            val row = convertView ?: layoutInflater.inflate(R.layout.capture_library_row, parent, false)
                            val entry = getItem(position)
                            val measured = detailsById[entry.id] ?: ClipDetails.from(null)
                            val kind = getString(when (entry.mimeType) { "video/mp4" -> R.string.library_video; "image/x-adobe-dng" -> R.string.library_raw; else -> R.string.library_capture })
                            row.findViewById<TextView>(R.id.libraryRowTitle).text = "${getString(R.string.library_added, dates.format(Date(entry.createdAt)))} · $kind"
                            row.findViewById<TextView>(R.id.libraryRowMetadata).text = metadata(measured)
                            row.findViewById<TextView>(R.id.libraryRowStatus).text = when {
                                measured.status == "recoverable" -> getString(R.string.library_recovery_status)
                                measured.status != "checked" -> getString(R.string.library_unknown_status)
                                measured.cadence == "within_tolerance" -> getString(R.string.library_checked_status)
                                measured.cadence == "warning" -> getString(R.string.library_cadence_warning)
                                else -> getString(R.string.library_cadence_unknown)
                            }
                            thumbnail(row.findViewById(R.id.libraryThumbnail), entry)
                            return row
                        }
                    }
                    list.onRestoreInstanceState(scroll)
                    status.text = if (entries.isEmpty()) getString(R.string.library_empty) else getString(R.string.library_scope, entries.size)
                    if (result.unreadableRecords > 0 || migrated.isFailure) status.append("\n" + getString(R.string.library_index_warning))
                }.onFailure { status.setText(R.string.library_load_failed) }
            }
        }
    }

    override fun onPause() { generation++; pendingThumbnails.clear(); super.onPause() }
    override fun onDestroy() { worker.shutdown(); thumbnails.evictAll(); super.onDestroy() }

    private fun metadata(details: ClipDetails): String {
        val dimensions = if (details.width != null && details.height != null) "${details.width} × ${details.height}" else getString(R.string.library_dimensions_unknown)
        val codec = when (details.mime) { "video/avc" -> "AVC"; "video/hevc" -> "HEVC"; else -> getString(R.string.library_codec_unknown) }
        val transfer = details.logLabel ?: when (details.transfer) {
            MediaFormat.COLOR_TRANSFER_LINEAR -> "Linear"
            MediaFormat.COLOR_TRANSFER_SDR_VIDEO -> "SDR"
            MediaFormat.COLOR_TRANSFER_ST2084 -> "PQ"
            MediaFormat.COLOR_TRANSFER_HLG -> "HLG"
            else -> getString(R.string.library_colour_unknown)
        }
        val measured = details.measuredFps?.let { getString(R.string.library_measured_fps, String.format(Locale.US, "%.2f", it)) } ?: getString(R.string.library_rate_unknown)
        val target = details.targetFps?.let { getString(R.string.library_target_fps, it) }.orEmpty()
        val depth = details.lumaBitDepth?.let { getString(R.string.library_bit_depth, it) } ?: getString(R.string.library_depth_unknown)
        return "$dimensions · $codec · $transfer\n$measured $target\n$depth"
    }

    private fun thumbnail(view: ImageView, entry: CaptureLibrary.Entry) {
        view.tag = entry.id
        val cached = thumbnails.get(entry.id)
        if (cached != null) {
            view.scaleType = ImageView.ScaleType.CENTER_CROP
            view.clearColorFilter(); view.setImageBitmap(cached); view.setContentDescription(getString(R.string.library_thumbnail)); return
        }
        view.scaleType = ImageView.ScaleType.CENTER
        view.setImageResource(if (entry.mimeType == "video/mp4") R.drawable.ic_clip_video else android.R.drawable.ic_menu_gallery)
        view.setColorFilter(0xffb6c5db.toInt())
        view.contentDescription = getString(R.string.library_thumbnail_pending)
        if (entry.id in missingThumbnails || !pendingThumbnails.add(entry.id)) return
        val request = generation
        worker.execute {
            if (request != generation) return@execute
            val bitmap = runCatching {
                if (Build.VERSION.SDK_INT < 27 || entry.mimeType != "video/mp4") return@runCatching null
                val retriever = MediaMetadataRetriever()
                try {
                    retriever.setDataSource(this, entry.uris.first())
                    retriever.getScaledFrameAtTime(0, MediaMetadataRetriever.OPTION_CLOSEST_SYNC, 256, 144)
                } finally { retriever.release() }
            }.getOrNull()
            runOnUiThread {
                if (isDestroyed || isFinishing || request != generation) { bitmap?.recycle(); return@runOnUiThread }
                pendingThumbnails.remove(entry.id)
                if (bitmap != null) thumbnails.put(entry.id, bitmap) else missingThumbnails.add(entry.id)
                if (view.tag == entry.id) {
                    if (bitmap != null) { view.scaleType = ImageView.ScaleType.CENTER_CROP; view.clearColorFilter(); view.setImageBitmap(bitmap) }
                    view.contentDescription = getString(if (bitmap != null) R.string.library_thumbnail else R.string.library_thumbnail_unavailable)
                }
            }
        }
    }

    private fun details(entry: CaptureLibrary.Entry) {
        val items = arrayOf(getString(R.string.library_open), getString(R.string.library_share), getString(R.string.share_validation), getString(R.string.library_share_pair), getString(R.string.library_details))
        AlertDialog.Builder(this).setTitle(R.string.library_actions).setItems(items) { _, choice ->
            if (choice == 4) {
                val text = TextView(this).apply { text = entry.message; setTextIsSelectable(true); setPadding(24, 16, 24, 16) }
                AlertDialog.Builder(this).setTitle(R.string.library_details).setView(ScrollView(this).apply { addView(text) })
                    .setPositiveButton(R.string.close, null).show()
            } else if (choice == 3) {
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
