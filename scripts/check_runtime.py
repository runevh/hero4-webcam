#!/usr/bin/env python3
"""Read-only ARM module and userspace compatibility checks; never loads code.

Symbol-name presence is a necessary check, not proof of exported-symbol ABI or
runtime compatibility. Use the exact upstream release and extracted stock rootfs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def elf(path, *args):
    return subprocess.check_output(['readelf', *args, str(path)], text=True)


def symbols(path):
    result = []
    for line in elf(path, '-Ws').splitlines():
        fields = line.split()
        if len(fields) >= 8 and fields[0].rstrip(':').isdigit():
            result.append((fields[6], fields[7], fields[4]))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runtime', type=Path)
    p.add_argument('stock_rootfs', type=Path)
    p.add_argument('stock_kernel', type=Path)
    args = p.parse_args()
    stock_module = next(args.stock_rootfs.rglob('ambafs.ko'))
    vermagic = re.search(r'vermagic=(.*)', elf(stock_module, '-p', '.modinfo')).group(1).strip()
    modules = sorted(args.runtime.glob('*.ko'))
    if len(modules) != 9:
        p.error('expected all nine upstream runtime modules')
    exports = set()
    for m in modules:
        exports.update(n.removeprefix('__ksymtab_') for ndx, n, _ in symbols(m)
                       if ndx != 'UND' and n.startswith('__ksymtab_'))
    kernel = args.stock_kernel.read_bytes()
    report = {'scope': 'static checks only; does not establish hardware support',
              'stock_vermagic': vermagic, 'modules': {}, 'userspace': {}}
    failed = False
    for m in modules:
        header = elf(m, '-h')
        actual = re.search(r'vermagic=(.*)', elf(m, '-p', '.modinfo')).group(1).strip()
        undefined = {n for ndx, n, bind in symbols(m) if ndx == 'UND' and bind != 'WEAK'}
        missing = sorted(n for n in undefined if n not in exports and
                         b'\0' + n.encode() + b'\0' not in kernel)
        ok = actual == vermagic and 'Machine:                           ARM' in header and not missing
        failed |= not ok
        report['modules'][m.name] = {'static_checks_pass': ok, 'vermagic': actual,
            'undefined_symbol_count': len(undefined), 'missing_symbol_names': missing,
            'sha256': hashlib.sha256(m.read_bytes()).hexdigest()}
    for name in ('h4csi', 'h4uvc'):
        binary = args.runtime / name
        needed = re.findall(r'Shared library: \[(.*?)\]', elf(binary, '-d'))
        versions = set(re.findall(r'Name: (GLIBC_[\d.]+)', elf(binary, '-V')))
        libs = {}
        for lib in needed:
            matches = [args.stock_rootfs / 'lib' / lib, args.stock_rootfs / 'usr/lib' / lib]
            libs[lib] = next((str(f) for f in matches if f.is_file()), None)
        supplied = set()
        for path in libs.values():
            if path:
                supplied.update(re.findall(r'Name: (GLIBC_[\d.]+)', elf(Path(path), '-V')))
        missing_versions = sorted(versions - supplied)
        header = elf(binary, '-h')
        ok = all(libs.values()) and not missing_versions and 'soft-float ABI' in header and 'Machine:                           ARM' in header
        failed |= not ok
        report['userspace'][name] = {'static_checks_pass': ok, 'needed_libraries': libs,
                                    'missing_glibc_versions': missing_versions}
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
