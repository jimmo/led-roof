import math
import random
import socket
import struct
import sys
import time

import asyncio
import rainbow


_CMD_ALL_COLOR = 0
_CMD_STRIP_COLOR = 1
_CMD_STRIP_PIXEL = 2
_CMD_ALL_PIXEL = 2

_CONTROLLER_DELAY = 0.015


class Controller:
    def __init__(self, ip, port):
        self._ip = ip
        self._port = port
        self._last = 0
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._q = []

    async def _wait(self):
        while True:
            dt = time.monotonic() - self._last
            if dt > _CONTROLLER_DELAY:
                break
            await asyncio.sleep(_CONTROLLER_DELAY - dt)
        self._last = time.monotonic()

    async def _send(self, buf):
        async def task():
            await self._wait()
            # print(self._ip, time.monotonic()-ttt)
            self._sock.sendto(buf, (self._ip, self._port))

        self._q.append(asyncio.create_task(task()))

    async def flush(self):
        await asyncio.gather(*self._q)
        self._q = []

    async def color(self, r, g, b, w=0):
        await self._send(b'roof' + struct.pack('BBBBB', _CMD_ALL_COLOR, r, g, b, w))

class Beam:
    def __init__(self, ctrl, idx, n):
        self._ctrl = ctrl
        self._idx = idx
        self._n = n

    async def color(self, r, g, b, w=0):
        await self._ctrl._send(b'roof' + struct.pack('BBBBBB', _CMD_STRIP_COLOR, self._idx, r, g, b, w))

    async def pixel(self, buf):
        # g r b w
        await self._ctrl._send(b'roof' + struct.pack('BB', _CMD_STRIP_PIXEL, self._idx) + buf)

    async def gradient(self, r, g, b, w=0):
        buf = bytearray()
        for i in range(self._n):
            buf += bytes((i*g//self._n,i*r//self._n,i*b//self._n,i*w//self._n))
        await self.pixel(buf)

    async def rainbow(self, offset=0):
        buf = bytearray()
        for i in range(self._n):
            r, g, b = rainbow.rainbow(offset + i * 2400 // self._n)
            buf += bytes((g, r, b, 0))
        await self.pixel(buf)


CONTROLLERS = [
    Controller('192.168.1.165', 6454),
    Controller('192.168.1.201', 6454),
    Controller('192.168.1.192', 6454),
    Controller('192.168.1.203', 6454),
]


BEAMS = [
    Beam(CONTROLLERS[0], 0, 180),
    Beam(CONTROLLERS[0], 1, 180),
    Beam(CONTROLLERS[0], 2, 180),
    Beam(CONTROLLERS[1], 0, 180),
    Beam(CONTROLLERS[1], 1, 180),
    Beam(CONTROLLERS[2], 0, 233),
    Beam(CONTROLLERS[2], 1, 233),
    Beam(CONTROLLERS[3], 0, 233),
    Beam(CONTROLLERS[3], 1, 233),
]


class Frame:
    def __init__(self, w, h):
        self._buf = bytearray(w*h*4)
        self._mv = memoryview(self._buf)
        self._w = w
        self._h = h

    def clear(self):
        for i in range(len(self._buf)):
            self._buf[i] = 0

    def fill(self, r, g, b, w=0):
        for i in range(0, len(self._buf), 4):
            self._buf[i] = g
            self._buf[i+1] = r
            self._buf[i+2] = b
            self._buf[i+3] = w

    def rect(self, x, y, w, h, r, g, b, ww=0):
        for xx in range(x, x+w):
            for yy in range(y, y+h):
                p = yy*self._w*4+xx*4
                self._buf[p] = g
                self._buf[p+1] = r
                self._buf[p+2] = b
                self._buf[p+3] = ww

    async def write(self):
        for i, s in enumerate(BEAMS):
            await s.pixel(self._mv[i*self._w*4:i*self._w*4+s._n*4])
        for c in CONTROLLERS:
            await c.flush()

    def pixel(self, x, y, r, g, b, w=0):
        p = y * self._w * 4 + x * 4
        self._buf[p] = g
        self._buf[p+1] = r
        self._buf[p+2] = b
        self._buf[p+3] = w


async def flush():
    for c in CONTROLLERS:
        await c.flush()


async def color(r,g,b,w=0):
    for c in CONTROLLERS:
        await c.color(r,g,b,w)
    await flush()


async def flash(r,g,b,w=0):
    await color(r,g,b,w)
    await color(0,0,0,0)


async def main():
    if len(sys.argv) < 2:
        return
    if sys.argv[1] == 'color':
        await color(*(int(x) for x in sys.argv[2:]))
    elif sys.argv[1] == 'rainbow':

        f = Frame(233, 9)
        i = 0
        while True:
            fx = 1+(1*math.cos(i/91)*math.cos(i/79))
            fy = 1+(1*math.sin(i/83)*math.sin(i/101))
            tt = i / 10
            for y in range(9):
                for x in range(233):
                    xx = x / 233
                    yy = y / 9
                    p1 = int(1200 * (math.sin(fy*math.pi*yy)+math.cos(fx*math.pi*xx) + 1))
                    r,g,b = rainbow.rainbow(p1+i)
                    f.pixel(x, y, r,g,b,0)
            await f.write()
            i += 0.1


if __name__ == '__main__':
    asyncio.run(main())
