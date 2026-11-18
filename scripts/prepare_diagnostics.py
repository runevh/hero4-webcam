#!/usr/bin/env python3
"""Prepare an OFFLINE diagnostic-only update from an exact stock HERO4 ZIP.

No RTOS/video, kernel, DSP, bootloader, USB driver or internal startup changes.
Only the SD mount script and its UBIFS inode are changed, plus firmware CRCs.
This still requires an untested firmware flash to run on a camera.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile
import zlib

from fwunpack import GLOBAL_HEADER_SIZE, SECTION_HEADER_SIZE, sections
from patch_firmware import (UPDATE_SHA256, SILVER_UPDATE_SHA256, STOCK_SHA256,
                            UPDATE_FILES, ORIGINAL_MARK, patch_ubifs, nodes,
                            DATA_NODE, INO_NODE, CH_SIZE, DATA_HDR)

DIAGNOSTIC_SCRIPT = b'''#!/bin/sh
if [ "$1" = mount ]; then
mount | grep -Fq "$3 on $2 type $4" || mount -t "$4" "$3" "$2"
if [ -f "$2/h4diag.enable" ] && [ -f "$2/h4diag.sh" ]; then
sh "$2/h4diag.sh" "$2" &
fi
fi
if [ "$1" = umount ]; then
umount "$2"
fi
'''
DIAGNOSTIC_SHA256 = '48ed74938b60051831b4814d45e07a5ba19f9a8f7dd321350fdd1853f2254bf0'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate(fw):
    if len(fw) < GLOBAL_HEADER_SIZE:
        raise ValueError('truncated firmware')
    if struct.unpack_from('<I', fw)[0] != zlib.crc32(fw[GLOBAL_HEADER_SIZE:]):
        raise ValueError('global CRC mismatch')
    entries = list(sections(fw))
    if len(entries) != 5:
        raise ValueError('expected five stock firmware sections')
    for s in entries:
        if zlib.crc32(fw[s['start']:s['start'] + s['length']]) != s['crc']:
            raise ValueError('section CRC mismatch')
    return entries


def verify_delta(stock, patched):
    """Reject differences outside the script's UBIFS nodes and two CRC fields."""
    if sha(stock) != STOCK_SHA256:
        raise ValueError('verification requires the exact stock firmware')
    before, after = validate(stock), validate(patched)
    if len(stock) != len(patched):
        raise ValueError('firmware length changed')
    ubi = before[4]
    start, length = ubi['start'], ubi['length']
    if stock[start:start + 4] != b'UBI#':
        raise ValueError('unexpected root filesystem')
    old_nodes = {p: (n, t) for p, n, t in nodes(stock[start:start + length])}
    new_nodes = {p: (n, t) for p, n, t in nodes(patched[start:start + length])}
    if old_nodes != new_nodes:
        raise ValueError('UBIFS node layout or CRC validation changed')
    changes = []
    allowed = bytearray(len(stock))
    allowed[:4] = b'\1' * 4
    allowed[start - SECTION_HEADER_SIZE:start - SECTION_HEADER_SIZE + 4] = b'\1' * 4
    for p, (n, t) in old_nodes.items():
        a, b = stock[start+p:start+p+n], patched[start+p:start+p+n]
        if a != b:
            changes.append((p, n, t, struct.unpack_from('<I', a, CH_SIZE)[0]))
            allowed[start+p:start+p+n] = b'\1' * n
    # The stock inode already has size=351, the exact padded data-node room;
    # rewriting it can therefore leave its bytes (including CRC) unchanged.
    if sorted(c[2] for c in changes) not in ([DATA_NODE], [INO_NODE, DATA_NODE]):
        raise ValueError('expected one script data node and at most its inode')
    if len({c[3] for c in changes}) != 1:
        raise ValueError('changed nodes do not belong to the same file')
    data_change = next(c for c in changes if c[2] == DATA_NODE)
    pos, length, _, inode = data_change
    expected = DIAGNOSTIC_SCRIPT + b'\n' * (length - DATA_HDR - len(DIAGNOSTIC_SCRIPT))
    if inode != 685 or patched[start+pos+DATA_HDR:start+pos+length] != expected:
        raise ValueError('changed data is not the expected diagnostic mount script')
    for offset, (a, b) in enumerate(zip(stock, patched)):
        if a != b and not allowed[offset]:
            raise ValueError(f'unexpected change at {offset:#x}')
    for i in range(4):
        s = before[i]
        lo, hi = s['hdr'], s['start'] + s['length']
        if stock[lo:hi] != patched[lo:hi]:
            raise ValueError(f'protected section {i} changed')
    return {'changed_ubifs_nodes': changes,
            'changed_bytes': sum(a != b for a, b in zip(stock, patched)),
            'protected_sections_0_through_3': 'byte-identical',
            'global_and_section_crcs': 'valid'}


def patch_diagnostics(stock):
    if sha(stock) != STOCK_SHA256:
        raise ValueError('not the exact supported stock firmware')
    entries = validate(stock)
    s = entries[4]
    start, end = s['start'], s['start'] + s['length']
    patched = bytearray(stock)
    patched[start:end] = patch_ubifs(stock[start:end], ORIGINAL_MARK,
                                   lambda original: DIAGNOSTIC_SCRIPT)
    struct.pack_into('<I', patched, start - SECTION_HEADER_SIZE,
                     zlib.crc32(patched[start:end]))
    struct.pack_into('<I', patched, 0, zlib.crc32(patched[GLOBAL_HEADER_SIZE:]))
    result = bytes(patched)
    report = verify_delta(stock, result)
    if sha(result) != DIAGNOSTIC_SHA256:
        raise ValueError('diagnostic output differs from the offline-verified candidate')
    report.update(stock_sha256=sha(stock), diagnostic_sha256=sha(result),
                  hardware_tested=False, webcam_enabled=False)
    return result, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stock_zip', type=Path)
    p.add_argument('output', type=Path, help='new offline build directory; never an SD mount')
    args = p.parse_args()
    # Keep output under this checkout's ignored build directory. No SD staging.
    build = Path(__file__).resolve().parents[1] / 'build'
    out = args.output.resolve()
    if build.resolve() not in out.parents or out.exists():
        p.error('output must be a NEW directory below this checkout/build')
    if sha(args.stock_zip.read_bytes()) not in {UPDATE_SHA256, SILVER_UPDATE_SHA256}:
        p.error('archive is not an exact supported official update')
    with zipfile.ZipFile(args.stock_zip) as z:
        files = {n: z.read(n) for n in UPDATE_FILES}
    files['camera_firmware.bin'], report = patch_diagnostics(files['camera_firmware.bin'])
    (out / 'UPDATE').mkdir(parents=True)
    for name, data in files.items():
        (out / 'UPDATE' / name).write_bytes(data)
    payload = Path(__file__).resolve().parents[1] / 'diagnostics' / 'h4diag.sh'
    (out / 'h4diag.sh').write_bytes(payload.read_bytes())
    # Deliberately omit h4diag.enable: running diagnostics is a later manual step.
    report['files_sha256'] = {n: sha(d) for n, d in files.items()}
    report['payload_sha256'] = sha(payload.read_bytes())
    (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
