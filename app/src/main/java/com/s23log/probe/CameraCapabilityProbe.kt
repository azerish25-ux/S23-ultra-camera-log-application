package com.s23log.probe

import android.content.Context
import android.graphics.ImageFormat
import android.graphics.ColorSpace
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.hardware.camera2.params.DynamicRangeProfiles
import android.media.MediaCodecInfo
import android.media.MediaCodecList
import android.media.MediaFormat
import android.os.Build
import android.util.Range
import android.util.Size
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class CameraCapabilityProbe(private val context: Context) {
    private val lines = mutableListOf<String>()

    fun run(): String {
        header()
        cameraSection()
        codecSection()
        verdictSection()
        return lines.joinToString("\n")
    }

    private fun header() {
        line("S23LOG CAMERA CAPABILITY REPORT")
        line("Generated: ${SimpleDateFormat("yyyy-MM-dd HH:mm:ss Z", Locale.US).format(Date())}")
        line("Device: ${Build.MANUFACTURER} ${Build.MODEL}")
        line("Product: ${Build.PRODUCT}")
        line("Android: ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
        line("Build: ${Build.DISPLAY}")
        line("")
    }

    private fun cameraSection() {
        val manager = context.getSystemService(CameraManager::class.java)
        line("=== CAMERA2 DEVICES ===")
        line("Camera IDs: ${manager.cameraIdList.joinToString()}")
        line("")

        manager.cameraIdList.forEach { id ->
            val c = manager.getCameraCharacteristics(id)
            val caps = c.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)?.toSet().orEmpty()
            line("--- Camera $id ---")
            line("Facing: ${facingName(c.get(CameraCharacteristics.LENS_FACING))}")
            line("Hardware level: ${hardwareLevelName(c.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL))}")
            line("Capabilities: ${caps.map(::capabilityName).sorted().joinToString()}")
            line("RAW capability: ${CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_RAW in caps}")
            line("Manual sensor: ${CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR in caps}")
            line("Manual post-processing: ${CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_POST_PROCESSING in caps}")
            line("Logical multi-camera: ${CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_LOGICAL_MULTI_CAMERA in caps}")
            line("Ultra-high-resolution sensor: ${if (Build.VERSION.SDK_INT >= 31) CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_ULTRA_HIGH_RESOLUTION_SENSOR in caps else "n/a"}")

            val physicalIds = if (Build.VERSION.SDK_INT >= 28) c.physicalCameraIds else emptySet()
            line("Physical camera IDs: ${physicalIds.ifEmpty { setOf("none") }.joinToString()}")

            line("Sensor pixel array: ${c.get(CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE).fmt()}")
            line("Sensor active array: ${c.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE) ?: "n/a"}")
            line("Sensitivity ISO range: ${c.get(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE).fmt()}")
            line("Exposure-time range: ${c.get(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE).fmtNs()}")
            line("Max frame duration: ${c.get(CameraCharacteristics.SENSOR_INFO_MAX_FRAME_DURATION)?.let { "${it} ns (${nsToMs(it)} ms)" } ?: "n/a"}")
            line("Color filter arrangement: ${colorFilterName(c.get(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT))}")
            line("White level: ${c.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL) ?: "n/a"}")
            line("Black-level pattern: ${c.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN) ?: "n/a"}")

            line("Focal lengths: ${c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)?.joinToString() ?: "n/a"} mm")
            line("Apertures: ${c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_APERTURES)?.joinToString() ?: "n/a"}")
            line("Minimum focus distance: ${c.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE) ?: "n/a"} diopters")
            line("Flash: ${c.get(CameraCharacteristics.FLASH_INFO_AVAILABLE) ?: false}")
            line("AE FPS ranges: ${c.get(CameraCharacteristics.CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES)?.joinToString() ?: "n/a"}")
            line("Video stabilization modes: ${c.get(CameraCharacteristics.CONTROL_AVAILABLE_VIDEO_STABILIZATION_MODES)?.joinToString() ?: "n/a"}")
            line("Optical stabilization modes: ${c.get(CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION)?.joinToString() ?: "n/a"}")

            if (Build.VERSION.SDK_INT >= 33) {
                val profiles = c.get(CameraCharacteristics.REQUEST_AVAILABLE_DYNAMIC_RANGE_PROFILES)
                line("Dynamic-range profiles: ${profiles?.supportedProfiles?.map(::dynamicRangeName)?.joinToString() ?: "n/a"}")
                line("Recommended 10-bit profile: ${c.get(CameraCharacteristics.REQUEST_RECOMMENDED_TEN_BIT_DYNAMIC_RANGE_PROFILE)?.let(::dynamicRangeName) ?: "n/a"}")
            }

            if (Build.VERSION.SDK_INT >= 34) {
                val colorProfiles = c.get(CameraCharacteristics.REQUEST_AVAILABLE_COLOR_SPACE_PROFILES)
                val named = colorProfiles?.getSupportedColorSpaces(ImageFormat.YUV_420_888)
                    ?.map(ColorSpace.Named::name)
                    ?.sorted()
                    ?.joinToString()
                line("YUV color spaces: ${named ?: "n/a"}")
            }

            val map = c.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
            if (map == null) {
                line("Stream configuration map: unavailable")
            } else {
                formatBlock("RAW_SENSOR", map.getOutputSizes(ImageFormat.RAW_SENSOR))
                formatBlock("RAW10", map.getOutputSizes(ImageFormat.RAW10))
                formatBlock("RAW12", map.getOutputSizes(ImageFormat.RAW12))
                formatBlock("YUV_420_888", map.getOutputSizes(ImageFormat.YUV_420_888))
                formatBlock("PRIVATE", map.getOutputSizes(ImageFormat.PRIVATE))
                formatBlock("JPEG", map.getOutputSizes(ImageFormat.JPEG))
            }
            line("")
        }
    }

    private fun codecSection() {
        line("=== MEDIA CODEC ENCODERS ===")
        val codecs = MediaCodecList(MediaCodecList.ALL_CODECS).codecInfos
            .filter { it.isEncoder }
            .sortedBy { it.name }

        val hevc = codecs.filter { MediaFormat.MIMETYPE_VIDEO_HEVC in it.supportedTypes }
        line("HEVC encoders found: ${hevc.size}")
        hevc.forEach { codec ->
            val caps = codec.getCapabilitiesForType(MediaFormat.MIMETYPE_VIDEO_HEVC)
            line("--- ${codec.name} ---")
            line("Hardware accelerated: ${if (Build.VERSION.SDK_INT >= 29) codec.isHardwareAccelerated else "unknown"}")
            line("Software only: ${if (Build.VERSION.SDK_INT >= 29) codec.isSoftwareOnly else "unknown"}")
            line("Vendor: ${if (Build.VERSION.SDK_INT >= 29) codec.isVendor else "unknown"}")
            line("HEVC profiles: ${caps.profileLevels.map { hevcProfileName(it.profile) }.distinct().joinToString()}")
            line("10-bit HEVC: ${caps.profileLevels.any { isHevc10BitProfile(it.profile) }}")
            line("P010 input: ${MediaCodecInfo.CodecCapabilities.COLOR_FormatYUVP010 in caps.colorFormats}")
            line("Color formats: ${caps.colorFormats.joinToString()}")
            caps.videoCapabilities?.let { v ->
                line("Width range: ${v.supportedWidths}")
                line("Height range: ${v.supportedHeights}")
                line("Bitrate range: ${v.bitrateRange}")
                line("Frame-rate range: ${v.supportedFrameRates}")
                listOf(Size(3840, 2160), Size(7680, 4320)).forEach { s ->
                    val supported = runCatching { v.isSizeSupported(s.width, s.height) }.getOrDefault(false)
                    line("${s.width}x${s.height} supported: $supported")
                    if (supported) {
                        val fps = runCatching { v.getSupportedFrameRatesFor(s.width, s.height) }.getOrNull()
                        line("${s.width}x${s.height} FPS: ${fps ?: "n/a"}")
                    }
                }
            }
        }
        line("")
    }

    private fun verdictSection() {
        val manager = context.getSystemService(CameraManager::class.java)
        var raw = false
        var manual = false
        var tenBitCamera = false

        manager.cameraIdList.forEach { id ->
            val c = manager.getCameraCharacteristics(id)
            val caps = c.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)?.toSet().orEmpty()
            raw = raw || CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_RAW in caps
            manual = manual || CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR in caps
            if (Build.VERSION.SDK_INT >= 33) {
                val profiles = c.get(CameraCharacteristics.REQUEST_AVAILABLE_DYNAMIC_RANGE_PROFILES)
                tenBitCamera = tenBitCamera || profiles?.supportedProfiles.orEmpty().any {
                    it != DynamicRangeProfiles.STANDARD
                }
            }
        }

        val hevc10 = MediaCodecList(MediaCodecList.ALL_CODECS).codecInfos
            .filter { it.isEncoder && MediaFormat.MIMETYPE_VIDEO_HEVC in it.supportedTypes }
            .any { codec ->
                codec.getCapabilitiesForType(MediaFormat.MIMETYPE_VIDEO_HEVC)
                    .profileLevels.any { isHevc10BitProfile(it.profile) }
            }

        line("=== S23LOG PHASE-1 SUMMARY ===")
        line("Any Camera2 RAW path: $raw")
        line("Any manual-sensor camera: $manual")
        line("Any advertised non-standard/10-bit dynamic-range profile: $tenBitCamera")
        line("Any HEVC Main10-class encoder: $hevc10")
        line("")
        line("Interpretation: this report records what Android publicly exposes. It does not assume that Samsung's stock-camera private ISP pipeline or proprietary LOG processing is accessible to third-party apps.")
    }

    private fun formatBlock(name: String, sizes: Array<Size>?) {
        val sorted = sizes.orEmpty().sortedWith(compareByDescending<Size> { it.width.toLong() * it.height }.thenByDescending { it.width })
        line("$name outputs (${sorted.size}): ${sorted.take(30).joinToString { "${it.width}x${it.height}" }}${if (sorted.size > 30) " …" else ""}")
    }

    private fun facingName(value: Int?): String = when (value) {
        CameraCharacteristics.LENS_FACING_FRONT -> "FRONT"
        CameraCharacteristics.LENS_FACING_BACK -> "BACK"
        CameraCharacteristics.LENS_FACING_EXTERNAL -> "EXTERNAL"
        else -> "UNKNOWN($value)"
    }

    private fun hardwareLevelName(value: Int?): String = when (value) {
        CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_LEGACY -> "LEGACY"
        CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_LIMITED -> "LIMITED"
        CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_FULL -> "FULL"
        CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_3 -> "LEVEL_3"
        CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_EXTERNAL -> "EXTERNAL"
        else -> "UNKNOWN($value)"
    }

    private fun capabilityName(value: Int): String = when (value) {
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_BACKWARD_COMPATIBLE -> "BACKWARD_COMPATIBLE"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR -> "MANUAL_SENSOR"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_POST_PROCESSING -> "MANUAL_POST_PROCESSING"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_RAW -> "RAW"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_PRIVATE_REPROCESSING -> "PRIVATE_REPROCESSING"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_READ_SENSOR_SETTINGS -> "READ_SENSOR_SETTINGS"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_BURST_CAPTURE -> "BURST_CAPTURE"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_YUV_REPROCESSING -> "YUV_REPROCESSING"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT -> "DEPTH_OUTPUT"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_CONSTRAINED_HIGH_SPEED_VIDEO -> "HIGH_SPEED_VIDEO"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_MOTION_TRACKING -> "MOTION_TRACKING"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_LOGICAL_MULTI_CAMERA -> "LOGICAL_MULTI_CAMERA"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_MONOCHROME -> "MONOCHROME"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_SECURE_IMAGE_DATA -> "SECURE_IMAGE_DATA"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_SYSTEM_CAMERA -> "SYSTEM_CAMERA"
        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_OFFLINE_PROCESSING -> "OFFLINE_PROCESSING"
        else -> "CAPABILITY_$value"
    }

    private fun colorFilterName(value: Int?): String = when (value) {
        CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_RGGB -> "RGGB"
        CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_GRBG -> "GRBG"
        CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_GBRG -> "GBRG"
        CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_BGGR -> "BGGR"
        CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_RGB -> "RGB"
        CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_MONO -> "MONO"
        CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT_NIR -> "NIR"
        else -> "UNKNOWN($value)"
    }

    private fun dynamicRangeName(profile: Long): String = when (profile) {
        DynamicRangeProfiles.STANDARD -> "STANDARD"
        DynamicRangeProfiles.HLG10 -> "HLG10"
        DynamicRangeProfiles.HDR10 -> "HDR10"
        DynamicRangeProfiles.HDR10_PLUS -> "HDR10_PLUS"
        DynamicRangeProfiles.DOLBY_VISION_10B_HDR_REF -> "DOLBY_VISION_10B_HDR_REF"
        DynamicRangeProfiles.DOLBY_VISION_10B_HDR_REF_PO -> "DOLBY_VISION_10B_HDR_REF_PO"
        DynamicRangeProfiles.DOLBY_VISION_10B_HDR_OEM -> "DOLBY_VISION_10B_HDR_OEM"
        DynamicRangeProfiles.DOLBY_VISION_10B_HDR_OEM_PO -> "DOLBY_VISION_10B_HDR_OEM_PO"
        DynamicRangeProfiles.DOLBY_VISION_8B_HDR_REF -> "DOLBY_VISION_8B_HDR_REF"
        DynamicRangeProfiles.DOLBY_VISION_8B_HDR_REF_PO -> "DOLBY_VISION_8B_HDR_REF_PO"
        DynamicRangeProfiles.DOLBY_VISION_8B_HDR_OEM -> "DOLBY_VISION_8B_HDR_OEM"
        DynamicRangeProfiles.DOLBY_VISION_8B_HDR_OEM_PO -> "DOLBY_VISION_8B_HDR_OEM_PO"
        else -> "PROFILE_$profile"
    }

    private fun hevcProfileName(profile: Int): String = when (profile) {
        MediaCodecInfo.CodecProfileLevel.HEVCProfileMain -> "Main8"
        MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10 -> "Main10"
        MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10HDR10 -> "Main10 HDR10"
        MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10HDR10Plus -> "Main10 HDR10+"
        else -> "profile=0x${profile.toString(16)}"
    }

    private fun isHevc10BitProfile(profile: Int): Boolean = profile == MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10 ||
        profile == MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10HDR10 ||
        profile == MediaCodecInfo.CodecProfileLevel.HEVCProfileMain10HDR10Plus

    private fun Size?.fmt(): String = this?.let { "${it.width}x${it.height}" } ?: "n/a"

    private fun <T : Comparable<T>> Range<T>?.fmt(): String = this?.toString() ?: "n/a"

    private fun Range<Long>?.fmtNs(): String = this?.let {
        "${it.lower}..${it.upper} ns (${nsToMs(it.lower)}..${nsToMs(it.upper)} ms)"
    } ?: "n/a"

    private fun nsToMs(ns: Long): String = String.format(Locale.US, "%.3f", ns / 1_000_000.0)

    private fun line(value: String) {
        lines += value
    }
}
