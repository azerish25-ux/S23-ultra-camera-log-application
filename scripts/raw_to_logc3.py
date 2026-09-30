#!/usr/bin/env python3
"""Develop S23RAW01 Bayer sequences into LogC3 EI800 / AWG3, with explicit calibration.

Reference/offline developer, not an ARRI sensor simulation. Requires NumPy, FFmpeg and
FFprobe. No guessed phone colour matrix, fake HLG tag, implicit retiming or source deletion.
See docs/RAW_SEQUENCE.md for the container and calibration contracts.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile
from typing import BinaryIO, Iterator
import zlib

import numpy as np

# ARRI, ALEXA Log C Curve: Usage in VFX, 2017-03, exposure-domain EI800 and AWG3.
XYZ_TO_AWG3 = np.array([[1.789066, -.482534, -.200076],
                        [-.639849, 1.396400, .194432],
                        [-.041532, .082335, .878868]], dtype=np.float64)
BAYER = ("RGGB", "GRBG", "GBRG", "BGGR")
MAX_JSON = 1_048_576
MAX_PIXELS = 64_000_000


def finite(value, label: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(f"{label} is below {minimum}")
    return float(value)


def integer(value, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


def load_json(data: bytes | str) -> dict:
    def invalid(value):
        raise ValueError(f"Nonfinite JSON constant: {value}")
    result = json.loads(data, parse_constant=invalid)
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")
    return result


def logc3_encode(linear) -> np.ndarray:
    """Signed linear toe; no pre-Log clamp, including scene-linear values above one."""
    x = np.asarray(linear, dtype=np.float64)
    if not np.isfinite(x).all():
        raise ValueError("Nonfinite scene-linear value")
    out = 5.367655 * x + .092809
    high = x > .010591
    # Evaluate only the logarithmic domain; np.where would also evaluate invalid low inputs.
    return np.where(high, .247190 * np.log10(5.555556 * np.maximum(x, .010591) + .052272) + .385537, out)


def logc3_decode(encoded) -> np.ndarray:
    y = np.asarray(encoded, dtype=np.float64)
    if not np.isfinite(y).all():
        raise ValueError("Nonfinite LogC3 value")
    return np.where(y > 5.367655 * .010591 + .092809,
                    (np.power(10., (y - .385537) / .247190) - .052272) / 5.555556,
                    (y - .092809) / 5.367655)


@dataclass(frozen=True)
class Frame:
    metadata: dict
    offset: int
    size: int


@dataclass(frozen=True)
class Sequence:
    path: Path
    header: dict
    frames: tuple[Frame, ...]
    recovered_tail_bytes: int
    byte_count: int
    mtime_ns: int


def read_exact(stream: BinaryIO, count: int) -> bytes:
    value = stream.read(count)
    if len(value) != count:
        raise EOFError("Truncated RAW record")
    return value


def scan(path: Path, recover_tail: bool = False) -> Sequence:
    """CRC-check every record without loading the complete recording into memory."""
    path = Path(path)
    before = path.stat()
    frames: list[Frame] = []
    recovered = 0
    with path.open("rb") as source:
        if read_exact(source, 8) != b"S23RAW01":
            raise ValueError("Not an S23RAW01 sequence")
        header_len, = struct.unpack("<I", read_exact(source, 4))
        if not 1 <= header_len <= MAX_JSON:
            raise ValueError("Invalid header length")
        header = load_json(read_exact(source, header_len))
        width = integer(header.get("width"), "width", 2)
        height = integer(header.get("height"), "height", 2)
        if width % 2 or height % 2 or width * height > MAX_PIXELS:
            raise ValueError("Unsupported dimensions")
        if header.get("schemaVersion") != 1 or header.get("kind") != "continuous-raw" or header.get("source") != "RAW_SENSOR":
            raise ValueError("Unsupported acquisition schema/source")
        if header.get("sampleEncoding") != "uint16le" or header.get("rowBytes") != 2 * width:
            raise ValueError("Unsupported sample layout")
        if integer(header.get("cfa"), "CFA") not in range(4):
            raise ValueError("Unsupported Bayer mosaic")
        integer(header.get("fpsRequested"), "fpsRequested", 1)
        previous = -1
        while True:
            beginning = source.tell()
            tag = source.read(4)
            if not tag:
                break
            try:
                if len(tag) < 4:
                    raise EOFError("Truncated record marker")
                if tag != b"FRM1":
                    raise ValueError(f"Unknown RAW record at byte {beginning}")
                sizes = read_exact(source, 12)
                metadata_len, payload_len = struct.unpack("<IQ", sizes)
                if not 1 <= metadata_len <= MAX_JSON or payload_len != width * height * 2:
                    raise ValueError("RAW record length does not match the header")
                metadata_bytes = read_exact(source, metadata_len)
                metadata = load_json(metadata_bytes)
                offset = source.tell()
                crc = zlib.crc32(metadata_bytes, zlib.crc32(sizes))
                remaining = payload_len
                while remaining:
                    block = read_exact(source, min(remaining, 1024 * 1024))
                    crc = zlib.crc32(block, crc)
                    remaining -= len(block)
                expected_crc, = struct.unpack("<I", read_exact(source, 4))
                if crc & 0xffffffff != expected_crc:
                    raise ValueError(f"RAW checksum mismatch at byte {beginning}; corruption is not tail recovery")
                timestamp = integer(metadata.get("sensorTimestampNs"), "sensorTimestampNs", 1)
                if timestamp <= previous:
                    raise ValueError("RAW timestamps repeat or regress")
                previous = timestamp
                levels(metadata)
                integer(metadata.get("iso"), "iso", 1)
                integer(metadata.get("exposureNs"), "exposureNs", 1)
                frames.append(Frame(metadata, offset, payload_len))
                if len(frames) > 100_000:
                    raise ValueError("Sequence exceeds the bounded frame-index limit")
            except EOFError:
                if not recover_tail:
                    raise ValueError("Truncated final RAW record; use --recover-tail explicitly to retain only complete records") from None
                recovered = before.st_size - beginning
                break
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Source changed during validation; stop capture before exporting")
    return Sequence(path, header, tuple(frames), recovered, before.st_size, before.st_mtime_ns)


def levels(metadata: dict) -> tuple[np.ndarray, float]:
    black = metadata.get("blackLevels")
    if not isinstance(black, list) or len(black) != 4:
        raise ValueError("Four black levels in 2x2 row-major order are required")
    black = np.array([finite(v, "black level", 0) for v in black])
    white = finite(metadata.get("whiteLevel"), "white level", 1)
    if white > 65535 or np.any(black >= white):
        raise ValueError("Invalid sensor normalization levels")
    return black, white


def validate_profile(profile: dict, seq: Sequence, allow_provisional: bool = False) -> dict:
    if profile.get("schemaVersion") != 1 or profile.get("kind") != "raw-colour-profile":
        raise ValueError("Unsupported colour profile")
    expected = profile.get("source", {})
    actual = {"fingerprint": seq.header.get("device", {}).get("fingerprint"),
              **{k: seq.header.get(k) for k in ("logicalCamera", "physicalCamera", "width", "height", "cfa")}}
    if expected != actual or not isinstance(actual["fingerprint"], str) or not actual["fingerprint"]:
        raise ValueError("Colour profile is not bound to this exact firmware/camera/RAW layout")
    calibration = profile.get("calibration", {})
    status = calibration.get("status")
    if status == "synthetic":
        if seq.header.get("device", {}).get("model") != "SYNTHETIC_FIXTURE":
            raise ValueError("A synthetic profile cannot calibrate a real camera")
    elif status != "measured" and not (status == "provisional" and allow_provisional):
        raise ValueError("Measured profile required; --allow-provisional is an explicit uncalibrated research mode")
    for key in ("evidence", "illuminant"):
        if not isinstance(calibration.get(key), str) or not calibration[key].strip():
            raise ValueError(f"Calibration {key} is required")
    scale = finite(profile.get("sceneScale"), "sceneScale", 1e-9)
    matrix = np.asarray(profile.get("cameraToXyzD65"), dtype=np.float64)
    if matrix.shape != (3, 3) or not np.isfinite(matrix).all() or np.linalg.cond(matrix) > 10000:
        raise ValueError("Invalid calibrated camera-to-XYZ D65 matrix")
    wb = profile.get("bayerWhiteBalance")
    if not isinstance(wb, list) or len(wb) != 4:
        raise ValueError("Four row-major Bayer white-balance gains required")
    wb = np.array([finite(v, "white balance", 1e-6) for v in wb])
    crop = profile.get("crop")
    if not isinstance(crop, list) or len(crop) != 4:
        raise ValueError("Explicit RAW-coordinate crop [left, top, width, height] required")
    left, top, width, height = [integer(v, "crop") for v in crop]
    if any(v % 2 for v in crop) or min(width, height) < 4 or left + width > seq.header["width"] or top + height > seq.header["height"]:
        raise ValueError("Crop must preserve Bayer phase and remain inside the source")
    iso = integer(profile.get("iso"), "profile iso", 1)
    exposure = integer(profile.get("exposureNs"), "profile exposureNs", 1)
    for frame in seq.frames:
        if abs(frame.metadata["iso"] / iso - 1) > .05 or abs(frame.metadata["exposureNs"] / exposure - 1) > .05:
            raise ValueError("Sensor exposure changed beyond the profile's 5% tolerance")
    return {"scale": scale, "matrix": matrix, "wb": wb, "crop": crop, "status": status}


def demosaic(mosaic: np.ndarray, cfa: int) -> np.ndarray:
    """Bilinear reference interpolation, normalized at edges; known samples are not replaced."""
    height, width = mosaic.shape
    rgb = np.empty((height, width, 3), dtype=np.float32)
    pattern = BAYER[cfa]
    for channel, name in enumerate("RGB"):
        mask = np.zeros((height, width), dtype=np.float32)
        for i, colour in enumerate(pattern):
            if colour == name:
                mask[i // 2::2, i % 2::2] = 1
        samples = np.pad(mosaic * mask, 1, mode="reflect")
        support = np.pad(mask, 1, mode="reflect")
        value = np.zeros_like(mosaic, dtype=np.float32)
        weight = np.zeros_like(mosaic, dtype=np.float32)
        for y, wy in enumerate((1, 2, 1)):
            for x, wx in enumerate((1, 2, 1)):
                value += wy * wx * samples[y:y + height, x:x + width]
                weight += wy * wx * support[y:y + height, x:x + width]
        rgb[..., channel] = np.where(mask != 0, mosaic, value / weight)
    return rgb


def develop(source: BinaryIO, seq: Sequence, frame: Frame, profile: dict) -> tuple[np.ndarray, dict]:
    source.seek(frame.offset)
    raw = np.frombuffer(read_exact(source, frame.size), dtype="<u2").reshape(seq.header["height"], seq.header["width"])
    left, top, width, height = profile["crop"]
    raw = raw[top:top + height, left:left + width]
    black, white = levels(frame.metadata)
    linear = raw.astype(np.float32)
    for i in range(4):
        samples = linear[i // 2::2, i % 2::2]
        samples -= black[i]
        samples *= profile["wb"][i] / (white - black[i])
    rgb = demosaic(linear, seq.header["cfa"])
    xyz = rgb @ profile["matrix"].T
    awg = (xyz @ XYZ_TO_AWG3.T) * profile["scale"]
    encoded = logc3_encode(awg)
    if not np.isfinite(encoded).all():
        raise ValueError("Nonfinite developed pixels")
    return encoded, {"sensorSaturatedSamples": int(np.count_nonzero(raw >= white)),
                     "outputBelowZero": int(np.count_nonzero(encoded < 0)),
                     "outputAboveOne": int(np.count_nonzero(encoded > 1))}


def timing(seq: Sequence, allow_retime: bool = False) -> dict:
    if len(seq.frames) < 2:
        raise ValueError("At least two complete frames are required for a video")
    fps = seq.header["fpsRequested"]
    pts = np.array([f.metadata["sensorTimestampNs"] for f in seq.frames], dtype=np.int64)
    intervals = np.diff(pts)
    period = 1e9 / fps
    deviation = float(np.max(np.abs(intervals / period - 1)))
    measured = (len(pts) - 1) * 1e9 / int(pts[-1] - pts[0])
    qualified = deviation <= .03 and abs(measured / fps - 1) <= .03
    if not qualified and not allow_retime:
        raise ValueError("Source is not within the 3% CFR tolerance; --allow-retime must explicitly authorize retiming")
    return {"outputFps": fps, "sourceMeasuredFps": measured, "sourceMaximumIntervalDeviation": deviation,
            "cfrMapping": True, "retimingExplicitlyAllowed": allow_retime, "sourceWithinTolerance": qualified,
            "sourceTimestampsNs": pts.tolist(), "framesDuplicatedOrInterpolated": 0}


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def encode(seq: Sequence, profile_json: dict, output: Path, codec: str = "ffv1", *,
           allow_provisional: bool = False, allow_retime: bool = False, allow_clipping: bool = False) -> dict:
    """Produce a new file, verify all decoded frames, then publish the colour/identity sidecar."""
    profile = validate_profile(profile_json, seq, allow_provisional)
    clock = timing(seq, allow_retime)
    output = Path(output)
    sidecar = output.with_suffix(output.suffix + ".logc3.json")
    if output.exists() or sidecar.exists():
        raise ValueError("Output or sidecar already exists; originals are never overwritten")
    if codec not in ("ffv1", "hevc10"):
        raise ValueError("Unknown output codec")
    if output.suffix.lower() != (".mkv" if codec == "ffv1" else ".mp4"):
        raise ValueError("Use .mkv for the lossless RGB master or .mp4 for HEVC10")
    _, _, width, height = profile["crop"]
    summary = {"sensorSaturatedSamples": 0, "outputBelowZero": 0, "outputAboveOne": 0}
    hashes: list[str] = []
    with tempfile.TemporaryDirectory(prefix="s23log-", dir=output.parent) as temporary:
        temp = Path(temporary)
        candidate = temp / output.name
        args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-f", "rawvideo", "-pixel_format", "rgb48le",
                "-video_size", f"{width}x{height}", "-framerate", str(clock["outputFps"]), "-i", "pipe:0", "-an", "-threads", "1"]
        if codec == "ffv1":
            args += ["-c:v", "ffv1", "-level", "3", "-pix_fmt", "gbrp16le", "-color_range", "pc",
                     "-color_primaries", "2", "-color_trc", "2"]
        else:
            args += ["-vf", "scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p10le",
                     "-c:v", "libx265", "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p10le",
                     "-x265-params", "pools=1:frame-threads=1:log-level=error:colorprim=2:transfer=2:colormatrix=bt709:range=limited",
                     "-colorspace", "bt709", "-color_primaries", "2", "-color_trc", "2", "-color_range", "tv", "-tag:v", "hvc1"]
        args += ["-metadata", "comment=S23Log RAW-derived LogC3 EI800 / AWG3; import using matching sidecar", str(candidate)]
        with (temp / "encoder.log").open("w+b") as errors, seq.path.open("rb") as source:
            process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors)
            try:
                for frame in seq.frames:
                    pixels, counts = develop(source, seq, frame, profile)
                    for key, value in counts.items():
                        summary[key] += value
                    if not allow_clipping and (counts["outputBelowZero"] or counts["outputAboveOne"]):
                        raise ValueError("Log output exceeds normalized storage; source preserved. Explicit --allow-output-clipping is required")
                    packed = np.rint(np.clip(pixels, 0, 1) * 65535).astype("<u2").tobytes()
                    hashes.append(hashlib.sha256(packed).hexdigest())
                    process.stdin.write(packed)
                process.stdin.close()
                if process.wait(timeout=300):
                    errors.seek(0)
                    raise ValueError("FFmpeg encode failed: " + errors.read(8192).decode(errors="replace"))
            except BaseException:
                process.kill(); process.wait()
                raise
            finally:
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
        probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(candidate)]))
        streams = probe.get("streams", [])
        if len(streams) != 1 or streams[0].get("codec_type") != "video":
            raise ValueError("Expected one video-only output track")
        stream = streams[0]
        expected_pixel = "gbrp16le" if codec == "ffv1" else "yuv420p10le"
        if stream.get("pix_fmt") != expected_pixel or stream.get("width") != width or stream.get("height") != height:
            raise ValueError("Encoded precision or dimensions differ from the requested contract")
        if stream.get("color_transfer", "unknown") != "unknown" or stream.get("color_primaries", "unknown") != "unknown":
            raise ValueError("LogC3/AWG3 was incorrectly tagged as a different transfer/gamut")
        decoder = ["ffmpeg", "-v", "error", "-i", str(candidate), "-an", "-threads", "1"]
        if codec == "hevc10":
            decoder += ["-vf", "scale=in_range=tv:out_range=full:in_color_matrix=bt709"]
        decoder += ["-f", "rawvideo", "-pix_fmt", "rgb48le", "pipe:1"]
        count = 0
        maximum_mean_error = 0.
        with (temp / "decoder.log").open("w+b") as errors, seq.path.open("rb") as source:
            process = subprocess.Popen(decoder, stdout=subprocess.PIPE, stderr=errors)
            try:
                for i, frame in enumerate(seq.frames):
                    decoded = read_exact(process.stdout, width * height * 6)
                    if codec == "ffv1":
                        if hashlib.sha256(decoded).hexdigest() != hashes[i]:
                            raise ValueError("Lossless master decoded to different RGB values")
                    else:
                        reference, _ = develop(source, seq, frame, profile)
                        reference = np.clip(reference, 0, 1)
                        actual = np.frombuffer(decoded, dtype="<u2").reshape(height, width, 3) / 65535.
                        error = float(np.mean(np.abs(actual - reference)))
                        maximum_mean_error = max(maximum_mean_error, error)
                        if error > .02:
                            raise ValueError("HEVC round-trip mean RGB error exceeds 0.02; not publishing this output")
                    count += 1
                if process.stdout.read(1):
                    raise ValueError("Decoder produced more frames than the RAW source")
                if process.wait(timeout=300):
                    errors.seek(0)
                    raise ValueError("Full decode failed: " + errors.read(8192).decode(errors="replace"))
            finally:
                if process.poll() is None:
                    process.kill(); process.wait()
                process.stdout.close()
        stat = seq.path.stat()
        if (stat.st_size, stat.st_mtime_ns) != (seq.byte_count, seq.mtime_ns):
            raise ValueError("Source changed during development")
        report = {"schemaVersion": 1, "kind": "raw-derived-logc3", "source": seq.path.name,
                  "sourceSha256": sha256(seq.path), "sourceHeader": seq.header,
                  "outputSha256": sha256(candidate), "profileSha256": hashlib.sha256(json.dumps(profile_json, sort_keys=True).encode()).hexdigest(),
                  "profile": profile_json, "calibrationStatus": profile["status"], "transfer": "ARRI_LogC3_EI800_exposure",
                  "primaries": "ARRI_Wide_Gamut_3", "whitePoint": "D65", "codec": codec, "decodedPixelFormat": expected_pixel,
                  "storageBits": 16 if codec == "ffv1" else 10, "dataLevels": "full" if codec == "ffv1" else "video",
                  "yuvMatrix": None if codec == "ffv1" else "BT709_coefficients_not_primaries",
                  "decodedFrames": count, "fullDecodeVerified": True, "losslessRgbVerified": codec == "ffv1",
                  "maximumFrameMeanRgbError": maximum_mean_error, "timing": clock, "clipping": summary,
                  "outputClippingExplicitlyAllowed": allow_clipping, "recoveredTailBytes": seq.recovered_tail_bytes,
                  "orientationDegrees": seq.header.get("orientationDegrees", 0), "orientationApplied": False,
                  "demosaic": "bilinear_reference", "audio": "none", "physicalCameraCertified": False,
                  "arriSensorDynamicRangeClaimed": False, "arriraw": False,
                  "editorImport": "Assign ARRI Wide Gamut 3 / LogC3; use stated data levels and apply orientation separately. Do not assign HLG or LogC4."}
        sidecar_temp = temp / sidecar.name
        sidecar_temp.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        # No replacement: concurrent publishers cannot overwrite an existing original.
        import os
        os.link(candidate, output)
        try:
            os.link(sidecar_temp, sidecar)
        except BaseException:
            # Keep the newly generated media rather than deleting a usable file after report failure.
            raise RuntimeError(f"Video preserved at {output}; sidecar publication failed. Re-run with a new output name")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--codec", choices=("ffv1", "hevc10"), default="ffv1")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--recover-tail", action="store_true")
    parser.add_argument("--allow-provisional", action="store_true")
    parser.add_argument("--allow-retime", action="store_true")
    parser.add_argument("--allow-output-clipping", action="store_true")
    args = parser.parse_args()
    try:
        sequence = scan(args.source, args.recover_tail)
        if args.inspect:
            print(json.dumps({"header": sequence.header, "completeFrames": len(sequence.frames),
                              "recoveredTailBytes": sequence.recovered_tail_bytes}, indent=2))
        else:
            if args.profile is None or args.output is None:
                parser.error("--profile and --output are required for colour development")
            result = encode(sequence, load_json(args.profile.read_text()), args.output, args.codec,
                            allow_provisional=args.allow_provisional, allow_retime=args.allow_retime,
                            allow_clipping=args.allow_output_clipping)
            print(json.dumps({k: result[k] for k in ("decodedFrames", "transfer", "primaries", "calibrationStatus", "outputSha256")}, indent=2))
    except (ValueError, EOFError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"RAW development failed: {exc}\n")


if __name__ == "__main__":
    main()
