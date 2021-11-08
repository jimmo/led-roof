import config
import connect

import machine
import network
import socket

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

def main():
    while True:
        packet = sock.recv(250*4*3+10)
        #print(packet)
        if not packet.startswith('roof') or len(packet) < 6:
            continue
        cmd = packet[4]
        if cmd == 0 and len(packet) == 9:
            r, g, b, w = packet[5:9]
            for strip in strips:
                strip.fill((r,g,b,w))
            for strip in strips:
                strip.write()
        if cmd == 1 and len(packet) == 10:
            n = packet[5]
            if n >= len(strips):
                continue
            r, g, b, w = packet[6:10]
            strips[n].fill((r,g,b,w))
            strips[n].write()
        if cmd == 2:
            n = packet[5]
            if n >= len(strips):
                continue
            if len(packet) != strips[n].n * 4 + 6:
                continue
            strips[n].buf[:] = packet[6:]
            strips[n].write()
        if cmd == 3:
            print(len(packet), sum(s.n for s in strips) * 4 + 5)
            if len(packet) != sum(s.n for s in strips) * 4 + 5:
                continue
            i = 5
            for s in strips:
                s.buf[:] = packet[i:i+s.n*4]
                i += s.n*4
                s.write()
main()
