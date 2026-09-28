package com.s23log.probe.camera

import android.graphics.ImageFormat
import android.graphics.SurfaceTexture
import android.hardware.camera2.CameraCharacteristics as C
import android.hardware.camera2.CameraManager
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
data class CameraTarget(val logicalId: String, val physicalId: String?, val characteristics: C) {
    val key: String get() = "$logicalId:${physicalId ?: "logical"}"
    val front: Boolean get() = characteristics[C.LENS_FACING] == C.LENS_FACING_FRONT
    val label: String get() {
        val facing = if (front) "Front" else "Back / external"
        val focal = characteristics[C.LENS_INFO_AVAILABLE_FOCAL_LENGTHS]?.joinToString() ?: "?"
        return "$facing · $focal mm · ${physicalId?.let { "$logicalId → $it" } ?: logicalId}"
    }
    val manualSensor: Boolean get() = characteristics[C.REQUEST_AVAILABLE_CAPABILITIES]?.contains(C.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR) == true
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
                    try { result += CameraTarget(id, physical, manager.getCameraCharacteristics(physical)) }
                    catch (e: Exception) { errors += "Physical $physical via $id: ${e.message}" }
                }
            } catch (e: Exception) { errors += "Camera $id: ${e.message}" }
        }
        return CatalogResult(result.sortedWith(compareBy<CameraTarget> { it.front }.thenBy { it.physicalId != null }.thenBy { it.key }), errors)
    }

    fun previewSize(target: CameraTarget): Size {
        val sizes = target.characteristics[C.SCALER_STREAM_CONFIGURATION_MAP]?.getOutputSizes(SurfaceTexture::class.java).orEmpty()
        require(sizes.isNotEmpty()) { "No advertised preview sizes" }
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
                            if (caps.isFormatSupported(videoFormat(candidate))) candidate else null
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
