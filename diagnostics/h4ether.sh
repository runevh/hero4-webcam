#!/bin/sh
# Experimental Silver USB ownership test, invoked through the diagnostic hook.
# Card-only installation. No flash writes or camera mode/settings commands.
card=$1
[ -n "$card" ] && [ -f "$card/h4ether.enable" ] || exit 0
mkdir /tmp/h4ether.lock 2>/dev/null || exit 0
# Keep the lock for this Linux session: do not take over USB twice.
umask 077
ram=/tmp/h4ether
mkdir -p "$ram" || exit 1
log=$ram/test.log
exec > "$log" 2>&1
save() { cp "$log" "$card/h4ether.log" && sync; }
fail() { echo "STOP: $*; power off and remove h4ether.enable before retrying"; dmesg | tail -60; save; exit 1; }
step() {
    echo "+ $*"
    save
    "$@"
    rc=$?
    echo "exit=$rc"
    [ "$rc" = 0 ] || fail "$*"
    save
}
echo 'HERO4 Silver USB Ethernet test v1'
uname -a
modules='usb-common udc-core ambarella_udc libcomposite h4_udc_dev g_ether'
for m in $modules; do
    cp "$card/h4ether/$m.ko" "$ram/" || fail "copy $m"
done
# Copy tools before USB ownership can make the card unavailable to Linux.
cp "$card/h4ether/h4csi" "$ram/" || fail 'copy h4csi'
chmod 700 "$ram/h4csi"
command -v tcpsvd || fail 'tcpsvd unavailable'
sleep 15
for m in usb-common udc-core ambarella_udc libcomposite h4_udc_dev; do
    step insmod "$ram/$m.ko"
done
step insmod "$ram/g_ether.ko" dev_addr=02:48:34:00:00:01 host_addr=02:48:34:00:00:02
step ifconfig usb0 169.254.77.1 netmask 255.255.255.0 up
# Restrict new access to the directly connected laptop, never Wi-Fi.
step iptables -I INPUT -i usb0 -s 169.254.77.2 -p icmp -j ACCEPT
step iptables -I INPUT -i usb0 -s 169.254.77.2 -p tcp --dport 2323 -j ACCEPT
step iptables -I OUTPUT -o usb0 -d 169.254.77.2 -j ACCEPT
tcpsvd -v 169.254.77.1 2323 sh -c 'exec sh 2>&1' > "$ram/shell.log" 2>&1 &
shell_pid=$!
sleep 1
kill -0 "$shell_pid" || fail 'USB shell did not start'
echo 'READY: USB 169.254.77.1/24, laptop 169.254.77.2, shell TCP 2323'
ifconfig usb0
cat /proc/modules
dmesg | tail -60
save
