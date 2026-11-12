import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from player import find_first_video, build_mpv_command

class TestPi3VideoKiosk(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_find_first_video_strict_mono_file(self):
        # Crear 2 videos válidos
        vid_b = os.path.join(self.temp_dir.name, "b_segundo_video.mp4")
        with open(vid_b, "wb") as f:
            f.write(b"0" * (1024 * 1024 + 50))  # > 1 MB

        vid_a = os.path.join(self.temp_dir.name, "a_primer_video.mp4")
        with open(vid_a, "wb") as f:
            f.write(b"0" * (1024 * 1024 + 100))  # > 1 MB

        # Archivo basura de macOS que debe ser ignorado
        mac_junk = os.path.join(self.temp_dir.name, "._a_primer_video.mp4")
        with open(mac_junk, "wb") as f:
            f.write(b"mac_resource_fork_metadata")

        # Archivo corrupto o pequeño que debe ser ignorado
        tiny_vid = os.path.join(self.temp_dir.name, "0_corrupt.mp4")
        with open(tiny_vid, "wb") as f:
            f.write(b"tiny")

        # Debe tomar estrictamente el PRIMERO ordenado alfabéticamente
        chosen = find_first_video(self.temp_dir.name)
        self.assertIsNotNone(chosen)
        self.assertEqual(os.path.basename(chosen), "a_primer_video.mp4")

    def test_empty_directory_returns_none(self):
        chosen = find_first_video(self.temp_dir.name)
        self.assertIsNone(chosen)

    def test_build_mpv_command_flags(self):
        vid = "/media/usb/test.mp4"
        cmd = build_mpv_command(vid)

        self.assertIn("--fullscreen", cmd)
        self.assertIn("--loop-file=inf", cmd)
        self.assertIn("--hwdec=auto-safe", cmd)
        self.assertIn("--profile=fast", cmd)
        self.assertIn("--vd-lavc-threads=4", cmd)
        self.assertIn("--audio-device=auto", cmd)
        self.assertIn("--volume=100", cmd)
        self.assertIn("--cursor-autohide=always", cmd)
        self.assertEqual(cmd[-1], vid)

if __name__ == "__main__":
    unittest.main()
