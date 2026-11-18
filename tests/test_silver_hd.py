"""Reject unintended firmware changes even when their CRCs are valid."""
from pathlib import Path
import sys
import unittest
import struct

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import prepare_silver_hd as hd


class SilverHDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = (ROOT / 'build/silver-diagnostics-v1/UPDATE/camera_firmware.bin').read_bytes()
        cls.candidate, cls.report = hd.patch(cls.base)

    def test_reversible_exact_change(self):
        self.assertTrue(self.report['reversed_patch_matches_tested_diagnostic'])
        self.assertEqual(len(self.report['dimensions']), 2)
        self.assertEqual(self.report['changed_bytes_from_diagnostic'], 16)
        self.assertEqual(self.report['candidate_sha256'], hd.HD_SHA256)
        # Root filesystem, DSP, kernel and other sections are byte-identical.
        for i, section in enumerate(hd.validate(self.base)):
            if i != 1:
                lo, hi = section['hdr'], section['start'] + section['length']
                self.assertEqual(self.base[lo:hi], self.candidate[lo:hi])

    def test_extra_rtos_edit_rejected_with_valid_crcs(self):
        bad = bytearray(self.candidate)
        section = hd.validate(self.base)[1]
        bad[section['start'] + 1024] ^= 1
        hd.crc(bad, section)
        hd.validate(bad)
        with self.assertRaisesRegex(ValueError, 'unexpected changes'):
            hd.verify(self.base, bad)

    def test_wrong_dimensions_rejected(self):
        bad = bytearray(self.candidate)
        struct.pack_into('<I', bad, self.report['dimensions'][0]['file_offset'], 3840)
        hd.crc(bad, hd.validate(self.base)[1])
        with self.assertRaisesRegex(ValueError, 'candidate dimensions'):
            hd.verify(self.base, bad)

    def test_repatch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exact tested'):
            hd.patch(self.candidate)


if __name__ == '__main__':
    unittest.main()
