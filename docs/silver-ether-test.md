# Silver USB Ethernet hardware test

Requires the successfully tested minimal diagnostic firmware hook. This test
replaces only the card's `h4diag.sh` with a wrapper that runs the original
collector and then `h4ether.sh` when `h4ether.enable` exists. Both the original
firmware-hook gate `h4diag.enable` and the new gate must be present.

The staged payload uses six checksum-verified v1.3.0 release modules:
usb-common, udc-core, ambarella_udc (without microphone patches), libcomposite,
h4_udc_dev and g_ether. Static compatibility checks passed; Silver hardware
USB enumeration has now passed the first hardware test below. h4csi is copied to RAM for later inspection
but is not executed by the startup script. No video modes are changed.

The camera receives 169.254.77.1/24; assign 169.254.77.2/24 to the laptop's
new USB interface without changing its default route. The test permits ICMP
and TCP 2323 from that laptop address over usb0. A passwordless root shell
binds only to 169.254.77.1:2323. No listener binds to Wi-Fi. Do not bridge the
USB interface or expose it to other hosts.

Each setup command is logged and failures stop subsequent setup. Logs remain
in `/tmp/h4ether/test.log`, with checkpoint copies to `h4ether.log` on the card
when the card is accessible. The USB transition may interrupt card access;
the last card checkpoint can therefore precede the actual failure.

Power off before inserting/removing the card. Start with the USB cable
connected and allow about 30 seconds. Check host enumeration, then ping and
read-only shell commands before attempting any preview or camera controls.
The existing collector log is preserved and is not a new test result.

To disable: power off, remove `h4ether.enable` using the laptop's card reader,
then cold boot (disconnect USB and briefly remove/reinsert the battery).
No additional firmware update or internal installation is staged. Removing
the marker does not unload modules in an already-running Linux session.

## First hardware result (2026-11-18)

All six modules loaded, usb0 received its address, firewall commands succeeded,
and the bound shell process survived its startup check. The camera logged
`high-speed config #1: CDC Ethernet (ECM)`. The host kernel independently
registered USB 0525:a4a1 as Ethernet Gadget with cdc_ether and interface
enx024834000002 at 12:22:24. It remained registered until unplugged at 12:23:46.
The initial host check preceded this transition and incorrectly suggested the
test had not succeeded. No payload change was needed.

Private card-log
SHA256: `1723b18aa58ffd5a5609ac7e73dafb29cbb42eb30f8924ad64e4a9f727666bf3`.

On the next connection the laptop was assigned 169.254.77.2/24 on the USB
interface. All three pings returned (0% loss, 0.389–0.667 ms). TCP 2323 shell
access succeeded: uname, uptime and ifconfig returned normally. Read-only
`h4csi get 9` and `h4csi get 0x43` returned zero (lengths 4 and 1 respectively).
The shell transcript is retained locally in ignored `build/ether-shell-check.log`.
Subsequent preview tests passed over USB. Setting CSI key 0x43 to 1 kept Linux
awake while leaving USB file-access mode. The stock preview yielded 432x240
H.264 at 30000/1001 fps plus AAC: 595 frames decoded from a 20-second sample,
without decoder errors. `scripts/silver_preview.py` displays the stream and
strips the GoPro datagram header/padding before passing MPEG-TS to ffplay.

The advertised 480 window (setting 64=4), even after a photo/video rebuild,
still produced 432x240 in 1080 Wide 60 mode. The bitrate changed to 2.4 Mbps.
Switching to 1080 SuperView 30 (2=8, 3=8, 4=0), default window (64=0), and
rebuilding via photo/video mode produced **848x480 at 30000/1001 fps**.
The 20-second sample contained 5,877 valid datagrams and 596 decoded frames,
with zero malformed datagrams or FFmpeg decoder errors. This configuration
was left active with the live preview running. No further firmware flash or
recording to the card was needed. Captures remain local under
`captures/silver-quality/`. Higher resolutions and sustained stability remain
unverified.

On this laptop NetworkManager's DHCP attempt removed the manually assigned
USB address. For the test the USB interface was temporarily marked unmanaged
and assigned 169.254.77.2/24 again; no default route was changed. Restore
management when done with `nmcli device set enx024834000002 managed yes`.
