# HERO4 Silver investigation and firmware comparison

Current status: **1080p29.97 video and AAC audio over USB Ethernet tested on
Silver with a Linux laptop**. Use the [Silver setup guide](silver-setup.md).
The smaller [entry-62 HD patch](silver-hd-test.md) is the tested path.
The original full webcam image described below remains untested on Silver;
these offline comparison notes are not its installation instructions.

The official v05.00.00 archives downloaded on 2026-11-18 were:

- Silver: https://device-firmware.gp-static.com/12/HD4.01/camera_fw/05.00.00/UPDATE.zip
- Black: https://device-firmware.gp-static.com/13/HD4.02/camera_fw/05.00.00/UPDATE.zip

The ZIP hashes differ, but all three extracted files are byte-identical:

| File | SHA-256 (both models) |
| --- | --- |
| camera_firmware.bin | f1be2cce699691cd1cd7754cad51b82fdb0c99c036a913bc11024454ec5e29c1 |
| camera_loaders.bin | d98d52b11e3730a66be64880ebc9207a04ad23f2f139e4db307b263225bc6566 |
| hd4_update.txt | 8954f40fd968a0bde7956061760ad561222b42fb76dca986e928c529f4c5cb85 |

All five firmware sections, including RTOS, DSP, kernel and root filesystem,
are identical. The upstream Black offsets therefore also match this Silver
download. No offsets or mode settings were guessed or changed for Silver.

The patcher now accepts the exact Silver ZIP hash only with
`--experimental-silver`. The stock firmware and author-tested output hash checks
remain intact. Example for **offline preparation**, not an SD card:

```sh
mkdir -p build/silver-candidate
.venv/bin/python scripts/patch_firmware.py --experimental-silver \
  /path/to/official-silver/UPDATE.zip build/silver-candidate
```

Verified locally: every input file matches Black; output matches upstream
`2c0eca6d6249bd2e91328f7fc49618d670ba961af42226322d2ff033058cf068`;
global and all section CRCs pass; Silver without the flag and altered ZIPs are
rejected; the original Black invocation still produces identical output.

## Remaining scope

- UVC/UAC modules and the upstream full-sensor mode remain untested on Silver.
- USB Ethernet and H.264 capture passed on Linux. Raspberry Pi operation,
  repeated power-cycle reliability and extended streaming still need tests.
- Keep the official Silver update available. Upstream describes restoration
  but has not tested it; USB recovery is experimental, not a guaranteed fallback.

The build-preparation script remains upstream's Black-only path. Since the
extracted firmware is identical, its Black input can be used for offline builds;
it must not be interpreted as evidence that the full Black UVC workflow is
supported on Silver.
