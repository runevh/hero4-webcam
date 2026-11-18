# Experimental HERO4 Silver preparation

Status: offline firmware preparation verified; **not hardware-tested**. This is
not a claim of working Silver webcam support. No experimental update has been
copied to the user's SD card or flashed.

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

## Work remaining before claiming support

- Build or obtain and inspect the runtime modules and `h4.sh`/`h4` payload.
  The generated UPDATE folder alone is not a complete webcam installation.
- Validate startup and USB ownership on Silver hardware. Shared firmware can
  select different behavior based on the detected board; byte identity does
  not prove that Black's sensor/preview settings work on Silver.
- Test USB Ethernet first with stock preview modes before enabling the custom
  high-resolution preset and UVC/audio modules.
- Test Linux/Raspberry Pi enumeration and H.264 capture; upstream tested macOS
  only. Verify reconnects, power cycling and sustained streaming.
- Keep the official Silver update available. Upstream describes restoration
  but has not tested it; USB recovery is experimental, not a guaranteed fallback.

The build-preparation script remains upstream's Black-only path. Since the
extracted firmware is identical, its Black input can be used for offline builds;
it must not be interpreted as evidence of tested Silver hardware support.
