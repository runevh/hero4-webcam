#!/usr/bin/env python3
"""Display the already-configured Silver stock preview over USB Ethernet."""
import http.client
import argparse
import socket
import subprocess
import threading
import time

CAMERA = '169.254.77.1'
HOST = '169.254.77.2'

def api(path):
    conn = http.client.HTTPConnection(CAMERA, timeout=5, source_address=(HOST, 0))
    try:
        conn.request('GET', '/gp/gpControl' + path)
        response = conn.getresponse()
        response.read()
        if response.status != 200:
            raise RuntimeError('HTTP ' + str(response.status))
    finally:
        conn.close()

def configure():
    """Reapply the tested HD preview settings after a camera cold boot."""
    command = (b'/tmp/h4ether/h4csi set 0x43 1 && '
               b'(iptables -C INPUT -i usb0 -s 169.254.77.2 -p udp --dport 8554 -j ACCEPT '
               b'|| iptables -I INPUT -i usb0 -s 169.254.77.2 -p udp --dport 8554 -j ACCEPT) '
               b'&& echo SILVER_READY; exit\n')
    with socket.create_connection((CAMERA, 2323), timeout=8) as shell:
        shell.settimeout(8)
        shell.sendall(command)
        response = bytearray()
        while True:
            data = shell.recv(4096)
            if not data:
                break
            response.extend(data)
        if b'SILVER_READY' not in response:
            raise RuntimeError('Camera setup failed: ' + response.decode(errors='replace'))
    for path in ('/setting/3/8', '/setting/2/8', '/setting/4/0',
                 '/setting/64/0', '/setting/62/2400000', '/command/mode?p=1'):
        api(path)
    time.sleep(3)
    api('/command/mode?p=0')
    time.sleep(3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configure', action='store_true',
                        help='apply tested SuperView 30 settings after boot (requires USB shell)')
    args = parser.parse_args()
    if args.configure:
        configure()
    stop = threading.Event()
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4000000)
    rx.bind((HOST, 8554))
    rx.settimeout(1)
    player = subprocess.Popen(['ffplay', '-hide_banner', '-loglevel', 'warning',
        '-fflags', 'nobuffer', '-flags', 'low_delay', '-framedrop',
        '-probesize', '100000', '-analyzeduration', '1000000',
        '-window_title', 'GoPro Silver — live USB preview', '-x', '864', '-y', '480',
        '-f', 'mpegts', '-i', 'pipe:0'], stdin=subprocess.PIPE)
    def maintain():
        while not stop.is_set():
            try:
                rx.sendto(b'_GPHD_:0:0:2:0.000000\n', (CAMERA, 8554))
                api('/status')
            except OSError as exc:
                print('Keep-alive:', exc, flush=True)
            stop.wait(2.5)
    try:
        api('/execute?p1=gpStream&a1=proto_v2&c1=restart')
        threading.Thread(target=maintain, daemon=True).start()
        last = time.monotonic()
        while player.poll() is None:
            try:
                data, addr = rx.recvfrom(65536)
            except socket.timeout:
                if time.monotonic() - last > 30:
                    raise RuntimeError('No preview packets for 30 seconds')
                continue
            n = int.from_bytes(data[10:12], 'big') if len(data) >= 12 else 0
            if addr[0] == CAMERA and n and n % 188 == 0 and 12+n <= len(data) and data[12] == 0x47:
                player.stdin.write(data[12:12+n])
                player.stdin.flush()
                last = time.monotonic()
    except BrokenPipeError:
        pass
    finally:
        stop.set()
        rx.close()
        try:
            player.stdin.close()
        except BrokenPipeError:
            pass  # Closing the player window is a normal stop.
        if player.poll() is None:
            player.terminate()
        player.wait()

if __name__ == '__main__':
    main()
