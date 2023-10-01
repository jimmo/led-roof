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

# MicroPython default:
_TIMING_SPEC = (400, 850, 800, 450)

# FastLED says
# WS2812: C_NS(250), C_NS(625), C_NS(375)
_TIMING_FASTLED_WS2812 = (250, 1000, 875, 375)
# SK6812: C_NS(300), C_NS(300), C_NS(600)
_TIMING_FASTLED_SK6812 = (300, 900, 600, 600)

_CMD_ALL_COLOR = 0
_CMD_STRIP_COLOR = 1
_CMD_STRIP_PIXEL = 2
_CMD_ALL_PIXEL = 3


for i, n in enumerate(config.layout):
    strips.append(neopixel.NeoPixel(pins[i], n, bpp=4, timing=_TIMING_FASTLED_SK6812))


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


def c(rgbw):
    for s in strips:
        s.fill(rgbw)
        s.write()



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
            if cmd == _CMD_ALL_COLOR and n == 9:
                for strip in strips:
                    strip.fill(packet_0_rgbw)
                for strip in strips:
                    strip.write()
            if cmd == _CMD_STRIP_COLOR and n == 10:
                strip = packet[5]
                if strip >= len(strips):
                    continue
                strips[strip].fill(packet_1_rgbw)
                strips[strip].write()
            if cmd == _CMD_STRIP_PIXEL:
                strip = packet[5]
                if strip >= len(strips):
                    continue
                if n != strips[strip].n * 4 + 6:
                    continue
                buf_tmp = strips[strip].buf
                strips[strip].buf = packet_2_data
                strips[strip].write()
                strips[strip].buf = buf_tmp
            if cmd == _CMD_ALL_PIXEL:
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
