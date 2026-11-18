# Silver validation and staged test plan

## Status (2026-11-18)

**Offline checks and standalone Linux RAM boot passed. No firmware flash or
webcam streaming test has been performed. This is not a safety certification
or working-Silver webcam claim.**

The camera was previously identified by its own `MISC/version.txt` as HERO4
Silver, HD4.01.05.00.00. The user subsequently chose the laptop as the test host;
Pi hardware testing is out of the current scope.

## Hardware result: standalone RAM boot

On 2026-11-18 the original USB cable caused descriptor error -71. Replacing
the cable restored normal GoPro USB enumeration (`2672:000d`). With the battery
and SD removed, holding Shutter while plugging USB in exposed command mode
`4255:0009` (Amba A7S).

With explicit user authorization, the locally built `gpboot --h4s-linux` was
run with upstream's `zImage-h4s`, `initrd-h4s.lzma` and `evilcortex/evilcortex`.
DDR initialization and its test passed; all uploads completed and gpboot exited
successfully. No `--h4-recovery` or `--h4-raw` command was executed.

The camera re-enumerated as `0525:a4a2`, RNDIS/Ethernet Gadget, with manufacturer
`Linux 3.8.0 with ambarella_udc`. After assigning a temporary 10.9.9.2/24 address
to only the laptop's new USB interface (no default-route/Wi-Fi change), a telnet
connection to 10.9.9.1 read the following:

```text
Linux camera 3.8.0 #314 SMP PREEMPT Sat Jul 11 01:10:43 PDT 2015 armv7l GNU/Linux
mem=500M@0x00500000 root=/dev/ram0 init=/bin/sh console=tty0 initrd=0x07000000,0x00097cf7
```

The mount list contained only rootfs, proc, tmpfs, sysfs, devpts and debugfs.
No SD or internal-flash filesystem was mounted; `/proc/mtd` listed no devices.
There was no `autoreflash` boot parameter. Commands sent over the shell were
only `echo`, `uname` and `cat` of proc files. Local evidence is saved in ignored
`build/ram-boot.log` and `build/ram-boot-diagnostics.log`.

This demonstrates command-mode access, standalone Linux RAM execution and a
working USB network/shell on this Silver. It does not demonstrate successful
flash restoration, stock dual-OS USB takeover, camera encoding or UVC video.
This standalone SMP kernel differs from the normal non-SMP camera kernel: do
not load the stock-targeted webcam modules into this diagnostic environment.
Returning to stock operation requires unplugging USB and reinserting the
battery, then normal power-on; that post-test reboot is not yet verified.

## Diagnostic-only candidate

`scripts/prepare_diagnostics.py` accepts only the exact official Black/Silver
v05.00 ZIP hashes and exact stock firmware hash. Output is restricted to a new
directory under the ignored local `build/` directory. It never installs to SD.

The candidate's only filesystem change is the SD mount script. It runs
`h4diag.sh` only when `h4diag.enable` exists on that card. It does **not** invoke
`h4.sh`, the webcam, any driver modules, a remote shell or the internal-install
path. The opt-in marker is deliberately absent from the generated package.

The payload takes one bounded diagnostic snapshot into `h4diag.log` on SD. It
reads kernel/CPU/memory/module/mount/USB information and the last 200 dmesg lines.
Its lock is in RAM; it does not overwrite an earlier log. It does not change
camera settings, configure networking or write to internal storage. The
firmware installation itself still writes flash and remains untested.

Verified:

- Candidate SHA-256:
  `48ed74938b60051831b4814d45e07a5ba19f9a8f7dd321350fdd1853f2254bf0`.
- 336 changed firmware bytes, confined to one UBIFS data node plus the
  filesystem-section/global CRC fields. The inode's padded size was already
  correct, so its bytes did not change.
- Sections 0–3 and headers (including RTOS/video tables, DSP and kernel) are
  byte-identical; the separate loader file and update instructions are stock.
  This does not mean the updater will refrain from rewriting identical sections.
- Global and every section CRC verified; UBIFS node layout/CRCs verified.
- Independently extracted both root filesystems and compared 755 regular files
  and symlinks: only `usr/local/share/script/sd_script.sh` differs. Extraction
  cannot create device nodes as an ordinary user; those and directory metadata
  are not covered by this file comparison. The byte-level checks cover the UBI
  image itself.
- Six regression tests cover expected output, protected sections, damaged input,
  repatching, unexpected RTOS changes even with recomputed CRCs, and the opt-in
  hook. Shell scripts pass `sh -n`.

Reproduce after extracting the official firmware:

```sh
.venv/bin/python scripts/prepare_diagnostics.py /path/to/official/UPDATE.zip build/silver-diagnostics-v1
.venv/bin/python -m unittest discover -s tests -v
```

## Runtime compatibility

Inspected upstream release v1.3.0, built from commit `e6d150e`.
ZIP SHA-256, matched against GitHub's release digest:
`e07c05fb3f892ac17ed03279039155db855449a512cff6878f467ba4594d6674`.
No webcam-release ARM binaries were executed on this host or the camera.
The separate recovery project's standalone Linux images were later RAM-booted
as recorded above.

`scripts/check_runtime.py` checked all nine modules and both userspace programs:

- ARM architecture; module vermagic matches stock ambafs:
  `3.8.0 preempt mod_unload ARMv7`.
- No missing undefined-symbol **names** after checking kernel strings and
  module exports. Name presence is not proof of a kernel export, ABI, structure
  layout, loading order, or hardware compatibility.
- `h4csi` and `h4uvc` use the ARM soft-float ABI; required shared libraries and
  GLIBC version names are available in the extracted stock rootfs. This is a
  necessary static check, not a dynamic-loader test.
- Kernel config permits modules without modversions/signatures and includes
  the relevant Ambarella USB platform support. Silver and Black kernel bytes
  and embedded configs are identical.

The runtime has **not been rebuilt from source here**: Docker/Podman and the ARM
cross-compiler are absent. Checks used the checksum-verified upstream build.
The native recovery tool was compiled separately with local Ubuntu libusb
headers, without installing system packages. It was later used for the
authorized RAM boot recorded above.

## Raspberry Pi host

The Raspberry Pi `rpi-6.12.y` kernel's UVC driver parses frame-based formats, and
its common UVC table maps this project's exact H264 GUID to `V4L2_PIX_FMT_H264`:

- https://github.com/raspberrypi/linux/blob/rpi-6.12.y/drivers/media/usb/uvc/uvc_driver.c
- https://github.com/raspberrypi/linux/blob/rpi-6.12.y/include/linux/usb/uvc.h
- https://github.com/raspberrypi/linux/blob/rpi-6.12.y/drivers/media/common/uvc.c

This establishes a plausible Linux path, not compatibility with the user's
unknown Pi kernel. `scripts/pi_preflight.sh` performs a read-only inventory of
the actual host when access is available. FFmpeg can be used to inspect/copy an
H.264 stream without re-encoding; no claim of sustained frame rate is made yet.

## RAM boot and recovery findings

Inspected `evilwombat/gopro-usb-tools` commit
`d1aa2bdf33710c79613a8cc461deebd88bac7ef9` and its bundled initramfs.

- `gpboot --h4s-linux` explicitly targets Silver and boots standalone Linux in
  RAM. It initializes DDR/peripherals/NAND-controller registers. It is not a
  passive test and not guaranteed risk-free.
- HERO4 command-mode USB ID is `4255:0009` in the tool source. The author's
  HERO4-specific guide documents: remove battery/unplug USB; hold Shutter while
  connecting USB, then release Shutter. This differs from the old-model README
  sequence. For our enumeration-only test remove the SD too; do not prepare a
  recovery card. This procedure has now been verified on this camera.
- Standalone Linux leaves the ARM11 spinning and does not run GoPro's normal
  RTOS/encoder/IPC environment. It can establish recovery/USB access but cannot
  validate this webcam runtime or a full normal-camera boot from RAM.
- `--h4-raw` is a raw load/jump primitive, not a ready-made verified boot of the
  complete patched firmware. Do not pass the multi-section update to it.
- `--h4-recovery` explicitly sets `autoreflash` and rewrites NAND; **never use
  this as a preflight test**.
- Even the normal RAM initramfs mounts SD read-only and runs `/card/init.sh`.
  Read-only SD does not constrain that script's access to internal storage.
  Any later standalone RAM test must remove the SD entirely and review the
  exact boot artifacts/command first.
- Stock reflash and USB recovery remain unproven on this particular camera.
  Merely compiling the recovery tool is not evidence that recovery will work.

Source: https://github.com/evilwombat/gopro-usb-tools/blob/master/gpboot.c

Author's HERO4 guide (also contains an owner-confirmed Silver recovery, not a
guarantee for this camera):
https://www.tapatalk.com/groups/goprouser/how-to-reflash-firmware-onto-a-bricked-hero4-camera-over-usb-t23149.html

## Hardware stages still required

1. Identify Pi model/kernel and run the read-only host preflight. Confirm a
   healthy camera battery and record baseline camera behavior. Do not copy an
   UPDATE folder to the card during these checks.
2. Check command-mode enumeration read-only using the author's HERO4 entry
   method, then assess a standalone RAM boot with the SD removed. A RAM boot
   tests a recovery route only, not the complete webcam firmware.
3. Review the minimal diagnostic image and its exact diff before any flash.
   After an explicitly agreed hardware test, check camera startup, normal
   recording/playback and the bounded diagnostic log. Remove UPDATE after a
   successful install; retain an untouched official recovery update separately.
4. Only after diagnostics pass, prepare a separate opt-in USB-Ethernet test.
   No internal installation, no shell exposed to Wi-Fi, no video-table edits.
   Test the existing low-resolution preview over Ethernet first.
5. Do **not** start the upstream UVC service with stock low-resolution preview:
   it advertises 1080p/720p and forces a high-resolution preset. Either validate
   the higher-resolution camera modes first or implement matching descriptors
   and runtime settings for a low-resolution UVC test.
6. Once the format matches, test UVC video without microphone first on the Pi:
   enumeration, actual decoded frame dimensions, reconnects, repeated cold
   boots, power loss/restart and a sustained capture. Add audio and higher
   resolution only after stable video. Stop on freezes, encoder errors or
   thermal/power problems.

Command-mode enumeration and standalone RAM boot are now verified. The stock
camera diagnostics flash and every webcam-streaming stage remain untested.
Firmware/output CRCs cannot certify hardware compatibility, thermal stability
or recoverability.
