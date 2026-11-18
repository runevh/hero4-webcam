"""Offline regression checks. Requires the official extracted firmware locally.

Run: .venv/bin/python -m unittest discover -s tests -v
No camera, SD card, USB access or network is used.
"""
import hashlib
from pathlib import Path
import struct
import sys
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import prepare_diagnostics as diag
from fwunpack import GLOBAL_HEADER_SIZE, SECTION_HEADER_SIZE, sections


class DiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'firmware/v05.00.00/camera_firmware.bin'
        if not path.exists():
            raise RuntimeError('Extract the official stock firmware before running these checks')
        cls.stock = path.read_bytes()
        cls.patched, cls.report = diag.patch_diagnostics(cls.stock)

    def test_exact_output(self):
        self.assertEqual(hashlib.sha256(self.patched).hexdigest(), diag.DIAGNOSTIC_SHA256)
        self.assertEqual(self.report['changed_bytes'], 336)
        self.assertEqual(len(self.report['changed_ubifs_nodes']), 1)

    def test_no_video_kernel_dsp_changes(self):
        for s in list(sections(self.stock))[:4]:
            start, end = s['hdr'], s['start'] + s['length']
            self.assertEqual(self.stock[start:end], self.patched[start:end])

    def test_corrupt_stock_rejected(self):
        damaged = bytearray(self.stock)
        damaged[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'exact supported stock'):
            diag.patch_diagnostics(bytes(damaged))

    def test_repatched_input_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exact supported stock'):
            diag.patch_diagnostics(self.patched)

    def test_unexpected_rtos_edit_rejected_even_with_valid_crcs(self):
        damaged = bytearray(self.patched)
        s = list(sections(damaged))[1]
        start, end = s['start'], s['start'] + s['length']
        damaged[start + 1024] ^= 1
        struct.pack_into('<I', damaged, start - SECTION_HEADER_SIZE, zlib.crc32(damaged[start:end]))
        struct.pack_into('<I', damaged, 0, zlib.crc32(damaged[GLOBAL_HEADER_SIZE:]))
        diag.validate(damaged)  # valid CRCs alone must not make this acceptable
        with self.assertRaisesRegex(ValueError, 'unexpected change|protected section'):
            diag.verify_delta(self.stock, bytes(damaged))

    def test_hook_is_separate_and_opt_in(self):
        self.assertIn(b'h4diag.enable', diag.DIAGNOSTIC_SCRIPT)
        self.assertNotIn(b'/h4.sh', diag.DIAGNOSTIC_SCRIPT)
        self.assertNotIn(b'insmod', diag.DIAGNOSTIC_SCRIPT)


if __name__ == '__main__':
    unittest.main()
