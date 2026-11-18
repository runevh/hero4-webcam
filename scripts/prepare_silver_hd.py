#!/usr/bin/env python3
"""Build the tested diagnostic hook plus ONLY the entry-62 1080p preview patch.

Offline only. This exact patch passed a short 1080p test on one Silver.
No full-sensor mode, internal startup hook, or runtime payload is included.
"""
import argparse
import json
from pathlib import Path
import struct
import zipfile
import zlib

from prepare_diagnostics import patch_diagnostics, validate, sha, DIAGNOSTIC_SHA256
from patch_firmware import (SILVER_UPDATE_SHA256, UPDATE_FILES, RTOS_BASE,
                            IDLE_ADDR, DSP_SEC_SIZE, ENC_SEC_SIZE, patch_rtos_idle)
from fwunpack import GLOBAL_HEADER_SIZE, SECTION_HEADER_SIZE

HD_SHA256 = '66b31df9791bd08f3b789ae966b71cd261b077454b063771be9f2e2a900a82eb'


def crc(fw, section):
    start, end = section['start'], section['start'] + section['length']
    struct.pack_into('<I', fw, start - SECTION_HEADER_SIZE, zlib.crc32(fw[start:end]))
    struct.pack_into('<I', fw, 0, zlib.crc32(fw[GLOBAL_HEADER_SIZE:]))


def verify(diagnostic, candidate):
    if sha(diagnostic) != DIAGNOSTIC_SHA256:
        raise ValueError('requires the exact tested diagnostic image')
    before = validate(diagnostic)
    validate(candidate)
    if len(candidate) != len(diagnostic):
        raise ValueError('firmware length changed')
    rtos = before[1]
    restored = bytearray(candidate)
    fields = []
    # Independently verify the four intended integers, then reverse them.
    # The complete reverted image must match the tested diagnostic image.
    for offset in (DSP_SEC_SIZE, ENC_SEC_SIZE):
        pos = rtos['start'] + IDLE_ADDR - RTOS_BASE + offset
        if struct.unpack_from('<II', diagnostic, pos) != (848, 480):
            raise ValueError('unexpected original dimensions')
        if struct.unpack_from('<II', candidate, pos) != (1920, 1080):
            raise ValueError('unexpected candidate dimensions')
        fields.append({'file_offset': pos, 'before': [848, 480], 'after': [1920, 1080]})
        restored[pos:pos+8] = diagnostic[pos:pos+8]
    crc(restored, rtos)
    if bytes(restored) != diagnostic:
        raise ValueError('unexpected changes outside entry-62 dimensions and CRCs')
    if sha(candidate) != HD_SHA256:
        raise ValueError('candidate does not match the verified offline build')
    return {'dimensions': fields,
            'changed_bytes_from_diagnostic': sum(a != b for a, b in zip(diagnostic, candidate)),
            'diagnostic_sha256': sha(diagnostic), 'candidate_sha256': sha(candidate),
            'crcs': 'valid', 'reversed_patch_matches_tested_diagnostic': True,
            'silver_hd_hardware_tested': False}


def patch(diagnostic):
    if sha(diagnostic) != DIAGNOSTIC_SHA256:
        raise ValueError('requires the exact tested diagnostic image')
    rtos = validate(diagnostic)[1]
    start, end = rtos['start'], rtos['start'] + rtos['length']
    result = bytearray(diagnostic)
    result[start:end] = patch_rtos_idle(diagnostic[start:end])
    crc(result, rtos)
    result = bytes(result)
    return result, verify(diagnostic, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stock_zip', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    build = Path(__file__).resolve().parents[1] / 'build'
    out = args.output.resolve()
    if build.resolve() not in out.parents or out.exists():
        parser.error('output must be a new directory under checkout/build')
    if sha(args.stock_zip.read_bytes()) != SILVER_UPDATE_SHA256:
        parser.error('requires the exact official Silver v5 archive')
    with zipfile.ZipFile(args.stock_zip) as archive:
        files = {name: archive.read(name) for name in UPDATE_FILES}
    diagnostic, _ = patch_diagnostics(files['camera_firmware.bin'])
    files['camera_firmware.bin'], report = patch(diagnostic)
    report['files_sha256'] = {name: sha(data) for name, data in files.items()}
    (out / 'UPDATE').mkdir(parents=True)
    for name, data in files.items():
        (out / 'UPDATE' / name).write_bytes(data)
    (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
