#!/bin/sh
# Read-only host inventory. Does not load modules, configure USB/network or record.
printf '\n--- Host ---\n'
uname -a
if [ -r /proc/device-tree/model ]; then tr '\000' '\n' < /proc/device-tree/model; fi
printf '\n--- Tools ---\n'
for tool in ffmpeg ffprobe v4l2-ctl lsusb modinfo; do command -v "$tool" || true; done
printf '\n--- UVC driver availability ---\n'
if command -v modinfo >/dev/null 2>&1; then modinfo uvcvideo 2>&1; fi
printf '\n--- Connected USB devices ---\n'
if command -v lsusb >/dev/null 2>&1; then lsusb; fi
printf '\n--- Video devices ---\n'
if command -v v4l2-ctl >/dev/null 2>&1; then v4l2-ctl --list-devices; fi
printf '\n--- Decoder availability ---\n'
if command -v ffmpeg >/dev/null 2>&1; then ffmpeg -hide_banner -decoders 2>/dev/null | grep -i h264; fi
printf '\nThis inventory does not verify a GoPro stream or sustained performance.\n'
