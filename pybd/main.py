import config
import connect

import machine
import network
import socket
import select

import gc

import neopixel


pins = [machine.Pin.board.X8, machine.Pin.board.Y8, machine.Pin.board.Y4]
strips = []

for i, n in enumerate(config.layout):
    strips.append(neopixel.NeoPixel(pins[i], n, bpp=4))


try:
    machine.Pin.board.EN_3V3.init(mode=machine.Pin.OUT)
    machine.Pin.board.EN_3V3.value(1)
    print("3v3 enabled")
except:
    pass


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
print("Listening on", network.WLAN(network.STA_IF).ifconfig()[0], config.port)
sock.bind((network.WLAN(network.STA_IF).ifconfig()[0], config.port))
sock.setblocking(False)


def main():
    p = select.poll()
    p.register(sock, select.POLLIN)
    buf = bytearray(250*4*3+10)
    packet = memoryview(buf)
    packet_header = packet[0:4]
    packet_0_rgbw = packet[5:9]
    packet_1_rgbw = packet[6:10]
    packet_2_data = packet[6:]

    packet_3_data = []
    i = 5
    for s in strips:
        packet_3_data.append(packet[i:i+s.n*4])

    mf = gc.mem_free()

    while True:
        connect.reconnect()

        for _, _ in p.ipoll(1000):
            n = sock.readinto(buf)
            if packet_header != b'roof' or n < 6:
                continue
            cmd = packet[4]
            if cmd == 0 and n == 9:
                for strip in strips:
                    strip.fill(packet_0_rgbw)
                for strip in strips:
                    strip.write()
            if cmd == 1 and n == 10:
                strip = packet[5]
                if strip >= len(strips):
                    continue
                strips[strip].fill(packet_1_rgbw)
                strips[strip].write()
            if cmd == 2:
                strip = packet[5]
                if strip >= len(strips):
                    continue
                if n != strips[strip].n * 4 + 6:
                    continue
                buf_tmp = strips[strip].buf
                strips[strip].buf = packet_2_data
                strips[strip].write()
                strips[strip].buf = buf_tmp
            if cmd == 3:
                if n != sum(s.n for s in strips) * 4 + 5:
                    continue
                i = 0
                for s in strips:
                    buf_tmp = s.buf
                    s.buf = packet_3_data[i]
                    s.write()
                    s.buf = buf_tmp
                    i += 1

main()
