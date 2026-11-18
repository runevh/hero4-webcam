#!/bin/sh
# Diagnostic-only payload. No modules, network, CSI settings, or flash writes.
# Invoked by the mount hook with the SD mount directory as its sole argument.
card=$1
[ -n "$card" ] && [ -d "$card" ] && [ -f "$card/h4diag.enable" ] || exit 0
# Prevent repeated hooks from spawning concurrent collectors; lock lives in RAM.
mkdir /tmp/h4diag.lock 2>/dev/null || exit 0
trap 'rmdir /tmp/h4diag.lock' EXIT
umask 077
log="$card/h4diag.log"
# One bounded snapshot. Do not overwrite an earlier boot's evidence.
[ ! -e "$log" ] || exit 0
set -C
{
    echo 'HERO4 diagnostic snapshot v1 (no webcam or video-mode changes)'
    uname -a
    for f in /proc/version /proc/cpuinfo /proc/meminfo /proc/modules \
             /proc/mounts /proc/interrupts /proc/ambarella/uport; do
        echo "--- $f"
        [ ! -r "$f" ] || cat "$f"
    done
    echo '--- platform devices'
    ls /sys/bus/platform/devices
    echo '--- UDC devices'
    ls /sys/class/udc
    echo '--- recent kernel messages'
    dmesg | tail -n 200
    echo '--- snapshot complete'
} > "$log" 2>&1
