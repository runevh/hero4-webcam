# Minimal Silver 1080p preview candidate

The Silver has demonstrated stable decoding for short 848x480, 29.97 fps
preview samples over USB Ethernet in 1080 SuperView 30 mode. This candidate
raises only the secondary DSP buffer and encoder dimensions of RTOS entry 62
from 848x480 to 1920x1080. The first Silver hardware test passed; see the result
below. Successful checksums alone do not establish hardware compatibility.

Build offline from the exact official Silver v5 archive:

```sh
.venv/bin/python scripts/prepare_silver_hd.py /path/to/UPDATE.zip build/silver-hd-v1
.venv/bin/python -m unittest discover -s tests -v
```

The build retains the already-tested diagnostic mount hook, which launches
the card's wrapper and USB test. It does not include the upstream full-sensor
entry-63 patch, 2.7K SuperView remapping, or internal startup installation.
Root filesystem, kernel, DSP firmware, loader file and all other RTOS bytes
remain unchanged relative to the tested diagnostic candidate. The updater
may nevertheless rewrite unchanged flash sections when installing the package.

The candidate differs from that diagnostic image by 16 bytes: four dimension
integers (in two pairs) plus section/global CRC changes. The verifier reverses
the dimension edits, recalculates CRCs and requires the entire resulting image
to equal the pinned diagnostic image. Regression tests reject unrelated RTOS
edits even with valid recalculated CRCs, incorrect dimensions and repatching.

Candidate firmware SHA256:
`66b31df9791bd08f3b789ae966b71cd261b077454b063771be9f2e2a900a82eb`.

Stage only this candidate's UPDATE directory after verifying the card identity.
Retain the working diagnostic firmware and official stock update on the laptop.
Temporarily disable the card's h4ether.enable marker for the update and first
normal boot. After normal operation is confirmed, restore the marker and test
USB preview in 1080 SuperView 30, default preview window. Measure actual
decoded dimensions, errors and sustained stability before claiming HD support.
No additional high-resolution or full-sensor patch should be combined with this
first test.

## First hardware result: passed (2026-11-18)

After installing the candidate, the user confirmed normal camera startup.
A fresh completed diagnostic log was archived locally and the Ethernet marker
was restored. USB networking and shell access worked on the next connection.
With Linux kept awake via CSI 0x43=1, the camera was configured to 1080
SuperView 30, Wide, default preview window, and 2.4 Mbps preview bitrate;
photo/video mode switching rebuilt the preview pipeline.

The USB sample decoded as **1920x1080 H.264, 30000/1001 fps**: 595 frames
from a 20-second capture, 5,859 valid datagrams, no malformed datagrams and
no ffprobe/FFmpeg decoding errors. A decoded frame was visually inspected.
The live preview was restarted successfully. Local evidence is retained in
`captures/silver-hd-first/` (stream, status snapshots, ffprobe report and frame).

This verifies the minimal entry-62 patch on this Silver for a short test.
It does not establish extended thermal stability, repeated power-cycle
reliability, higher bitrates, full-sensor readout or UVC webcam operation.
The offline build report's silver_hd_hardware_tested flag conservatively refers
to the newly built artifact; it does not certify another physical camera.
AAC playback was subsequently enabled in the viewer and confirmed by the user.
