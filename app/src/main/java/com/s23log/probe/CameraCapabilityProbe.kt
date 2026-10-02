package com.s23log.probe

import com.s23log.probe.diagnostics.StreamDiagnostics
import android.content.Context
import android.graphics.ImageFormat
import android.hardware.camera2.CameraCharacteristics as C
import android.hardware.camera2.CameraManager
import android.hardware.camera2.params.StreamConfigurationMap
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaCodecList
import android.media.MediaFormat
import android.os.Build
import com.s23log.probe.core.CapturePolicy
import com.s23log.probe.diagnostics.ProbeReport
import com.s23log.probe.diagnostics.ProbeSection
import java.time.Instant

/** Metadata only: no cameras are opened and no sensor/recording capabilities are assumed. */
class CameraCapabilityProbe(context: Context) {
    private val manager = context.applicationContext.getSystemService(CameraManager::class.java)

    fun run(): ProbeReport {
        val sections = mutableListOf<ProbeSection>()
        val device = ProbeSection("device", Build.MODEL).also(sections::add)
        device.query("manufacturer") { Build.MANUFACTURER }
        device.query("model") { Build.MODEL }
        device.query("android") { Build.VERSION.RELEASE }
        device.query("api") { Build.VERSION.SDK_INT }
        device.query("build") { Build.DISPLAY }
        var ids = emptyList<String>()
        device.query("cameraIds") { manager.cameraIdList.toList().also { ids = it } }
        // Cache successes and failures, including physical-only IDs. No second scan for the summary.
        val characteristics = mutableMapOf<String, Result<C>>()
        fun get(id: String): C = characteristics.getOrPut(id) {
            runCatching { manager.getCameraCharacteristics(id) }
        }.getOrThrow()
        val targets = linkedMapOf<String, String?>()
        ids.forEach { targets[it] = null }
        ids.forEach { id ->
            val section = ProbeSection("camera", id).also(sections::add)
            section.query("characteristics") {
                val c = get(id)
                inspectCamera(section, c)
                if (Build.VERSION.SDK_INT >= 28) {
                    c.physicalCameraIds.forEach { physical -> if (physical !in targets) targets[physical] = id }
                }
                "read"
            }
        }
        targets.filterValues { it != null }.forEach { (id, parent) ->
            val section = ProbeSection("physical_camera", id).also(sections::add)
            section.query("logicalParent") { parent }
            section.query("independentlyOpenable") { id in ids }
            section.query("characteristics") { inspectCamera(section, get(id)); "read" }
        }
        val codecList = ProbeSection("codec_discovery", "encoders").also(sections::add)
        var codecs = emptyList<MediaCodecInfo>()
        codecList.query("enumeration") {
            MediaCodecList(MediaCodecList.REGULAR_CODECS).codecInfos.filter { it.isEncoder }
                .sortedBy { it.name }.also { codecs = it }.map { it.name }
        }
        codecs.forEach { codec ->
            val section = ProbeSection("encoder", codec.name)
            var useful = false
            section.query("videoTypes") {
                codec.supportedTypes.filter { it == MediaFormat.MIMETYPE_VIDEO_AVC || it == MediaFormat.MIMETYPE_VIDEO_HEVC }
                    .also { types ->
                        useful = types.isNotEmpty()
                        types.forEach { mime -> inspectCodec(section, codec, mime) }
                    }
            }
            if (useful || section.fields.values.any { it.status == "query_failed" }) sections += section
        }
        val summary = ProbeSection("summary", "advertised-only").also(sections::add)
        val cameras = sections.filter { it.kind == "camera" || it.kind == "physical_camera" }
        summary.query("camerasAdvertisingRAW") { cameras.filter { it.fields["rawCapability"]?.value == true }.map { it.id } }
        summary.query("camerasAdvertisingManualSensor") { cameras.filter { it.fields["manualSensor"]?.value == true }.map { it.id } }
        summary.query("camerasAdvertisingHLG10") { cameras.filter { it.fields["hlg10"]?.value == true }.map { it.id } }
        summary.query("recordingPathVerified") { false }
        return ProbeReport(Instant.now().toString(), sections, BuildConfig.SOURCE_REVISION, Build.FINGERPRINT)
    }

    private fun inspectCamera(s: ProbeSection, c: C) {
        s.query("hardwareLevel") { c[C.INFO_SUPPORTED_HARDWARE_LEVEL] }
        s.query("facing") { c[C.LENS_FACING] }
        s.query("orientation") { c[C.SENSOR_ORIENTATION] }
        s.query("capabilities") { c[C.REQUEST_AVAILABLE_CAPABILITIES]?.toList() }
        s.query("rawCapability") { c[C.REQUEST_AVAILABLE_CAPABILITIES]?.contains(C.REQUEST_AVAILABLE_CAPABILITIES_RAW) }
        s.query("manualSensor") { c[C.REQUEST_AVAILABLE_CAPABILITIES]?.contains(C.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR) }
        s.query("manualPostProcessing") { c[C.REQUEST_AVAILABLE_CAPABILITIES]?.contains(C.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_POST_PROCESSING) }
        if (Build.VERSION.SDK_INT >= 28) s.query("physicalCameraIds") { c.physicalCameraIds.sorted() }
        s.query("pixelArray") { c[C.SENSOR_INFO_PIXEL_ARRAY_SIZE] }
        s.query("activeArray") { c[C.SENSOR_INFO_ACTIVE_ARRAY_SIZE] }
        s.query("sensorPhysicalSizeMm") { c[C.SENSOR_INFO_PHYSICAL_SIZE] }
        s.query("isoRange") { c[C.SENSOR_INFO_SENSITIVITY_RANGE] }
        s.query("exposureNsRange") { c[C.SENSOR_INFO_EXPOSURE_TIME_RANGE] }
        s.query("maxFrameDurationNs") { c[C.SENSOR_INFO_MAX_FRAME_DURATION] }
        s.query("cfa") { c[C.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT] }
        s.query("whiteLevel") { c[C.SENSOR_INFO_WHITE_LEVEL] }
        s.query("blackLevel") { c[C.SENSOR_BLACK_LEVEL_PATTERN] }
        s.query("focalLengthsMm") { c[C.LENS_INFO_AVAILABLE_FOCAL_LENGTHS] }
        s.query("apertures") { c[C.LENS_INFO_AVAILABLE_APERTURES] }
        s.query("minimumFocusDiopters") { c[C.LENS_INFO_MINIMUM_FOCUS_DISTANCE] }
        s.query("flash") { c[C.FLASH_INFO_AVAILABLE] }
        s.query("aeFpsRanges") { c[C.CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES]?.map { listOf(it.lower, it.upper) } }
        s.query("aeCompensationRange") { c[C.CONTROL_AE_COMPENSATION_RANGE]?.let { listOf(it.lower, it.upper) } }
        s.query("aeCompensationStep") { c[C.CONTROL_AE_COMPENSATION_STEP]?.let { mapOf("numerator" to it.numerator, "denominator" to it.denominator) } }
        s.query("sensorTimestampSource") { c[C.SENSOR_INFO_TIMESTAMP_SOURCE] }
        s.query("awbModes") { c[C.CONTROL_AWB_AVAILABLE_MODES] }
        s.query("awbLockAvailable") { c[C.CONTROL_AWB_LOCK_AVAILABLE] }
        s.query("afModes") { c[C.CONTROL_AF_AVAILABLE_MODES] }
        s.query("oisModes") { c[C.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION] }
        s.query("eisModes") { c[C.CONTROL_AVAILABLE_VIDEO_STABILIZATION_MODES] }
        s.query("requestKeys") { c.availableCaptureRequestKeys?.map { it.name }?.sorted() }
        s.query("resultKeys") { c.availableCaptureResultKeys?.map { it.name }?.sorted() }
        if (Build.VERSION.SDK_INT >= 33) {
            s.query("tenBitCapability") { c[C.REQUEST_AVAILABLE_CAPABILITIES]?.contains(C.REQUEST_AVAILABLE_CAPABILITIES_DYNAMIC_RANGE_TEN_BIT) }
            s.query("dynamicRangeProfiles") {
                c[C.REQUEST_AVAILABLE_DYNAMIC_RANGE_PROFILES]?.let { profiles ->
                    profiles.supportedProfiles.sorted().map { p -> mapOf(
                        "id" to p, "tenBit" to CapturePolicy.isTenBitProfile(p),
                        "requestConstraints" to profiles.getProfileCaptureRequestConstraints(p).sorted(),
                        "extraLatency" to profiles.isExtraLatencyPresent(p)
                    ) }
                }
            }
            s.query("hlg10") {
                CapturePolicy.supportsHlg(
                    c[C.REQUEST_AVAILABLE_CAPABILITIES]?.contains(C.REQUEST_AVAILABLE_CAPABILITIES_DYNAMIC_RANGE_TEN_BIT) == true,
                    c[C.REQUEST_AVAILABLE_DYNAMIC_RANGE_PROFILES]?.supportedProfiles.orEmpty()
                )
            }
            s.query("recommendedTenBitProfile") { c[C.REQUEST_RECOMMENDED_TEN_BIT_DYNAMIC_RANGE_PROFILE] }
        } else s.unavailable("hlg10", "Requires Android API 33+")
        if (Build.VERSION.SDK_INT >= 34) s.query("colorSpacesByFormatAndProfile") {
            c[C.REQUEST_AVAILABLE_COLOR_SPACE_PROFILES]?.let { colors ->
                listOf(ImageFormat.PRIVATE, ImageFormat.YUV_420_888, ImageFormat.YCBCR_P010).associate { format ->
                    format.toString() to colors.getSupportedColorSpaces(format).associate { space ->
                        space.name to colors.getSupportedDynamicRangeProfiles(space, format).sorted()
                    }
                }
            }
        }
        s.query("streams") { streams(c[C.SCALER_STREAM_CONFIGURATION_MAP]) }
        s.query("highSpeedVideo") {
            c[C.SCALER_STREAM_CONFIGURATION_MAP]?.let { map ->
                if (c[C.REQUEST_AVAILABLE_CAPABILITIES]?.contains(C.REQUEST_AVAILABLE_CAPABILITIES_CONSTRAINED_HIGH_SPEED_VIDEO) == true)
                    map.highSpeedVideoSizes.map { size -> mapOf("size" to size.toString(), "fps" to map.getHighSpeedVideoFpsRangesFor(size).map { it.toString() }) }
                else emptyList<Any>()
            }
        }
        if (Build.VERSION.SDK_INT >= 31) s.query("maximumResolutionStreams") {
            streams(c[C.SCALER_STREAM_CONFIGURATION_MAP_MAXIMUM_RESOLUTION])
        }
    }

    private fun streams(map: StreamConfigurationMap?): Any? {
        if (map == null) return null
        val fallback = listOf(ImageFormat.RAW_SENSOR, ImageFormat.RAW10, ImageFormat.RAW12, ImageFormat.PRIVATE, ImageFormat.YUV_420_888) +
            if (Build.VERSION.SDK_INT >= 31) listOf(ImageFormat.YCBCR_P010) else emptyList()
        return StreamDiagnostics.collect(object : StreamDiagnostics.Queries {
            override fun formats() = map.outputFormats.toList()
            override fun sizes(format: Int) = map.getOutputSizes(format).orEmpty().map { StreamDiagnostics.Size(it.width, it.height) }
            override fun minimumDuration(format: Int, size: StreamDiagnostics.Size) = map.getOutputMinFrameDuration(format, android.util.Size(size.width, size.height))
            override fun stallDuration(format: Int, size: StreamDiagnostics.Size) = map.getOutputStallDuration(format, android.util.Size(size.width, size.height))
            override fun codecSizes() = map.getOutputSizes(MediaCodec::class.java)?.map { it.toString() }
        }, fallback)
    }

    private fun inspectCodec(s: ProbeSection, codec: MediaCodecInfo, mime: String) {
        if (Build.VERSION.SDK_INT >= 29) {
            s.query("hardwareAccelerated") { codec.isHardwareAccelerated }
            s.query("softwareOnly") { codec.isSoftwareOnly }
        }
        s.query(mime) {
            val caps = codec.getCapabilitiesForType(mime)
            val video = caps.videoCapabilities
            mapOf(
                "profilesAndLevels" to caps.profileLevels.map { mapOf("profile" to it.profile, "level" to it.level) },
                "colorFormats" to caps.colorFormats.toList(),
                "surfaceInput" to caps.colorFormats.contains(MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface),
                "p010BufferInput" to caps.colorFormats.contains(MediaCodecInfo.CodecCapabilities.COLOR_FormatYUVP010),
                "widthRange" to video?.supportedWidths.toString(), "heightRange" to video?.supportedHeights.toString(),
                "bitrateRange" to video?.bitrateRange.toString(),
                "sampleSizeRates" to listOf(1920 to 1080, 3840 to 2160, 7680 to 4320).map { (w, h) ->
                    try { mapOf("width" to w, "height" to h, "supported30fps" to video?.areSizeAndRateSupported(w, h, 30.0),
                        "fps" to if (video?.isSizeSupported(w, h) == true) video.getSupportedFrameRatesFor(w, h).toString() else null) }
                    catch (e: Exception) { mapOf("width" to w, "height" to h, "queryError" to e.toString()) }
                }
            )
        }
    }
}
