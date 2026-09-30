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
import com.s23log.probe.core.*

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
    val exposureCompensation: ExposureCompensation? get() = runCatching {
        if (!independentlySettable(R.CONTROL_AE_EXPOSURE_COMPENSATION)) return@runCatching null
        val range = characteristics[C.CONTROL_AE_COMPENSATION_RANGE] ?: return@runCatching null
        val step = characteristics[C.CONTROL_AE_COMPENSATION_STEP] ?: return@runCatching null
        ExposureCompensation(range.lower, range.upper, step.numerator, step.denominator)
    }.getOrNull()
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
data class ModePlan(val modes: List<RecordingMode>, val notes: List<String>, val rejected: List<ModeRejection> = emptyList()) {
    fun describe(): Map<String, Any?> = mapOf("candidates" to modes.map { it.describe() },
        "rejections" to rejected.map { it.describe() }, "notes" to notes,
        "scope" to "Public ordinary-session candidates; not device certification. No custom Log or high-speed sessions.")
}

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

    fun plan(target: CameraTarget, bitratePreset: BitratePreset = BitratePreset.STANDARD): ModePlan {
        val c = target.characteristics
        val map = c[C.SCALER_STREAM_CONFIGURATION_MAP] ?: return ModePlan(emptyList(), listOf("No stream map"))
        val notes = mutableListOf<String>()
        val modes = mutableListOf<RecordingMode>()
        val rejected = mutableListOf<ModeRejection>()
        val sizes = runCatching { map.getOutputSizes(MediaCodec::class.java).orEmpty().map { VideoSize(it.width, it.height) } }
            .getOrElse { notes += "Encoder output-size query failed: ${it.message}"; emptyList() }
        val logicalRanges = target.logicalCharacteristics[C.CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES].orEmpty().toSet()
        val fpsRanges = if (R.CONTROL_AE_TARGET_FPS_RANGE in target.requestKeys)
            c[C.CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES].orEmpty().filter { it in logicalRanges }.map { FpsRange(it.lower, it.upper) }
            else emptyList()
        val encoders = MediaCodecList(MediaCodecList.REGULAR_CODECS).codecInfos.filter { it.isEncoder }
            .filter { Build.VERSION.SDK_INT < 29 || !it.isAlias }
            .sortedWith(compareBy<MediaCodecInfo> { if (Build.VERSION.SDK_INT >= 29) !it.isHardwareAccelerated else false }.thenBy { it.name })
        val capabilities = mutableMapOf<Pair<String, String>, MediaCodecInfo.CodecCapabilities?>()
        for (encoder in encoders) for (mime in listOf(MediaFormat.MIMETYPE_VIDEO_AVC, MediaFormat.MIMETYPE_VIDEO_HEVC)) {
            capabilities[encoder.name to mime] = runCatching {
                if (mime in encoder.supportedTypes) encoder.getCapabilitiesForType(mime) else null
            }.getOrElse { notes += "${encoder.name}/$mime capability query failed: ${it.message}"; null }
        }
        var hlg = false
        var mixed = false
        if (Build.VERSION.SDK_INT >= 33) {
            runCatching {
                val profiles = c[C.REQUEST_AVAILABLE_DYNAMIC_RANGE_PROFILES]
                hlg = CapturePolicy.supportsHlg(c[C.REQUEST_AVAILABLE_CAPABILITIES]?.contains(C.REQUEST_AVAILABLE_CAPABILITIES_DYNAMIC_RANGE_TEN_BIT) == true, profiles?.supportedProfiles.orEmpty())
                if (hlg && profiles != null) mixed = CapturePolicy.allowsPair(
                    profiles.getProfileCaptureRequestConstraints(DynamicRangeProfiles.STANDARD),
                    profiles.getProfileCaptureRequestConstraints(DynamicRangeProfiles.HLG10),
                    DynamicRangeProfiles.STANDARD, DynamicRangeProfiles.HLG10)
            }.onFailure { hlg = false; mixed = false; notes += "HDR profile query failed: ${it.message}" }
        }
        if (hlg && !mixed) notes += "HLG10 encoder-only capture: live SDR monitoring is unavailable on this route."
        for (size in ModePlanning.sizes(sizes)) {
            val durationResult = runCatching { map.getOutputMinFrameDuration(MediaCodec::class.java, Size(size.width, size.height)) }
            val duration = durationResult.getOrNull()
            for (fps in ModePlanning.rates(fpsRanges)) for (range in DynamicRange.entries) for (mime in ModePlanning.mimes(range)) {
                fun reject(reason: String) { rejected += ModeRejection(size, fps, range, mime, reason) }
                if (size !in sizes) { reject("Size is not exposed as a public MediaCodec camera output"); continue }
                if (range == DynamicRange.HLG10 && !hlg) { reject("Camera does not expose both ten-bit capability and HLG10"); continue }
                if (duration == null) { reject("Camera timing query failed: ${durationResult.exceptionOrNull()?.javaClass?.simpleName}"); continue }
                if (!CapturePolicy.nominalRateFits(duration, fps)) { reject("Advertised camera minimum frame interval is too long"); continue }
                val timing = ModePlanning.timing(fps, fpsRanges, target.manualSensor,
                    c[C.SENSOR_INFO_MAX_FRAME_DURATION], c[C.SENSOR_INFO_EXPOSURE_TIME_RANGE]?.lower)
                if (timing == null) { reject("No matching AE rate or supported manual frame-duration path"); continue }
                val failures = mutableListOf<String>()
                var matched = false
                for (encoder in encoders) {
                    val caps = capabilities[encoder.name to mime] ?: continue
                    try {
                        require(MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface in caps.colorFormats) { "No Surface input" }
                        if (mime == MediaFormat.MIMETYPE_VIDEO_HEVC) {
                            val profile = if (range == DynamicRange.HLG10) MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10 else MediaCodecInfo.CodecProfileLevel.HEVCProfileMain
                            require(caps.profileLevels.any { it.profile == profile }) { "Required HEVC profile unavailable" }
                        }
                        val video = requireNotNull(caps.videoCapabilities) { "No video capabilities" }
                        require(video.areSizeAndRateSupported(size.width, size.height, fps.toDouble())) { "Size/rate rejected" }
                        val bitrate = (size.pixels * fps / 5).coerceIn(video.bitrateRange.lower.toLong(), video.bitrateRange.upper.toLong()).toInt()
                        val candidate = RecordingMode(size.width, size.height, fps, range, encoder.name, mime, bitrate,
                            range == DynamicRange.SDR || mixed, duration > 0, timing,
                            minimumBitRate = video.bitrateRange.lower.coerceAtLeast(1), maximumBitRate = video.bitrateRange.upper)
                            .withBitratePreset(bitratePreset)
                        require(caps.isFormatSupported(videoFormat(candidate))) { "Configured format rejected" }
                        previewSize(target, candidate)
                        modes += candidate
                        matched = true
                    } catch (e: Exception) { failures += "${encoder.name}: ${e.message ?: e.javaClass.simpleName}" }
                }
                if (!matched) reject("No compatible encoder/preview: " + failures.ifEmpty { listOf("No encoder exposes $mime") }.joinToString("; "))
            }
        }
        // A rendered HDR route is a distinct candidate, never an upgrade of a direct mode.
        val textureSizes = runCatching { map.getOutputSizes(SurfaceTexture::class.java).orEmpty().toSet() }.getOrDefault(emptySet())
        for (direct in modes.toList().filter { it.range == DynamicRange.HLG10 }) {
            val size = Size(direct.width, direct.height)
            val textureTiming = runCatching { map.getOutputMinFrameDuration(SurfaceTexture::class.java, size) }.getOrNull()
            val caps = capabilities[direct.encoder to direct.mime]
            val hdrEditing = Build.VERSION.SDK_INT >= 33 && caps?.isFeatureSupported(MediaCodecInfo.CodecCapabilities.FEATURE_HdrEditing) == true
            val hlgEditing = Build.VERSION.SDK_INT >= 35 && caps?.isFeatureSupported(MediaCodecInfo.CodecCapabilities.FEATURE_HlgEditing) == true
            var reason = ProcessingPolicy.rejection(Build.VERSION.SDK_INT, direct,
                size in textureSizes && textureTiming != null && CapturePolicy.nominalRateFits(textureTiming, direct.fps), hdrEditing, hlgEditing)
            val candidate = direct.copy(processing = ProcessingPath.GPU_HLG10, previewDuringRecording = true,
                timingAdvertised = direct.timingAdvertised && textureTiming != null && textureTiming > 0)
            if (reason == null) reason = runCatching {
                require(caps?.isFormatSupported(videoFormat(candidate)) == true) { "Rendered HLG encoder format rejected" }
            }.exceptionOrNull()?.message
            if (reason == null) modes += candidate else rejected += ModeRejection(VideoSize(direct.width,direct.height),
                direct.fps,direct.range,direct.mime,requireNotNull(reason),ProcessingPath.GPU_HLG10)
        }
        notes += "GPU HLG is experimental, at most 1080p24/30. Runtime checks require explicit YUV import, FP16, RGB10 HLG EGL and an independent monitor."
        notes += "Custom Log remains reference-only and cannot be selected for recording."
        notes += "Candidates are advertised only. Test the exact camera, codec, size, rate and colour profile on the device."
        notes += "Variable AE can slow down in low light. Manual-timing modes require confirmed manual exposure before recording."
        notes += "8K24 and 8K30 are explicit targets, not guarantees. Maximum-resolution sensor and high-speed sessions remain separate work."
        notes += "HEVC SDR is distinct from HLG10; neither is custom or Samsung Log. P010 byte-buffer support is not a Surface-input prerequisite."
        notes += "RAW DNG stills are limited to 24 MP; they are not RAW video."
        return ModePlan(modes.distinctBy { it.key }, notes.distinct(), rejected)
    }

    fun videoFormat(mode: RecordingMode): MediaFormat = MediaFormat.createVideoFormat(mode.mime, mode.width, mode.height).apply {
        if (mode.processing == ProcessingPath.GPU_HLG10) {
            require(Build.VERSION.SDK_INT >= 33)
            val caps = MediaCodecList(MediaCodecList.REGULAR_CODECS).codecInfos.first { it.name == mode.encoder }.getCapabilitiesForType(mode.mime)
            val feature = if (Build.VERSION.SDK_INT >= 35 && caps.isFeatureSupported(MediaCodecInfo.CodecCapabilities.FEATURE_HlgEditing))
                MediaCodecInfo.CodecCapabilities.FEATURE_HlgEditing else MediaCodecInfo.CodecCapabilities.FEATURE_HdrEditing
            require(caps.isFeatureSupported(feature)) { "Rendered RGB10 HLG encoding unavailable" }
            setFeatureEnabled(feature, true)
        }
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
            if (mode.mime == MediaFormat.MIMETYPE_VIDEO_HEVC) setInteger(MediaFormat.KEY_PROFILE, MediaCodecInfo.CodecProfileLevel.HEVCProfileMain)
            setInteger(MediaFormat.KEY_COLOR_STANDARD, MediaFormat.COLOR_STANDARD_BT709)
            setInteger(MediaFormat.KEY_COLOR_TRANSFER, MediaFormat.COLOR_TRANSFER_SDR_VIDEO)
            setInteger(MediaFormat.KEY_COLOR_RANGE, MediaFormat.COLOR_RANGE_LIMITED)
        }
    }
}
