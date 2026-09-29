import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_evidence import verify


class EvidenceChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.archive = Path(self.directory.name) / "reports.tar"
        self.videos = Path(self.directory.name) / "videos.json"
        self.clips = [{"fullDecodePassed": True, "packetSpanSeconds": 65}] * 12
        report = {"kind": "recording-validation", "status": "checked",
                  "stages": ["container_and_output_checked"],
                  "verification": {"firstSyncFrameDecoded": True, "sampleSpanUs": 65_000_000}}
        self.files = {f"files/exports/validation/recording-{i}.json": json.dumps(report) for i in range(12)}
        self.files["files/exports/reports/report-probe.json"] = '{"schemaVersion": 2}'
        self.files["files/exports/reports/report-probe.txt"] = "S23LOG"

    def check(self, require_audio=False):
        with tarfile.open(self.archive, "w") as tar:
            for name, text in self.files.items():
                encoded = text.encode()
                entry = tarfile.TarInfo(name)
                entry.size = len(encoded)
                tar.addfile(entry, io.BytesIO(encoded))
        self.videos.write_text(json.dumps(self.clips))
        return verify(self.archive, self.videos, require_audio)

    def test_complete_evidence(self):
        result = self.check()
        self.assertEqual(result["recordingReports"], 12)
        self.assertEqual(result["probeReports"], 1)

    def test_empty_report_archive_fails(self):
        self.files.clear()
        with self.assertRaises(ValueError):
            self.check()

    def test_missing_recording_fails(self):
        del self.files["files/exports/validation/recording-0.json"]
        with self.assertRaises(ValueError):
            self.check()

    def test_missing_text_export_fails(self):
        del self.files["files/exports/reports/report-probe.txt"]
        with self.assertRaises(ValueError):
            self.check()

    def test_rejected_recording_fails(self):
        self.files["files/exports/validation/recording-0.json"] = '{"kind":"recording-validation","status":"rejected"}'
        with self.assertRaises(ValueError):
            self.check()

    def test_missing_full_decode_fails(self):
        self.clips = [{"packetSpanSeconds": 65}] * 12
        with self.assertRaises(ValueError):
            self.check()

    def test_short_recordings_fail(self):
        self.clips = [{"fullDecodePassed": True, "packetSpanSeconds": 4}] * 12
        with self.assertRaises(ValueError):
            self.check()

    def test_unsafe_archive_path_fails(self):
        self.files["../outside.txt"] = "not extracted"
        with self.assertRaises(ValueError):
            self.check()


class AudioEvidenceChecks(unittest.TestCase):
    check = EvidenceChecks.check
    def setUp(self):
        EvidenceChecks.setUp(self)
        self.clips = [dict(c) for c in self.clips]
        for i in range(6):
            self.clips[i].update(audioPresent=True, audioFullDecodePassed=True, audioPacketSpanSeconds=65,
                                 audioStream={"channels": 2 if i == 0 else 1})
            name = f"files/exports/validation/recording-{i}.json"
            report = json.loads(self.files[name])
            report.update(schemaVersion=3, videoOnly=False, physicalLipSyncVerified=False,
                          audio={"builtInRouteConfirmed": True, "clock": {"source": "audio_timestamp_monotonic"}})
            report["stages"].append("av_samples_written")
            report["verification"]["firstAudioPcmDecoded"] = True
            self.files[name] = json.dumps(report)

    def test_audio_suite_complete(self):
        self.assertEqual(self.check(True)["audioRecordings"], 6)

    def test_video_only_cannot_satisfy_audio_gate(self):
        self.clips = [{"fullDecodePassed": True, "packetSpanSeconds": 65}] * 12
        with self.assertRaises(ValueError): self.check(True)

    def test_audio_decode_evidence_mandatory(self):
        self.clips[0]["audioFullDecodePassed"] = False
        with self.assertRaises(ValueError): self.check(True)

    def test_audio_duration_mandatory(self):
        for clip in self.clips: clip["audioPacketSpanSeconds"] = 3
        with self.assertRaises(ValueError): self.check(True)

    def test_stereo_cannot_be_silently_downmixed(self):
        for clip in self.clips: clip["audioStream"] = {"channels": 1}
        with self.assertRaises(ValueError): self.check(True)

    def test_audio_decode_stage_cannot_be_fabricated(self):
        name = "files/exports/validation/recording-0.json"
        report = json.loads(self.files[name]); report["verification"].pop("firstAudioPcmDecoded")
        self.files[name] = json.dumps(report)
        with self.assertRaises(ValueError): self.check(True)
