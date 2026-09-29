package com.s23log.probe.camera

import android.graphics.ImageFormat
import android.graphics.SurfaceTexture
import android.hardware.camera2.CameraCharacteristics as C
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CaptureRequest as R
import android.hardware.camera2.params.DynamicRangeProfiles
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaCodecList
import android.media.MediaFormat
import android.os.Build
import android.util.Size
import com.s23log.probe.core.CapturePolicy
import com.s23log.probe.core.DynamicRange
import com.s23log.probe.core.RecordingMode
import com.s23log.probe.core.RawLimits

/** A physical-only camera is routed through its public logical device, never opened by guess. */
data class CameraTarget(val logicalId: String, val physicalId: String?, val characteristics: C, val logicalCharacteristics: C = characteristics) {
    val key: String get() = "$logicalId:${physicalId ?: "logical"}"
    val front: Boolean get() = characteristics[C.LENS_FACING] == C.LENS_FACING_FRONT
    val label: String get() {
        val facing = if (front) "Front" else "Back / external"
        val focal = characteristics[C.LENS_INFO_AVAILABLE_FOCAL_LENGTHS]?.joinToString() ?: "?"
        return "$facing · $focal mm · ${physicalId?.let { "$logicalId → $it" } ?: logicalId}"
    }
    val requestKeys: Set<R.Key<*>> get() = logicalCharacteristics.availableCaptureRequestKeys.toSet()
    val physicalKeys: Set<R.Key<*>> get() = if (physicalId != null && Build.VERSION.SDK_INT >= 28)
        logicalCharacteristics.availablePhysicalCameraRequestKeys.orEmpty().toSet() else emptySet()
    fun independentlySettable(key: R.Key<*>): Boolean = key in requestKeys && (physicalId == null || key in physicalKeys)
    val manualSensor: Boolean get() = characteristics[C.REQUEST_AVAILABLE_CAPABILITIES]?.contains(C.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR) == true &&
        listOf(R.SENSOR_SENSITIVITY, R.SENSOR_EXPOSURE_TIME, R.SENSOR_FRAME_DURATION).all(::independentlySettable)
    val manualFocus: Boolean get() = minFocus > 0 && independentlySettable(R.LENS_FOCUS_DISTANCE) &&
        characteristics[C.CONTROL_AF_AVAILABLE_MODES]?.contains(R.CONTROL_AF_MODE_OFF) == true
    val wbLockAvailable: Boolean get() = characteristics[C.CONTROL_AWB_LOCK_AVAILABLE] == true && logicalCharacteristics[C.CONTROL_AWB_LOCK_AVAILABLE] == true
    val wbModes: List<Int> get() = characteristics[C.CONTROL_AWB_AVAILABLE_MODES]?.toList().orEmpty().filter {
        it in logicalCharacteristics[C.CONTROL_AWB_AVAILABLE_MODES]?.toList().orEmpty() && it != R.CONTROL_AWB_MODE_OFF
    }
    fun request(camera: CameraDevice, template: Int): R.Builder = if (physicalId != null && Build.VERSION.SDK_INT >= 28)
        camera.createCaptureRequest(template, setOf(physicalId)) else camera.createCaptureRequest(template)
    fun <T> set(builder: R.Builder, key: R.Key<T>, value: T) {
        if (key !in requestKeys) return
        // Common logical settings govern the session. Override only explicitly advertised physical keys.
        if (physicalId != null && key in physicalKeys && Build.VERSION.SDK_INT >= 28) builder.setPhysicalCameraKey(key, value, physicalId)
        else builder.set(key, value)
    }
    val minFocus: Float get() = characteristics[C.LENS_INFO_MINIMUM_FOCUS_DISTANCE] ?: 0f
    val rawSize: Size? get() {
        if (characteristics[C.REQUEST_AVAILABLE_CAPABILITIES]?.contains(C.REQUEST_AVAILABLE_CAPABILITIES_RAW) != true) return null
        val sizes = characteristics[C.SCALER_STREAM_CONFIGURATION_MAP]?.getOutputSizes(ImageFormat.RAW_SENSOR).orEmpty()
        // Bound initial still-capture memory. This does not truncate the diagnostic export.
        return sizes.filter { RawLimits.supports(it.width, it.height) }.maxByOrNull { it.width.toLong() * it.height }
    }
}

data class CatalogResult(val targets: List<CameraTarget>, val errors: List<String>)
data class ModePlan(val modes: List<RecordingMode>, val notes: List<String>)

object CameraCatalog {
    fun discover(manager: CameraManager): CatalogResult {
        val result = mutableListOf<CameraTarget>()
        val errors = mutableListOf<String>()
        val ids = try { manager.cameraIdList.toList() } catch (e: Exception) { return CatalogResult(emptyList(), listOf(e.toString())) }
        ids.forEach { id ->
            try {
                val c = manager.getCameraCharacteristics(id)
                result += CameraTarget(id, null, c)
                if (Build.VERSION.SDK_INT >= 28) c.physicalCameraIds.sorted().filter { it !in ids }.forEach { physical ->
                    try { result += CameraTarget(id, physical, manager.getCameraCharacteristics(physical), c) }
                    catch (e: Exception) { errors += "Physical $physical via $id: ${e.message}" }
                }
            } catch (e: Exception) { errors += "Camera $id: ${e.message}" }
        }
        return CatalogResult(result.sortedWith(compareBy<CameraTarget> { it.front }.thenBy { it.physicalId != null }.thenBy { it.key }), errors)
    }

    fun previewSize(target: CameraTarget, mode: RecordingMode? = null): Size {
        val map = requireNotNull(target.characteristics[C.SCALER_STREAM_CONFIGURATION_MAP])
        val sizes = map.getOutputSizes(SurfaceTexture::class.java).orEmpty().filter { size ->
            mode == null || (size.width.toLong() * mode.height == size.height.toLong() * mode.width &&
                CapturePolicy.nominalRateFits(map.getOutputMinFrameDuration(SurfaceTexture::class.java, size), mode.fps))
        }
        require(sizes.isNotEmpty()) { "No preview with the selected mode's aspect ratio and advertised timing" }
        return sizes.firstOrNull { it.width == 1280 && it.height == 720 }
            ?: sizes.filter { it.width <= 1920 && it.height <= 1080 }.maxByOrNull { it.width.toLong() * it.height }
            ?: sizes.minBy { it.width.toLong() * it.height }
    }

    fun plan(target: CameraTarget): ModePlan {
        val c = target.characteristics
        val map = c[C.SCALER_STREAM_CONFIGURATION_MAP] ?: return ModePlan(emptyList(), listOf("No stream map"))
        val notes = mutableListOf<String>()
        val modes = mutableListOf<RecordingMode>()
        val sizes = map.getOutputSizes(MediaCodec::class.java).orEmpty().toSet()
        val fpsRanges = c[C.CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES].orEmpty()
        val encoders = MediaCodecList(MediaCodecList.REGULAR_CODECS).codecInfos.filter { it.isEncoder }
            .sortedWith(compareBy<MediaCodecInfo> { if (Build.VERSION.SDK_INT >= 29) !it.isHardwareAccelerated else false }.thenBy { it.name })
        var hlg = false
        var mixed = false
        if (Build.VERSION.SDK_INT >= 33) {
            val profiles = c[C.REQUEST_AVAILABLE_DYNAMIC_RANGE_PROFILES]
            hlg = CapturePolicy.supportsHlg(c[C.REQUEST_AVAILABLE_CAPABILITIES]?.contains(C.REQUEST_AVAILABLE_CAPABILITIES_DYNAMIC_RANGE_TEN_BIT) == true, profiles?.supportedProfiles.orEmpty())
            if (hlg && profiles != null) mixed = CapturePolicy.allowsPair(
                profiles.getProfileCaptureRequestConstraints(DynamicRangeProfiles.STANDARD),
                profiles.getProfileCaptureRequestConstraints(DynamicRangeProfiles.HLG10),
                DynamicRangeProfiles.STANDARD, DynamicRangeProfiles.HLG10)
        }
        if (!hlg) notes += "HLG10 unavailable: the selected camera does not advertise both 10-bit capability and HLG10."
        if (hlg && !mixed) notes += "HLG10 requires encoder-only capture on this camera; SDR preview is suspended while recording."
        for (range in listOf(DynamicRange.SDR, DynamicRange.HLG10)) {
            if (range == DynamicRange.HLG10 && !hlg) continue
            for (size in listOf(Size(1920, 1080), Size(1280, 720), Size(3840, 2160), Size(640, 480))) {
                for (fps in listOf(30, 24)) {
                    if (size !in sizes || fpsRanges.none { it.upper == fps }) continue
                    val durationResult = runCatching { map.getOutputMinFrameDuration(MediaCodec::class.java, size) }
                    val duration = durationResult.getOrNull()
                    if (duration == null) { notes += "Timing query failed for $size: ${durationResult.exceptionOrNull()?.message}"; continue }
                    if (!CapturePolicy.nominalRateFits(duration, fps)) continue
                    val mime = if (range == DynamicRange.SDR) MediaFormat.MIMETYPE_VIDEO_AVC else MediaFormat.MIMETYPE_VIDEO_HEVC
                    val match = encoders.firstNotNullOfOrNull { encoder ->
                        try {
                            if (mime !in encoder.supportedTypes) return@firstNotNullOfOrNull null
                            val caps = encoder.getCapabilitiesForType(mime)
                            if (MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface !in caps.colorFormats) return@firstNotNullOfOrNull null
                            if (range == DynamicRange.HLG10 && caps.profileLevels.none { it.profile == MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10 }) return@firstNotNullOfOrNull null
                            val video = caps.videoCapabilities ?: return@firstNotNullOfOrNull null
                            if (!video.areSizeAndRateSupported(size.width, size.height, fps.toDouble())) return@firstNotNullOfOrNull null
                            val bitrate = (size.width.toLong() * size.height * fps / 5).coerceIn(video.bitrateRange.lower.toLong(), video.bitrateRange.upper.toLong()).toInt()
                            val candidate = RecordingMode(size.width, size.height, fps, range, encoder.name, mime, bitrate, range == DynamicRange.SDR || mixed, duration > 0)
                            if (caps.isFormatSupported(videoFormat(candidate))) { previewSize(target, candidate); candidate } else null
                        } catch (e: Exception) {
                            notes += "${encoder.name}, $size/$fps/${range.name}: ${e.javaClass.simpleName}"
                            null
                        }
                    }
                    if (match != null) modes += match
                }
            }
        }
        if (hlg && modes.none { it.range == DynamicRange.HLG10 }) notes += "No Surface-input HEVC Main10 encoder matched the selected camera's advertised size/rate combinations."
        notes += "The initial RAW DNG path is limited to RAW_SENSOR modes up to 24 megapixels. Larger modes remain listed in Diagnostics."
        if (target.physicalId != null) notes += "Physical sensor/focus controls require logical-device override keys; unavailable overrides are disabled."
        notes += "All listed modes are advertised candidates, not device-validated recording guarantees."
        notes += "P010 byte-buffer support is deliberately not used to gate Surface-input recording."
        return ModePlan(modes.distinctBy { it.key }, notes.distinct())
    }

    fun videoFormat(mode: RecordingMode): MediaFormat = MediaFormat.createVideoFormat(mode.mime, mode.width, mode.height).apply {
        setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
        setInteger(MediaFormat.KEY_BIT_RATE, mode.bitRate)
        setInteger(MediaFormat.KEY_FRAME_RATE, mode.fps)
        setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
        if (Build.VERSION.SDK_INT >= 29) setInteger(MediaFormat.KEY_MAX_B_FRAMES, 0)
        if (mode.range == DynamicRange.HLG10) {
            setInteger(MediaFormat.KEY_PROFILE, MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10)
            setInteger(MediaFormat.KEY_COLOR_STANDARD, MediaFormat.COLOR_STANDARD_BT2020)
            setInteger(MediaFormat.KEY_COLOR_TRANSFER, MediaFormat.COLOR_TRANSFER_HLG)
            setInteger(MediaFormat.KEY_COLOR_RANGE, MediaFormat.COLOR_RANGE_LIMITED)
        } else {
            setInteger(MediaFormat.KEY_COLOR_STANDARD, MediaFormat.COLOR_STANDARD_BT709)
            setInteger(MediaFormat.KEY_COLOR_TRANSFER, MediaFormat.COLOR_TRANSFER_SDR_VIDEO)
            setInteger(MediaFormat.KEY_COLOR_RANGE, MediaFormat.COLOR_RANGE_LIMITED)
        }
    }
}
