# HERO4 Silver: 1080p video and audio over USB

Tested on one HERO4 Silver (HD4.01, official v5 firmware) and an Ubuntu-based
Linux laptop: 1920x1080 H.264 at 29.97 fps, 2.4 Mbps, with AAC from the built-in
microphone. A 20-second capture decoded 595 frames without errors; live playback
with audio was confirmed. See [the evidence](silver-hd-test.md).

This path uses USB Ethernet and an FFplay viewer. It does not expose a UVC
webcam or a system microphone device. Raspberry Pi, long drives, repeated cold
boots and full-sensor mode remain unverified. The firmware is experimental;
keep the official update and a charged battery available. Firmware updates
can leave a camera unusable if interrupted or incompatible.

## Prepare the update and runtime

Install Python 3, venv support, FFmpeg (including ffplay/ffprobe), and unzip.
From this checkout:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
mkdir -p firmware vendor build
curl -fL https://device-firmware.gp-static.com/12/HD4.01/camera_fw/05.00.00/UPDATE.zip -o firmware/UPDATE-silver.zip
.venv/bin/python scripts/prepare_silver_hd.py firmware/UPDATE-silver.zip build/silver-hd-v1
curl -fL https://github.com/victor-torres/hero4-webcam/releases/download/v1.3.0/hero4-webcam-v1.3.0.zip -o vendor/hero4-webcam-v1.3.0.zip
echo 'e07c05fb3f892ac17ed03279039155db855449a512cff6878f467ba4594d6674  vendor/hero4-webcam-v1.3.0.zip' | sha256sum -c -
unzip vendor/hero4-webcam-v1.3.0.zip -d vendor/release-v1.3.0
```

The builder requires the exact official Silver archive and writes only to a
new directory under build/. Do not use the original full Black patch or its
`h4.sh` startup script for this workflow. Firmware and release binaries stay
outside Git.

## Prepare the card

Mount the camera's FAT32 microSD using a card reader. Confirm its identity and
back up any existing UPDATE directory. Set `CARD` to its actual mount point:

```sh
CARD=/media/your-user/GOPRO
RUNTIME=vendor/release-v1.3.0/hero4-webcam-v1.3.0/h4
mkdir -p "$CARD/h4ether"
cp diagnostics/h4diag.sh "$CARD/h4diag-original.sh"
cp diagnostics/h4ether.sh "$CARD/h4ether.sh"
for name in usb-common udc-core ambarella_udc libcomposite h4_udc_dev g_ether; do
    cp "$RUNTIME/$name.ko" "$CARD/h4ether/"
done
cp "$RUNTIME/h4csi" "$CARD/h4ether/"
cat > "$CARD/h4diag.sh" <<'SH'
#!/bin/sh
card=$1
sh "$card/h4diag-original.sh" "$card"
[ ! -f "$card/h4ether.enable" ] || sh "$card/h4ether.sh" "$card"
SH
touch "$CARD/h4diag.enable"
cp -r build/silver-hd-v1/UPDATE "$CARD/"
sync
```

Do not create `h4ether.enable` until the update and first normal boot finish.
For an existing test card, temporarily rename that marker before installing.
Verify all three copied update files against `build/silver-hd-v1/verification.json`.
Safely unmount the card. With the camera off, USB disconnected and battery
well charged, insert the card and power on. Let the update finish without
interrupting its restarts. Confirm normal camera operation before proceeding.

Turn off, return the card to the reader, archive the fresh `h4diag.log`, and
confirm it ends in `snapshot complete`. Remove any remaining UPDATE directory
after successful installation. Create an empty `h4ether.enable` on the card,
sync and safely unmount it. Insert it into the powered-off camera, connect USB,
turn on and allow about 45 seconds. See [Ethernet details](silver-ether-test.md).

## Start the viewer

The expected USB device is 0525:a4a1, Ethernet Gadget. On the tested Linux host
the interface is `enx024834000002`; check `ip -br link` and use the actual name.
The camera address is 169.254.77.1. Assign the laptop 169.254.77.2 without a
gateway. If NetworkManager manages this interface, temporarily disable its
management so DHCP does not erase the test address:

```sh
sudo nmcli device set enx024834000002 managed no
sudo ip link set enx024834000002 up
sudo ip address replace 169.254.77.2/24 dev enx024834000002
ping -c 3 169.254.77.1
python3 scripts/silver_preview.py --configure
```

`--configure` keeps the camera's Linux side awake, enables preview keep-alives,
selects 1080 SuperView 30/Wide/default preview window at 2.4 Mbps, and rebuilds
the pipeline via photo/video mode switching. It does not start SD recording.
It uses the test's root shell on TCP 2323, restricted to the USB laptop address;
do not bridge or expose this link to other hosts. After configuring, subsequent
viewer restarts in the same camera session can omit `--configure`.

The viewer unwraps GoPro UDP packets and plays video plus audio. Closing the
window stops playback. When finished, restore network management with
`sudo nmcli device set enx024834000002 managed yes` if it was enabled before.
To disable camera-side USB takeover, remove `h4ether.enable` from the card,
then disconnect USB and remove/reinsert the battery for a cold boot.

## Offline regression checks

Tests use the official firmware and a reproducible diagnostic baseline locally:

```sh
mkdir -p firmware/v05.00.00
unzip firmware/UPDATE-silver.zip -d firmware/v05.00.00
.venv/bin/python scripts/prepare_diagnostics.py firmware/UPDATE-silver.zip build/silver-diagnostics-v1
.venv/bin/python -m unittest discover -s tests -v
```

Build directories must be new; retain existing verified outputs rather than
overwriting them. These tests validate patch scope and checksums, not hardware
safety on every Silver.
