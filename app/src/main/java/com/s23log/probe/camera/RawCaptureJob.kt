package com.s23log.probe.camera

import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraDevice
import android.view.Surface

/** CameraController retains ownership of the camera/session while a RAW job owns its input buffers. */
interface RawCaptureJob {
    val surface: Surface
    fun start(camera: CameraDevice, captureSession: CameraCaptureSession)
    fun cancel(message: String)
    fun stop() = cancel("RAW capture stopped by user")
}
