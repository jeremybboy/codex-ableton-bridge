import math
import shutil
import tempfile
import unittest
from pathlib import Path

from codex_ableton_bridge.audio import analyze, measure_main_render
from examples.synthetic_wav import write_wav


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required for audio tests")
class AudioTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "fixture.wav"

    def test_analyzes_synthetic_tone(self):
        write_wav(self.path)
        result = analyze(str(self.path), start=0.1, seconds=2)
        self.assertAlmostEqual(result["peak_dbfs"], 20 * math.log10(0.25), delta=0.1)
        self.assertAlmostEqual(result["peak_to_rms_db"], 3.01, delta=0.2)
        self.assertFalse(result["near_silence"])
        bands = result["approximate_band_rms_dbfs"]
        self.assertEqual(len(bands), 7)
        self.assertEqual(max(bands, key=bands.get), "900-2500 Hz")

    def test_reports_distinct_sample_and_true_peaks_and_level_change(self):
        write_wav(self.path, frequency=12000, phase=math.pi / 4)
        quiet = measure_main_render(str(self.path))
        self.assertAlmostEqual(quiet["sample_peak_dbfs"], -15.05, delta=0.1)
        self.assertGreater(quiet["true_peak_dbtp"], quiet["sample_peak_dbfs"] + 2)
        self.assertAlmostEqual(quiet["loudness_range_lu"], 0, delta=0.2)
        self.assertAlmostEqual(quiet["true_peak_headroom_db"], -quiet["true_peak_dbtp"], delta=0.05)
        write_wav(self.path, frequency=12000, amplitude=0.5, phase=math.pi / 4)
        loud = measure_main_render(str(self.path))
        for field in ("sample_peak_dbfs", "true_peak_dbtp", "integrated_loudness_lufs"):
            self.assertAlmostEqual(loud[field] - quiet[field], 6.02, delta=0.2)

    def test_silence_has_no_main_loudness(self):
        write_wav(self.path, amplitude=0)
        self.assertTrue(analyze(str(self.path))["near_silence"])
        with self.assertRaises(ValueError):
            measure_main_render(str(self.path))

    def test_rejects_an_offset_beyond_the_render(self):
        write_wav(self.path)
        with self.assertRaises((ValueError, RuntimeError)):
            analyze(str(self.path), start=7)
