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
_CMD_ALL_PIXEL = 3

_CONTROLLER_DELAY = 0.015


class Controller:
    def __init__(self, hostname, port):
        self._ip = socket.gethostbyname(hostname)
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
            # print(buf)
            self._sock.sendto(buf, (self._ip, self._port))

        self._q.append(asyncio.create_task(task()))

    async def flush(self):
        await asyncio.gather(*self._q)
        self._q = []

    async def color(self, r, g, b, w=0):
        await self._send(b'roof' + struct.pack('BBBBB', _CMD_ALL_COLOR, r, g, b, w))


class Beam:
    def __init__(self, ctrl, idx, n, cal=None):
        self._ctrl = ctrl
        self._idx = idx
        self._n = n
        self._cal = cal

    async def flush(self):
        await self._ctrl.flush()

    async def color(self, r, g, b, w=0):
        if self._cal:
            r, g, b, w = self._cal(r, g, b, w)
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
    Controller('roof-1', 6454),
    Controller('roof-2', 6454),
    Controller('roof-3', 6454),
    Controller('roof-4', 6454),
]


def fix_beam_2(r, g, b, w):
    # if w and not g and not b:
    #     r += (w + 3) // 4
    return r, g, b, w


BEAMS = [
    Beam(CONTROLLERS[0], 0, 180),
    Beam(CONTROLLERS[0], 1, 180),
    Beam(CONTROLLERS[0], 2, 180, fix_beam_2),
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


async def color_raw(r,g,b,w=0):
    for c in CONTROLLERS:
       await c.color(r,g,b,w)
    await flush()

async def color(r,g,b,w=0):
    # for c in CONTROLLERS:
    #    await c.color(r,g,b,w)
    for i in BEAMS:
        await i.color(r,g,b,w)
        await i.flush()
    # await flush()

async def gradient(r,g,b,w=0):
    for i in BEAMS:
        await i.gradient(r,g,b,w)
    await flush()


async def flash(r,g,b,w=0):
    await color(r,g,b,w)
    await color(0,0,0,0)


async def main():
    if len(sys.argv) < 2:
        return
    if sys.argv[1] == 'color':
        await color(*(int(x) for x in sys.argv[2:]))
    if sys.argv[1] == 'gradient':
        await gradient(*(int(x) for x in sys.argv[2:]))
    elif sys.argv[1] == 'rainbow':
        f = Frame(233, 9)
        i = 0
        d = 20
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
                    f.pixel(x, y, r//d,g//d,b//d,0)
            await f.write()
            await asyncio.sleep(0.02)
            i += 1
    elif sys.argv[1] == 'sky':
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
                    p1 = int(20 * (math.sin(fy*math.pi*yy)+math.cos(fx*math.pi*xx) + 2))
                    f.pixel(x, y, 0, 0, p1 * 2, 80-p1//2)
            await f.write()
            await asyncio.sleep(1)
            i += 5
    elif sys.argv[1] == 'fill':
        f = Frame(233, 9)
        for y in range(9):
            for x in range(233):
                r,g,b = rainbow.rainbow(random.randrange(2400))
                f.pixel(x, y, r//20, g//20, b//20, 0)
        await f.write()
    elif sys.argv[1] == 'dots':
        f = Frame(233, 9)
        for y in range(9):
            for x in range(233):
                f.pixel(x, y, x % 4 == 0, x % 4 == 1, x % 4 == 2, x % 4 == 3)
        await f.write()
    elif sys.argv[1] == 'random':
        f = Frame(233, 9)
        q = []
        while True:
            q.append((random.randrange(233), random.randrange(9)))
            r,g,b = rainbow.rainbow(random.randrange(2400))
            f.pixel(q[-1][0], q[-1][1], r, g, b, 0)
            if len(q) > 20:
                d = q.pop(0)
                f.pixel(d[0], d[1], 0, 0, 0, 0)
            await f.write()
            await asyncio.sleep(0.1)
    elif sys.argv[1] == 'sparse':
        f = Frame(233, 9)
        n = 30
        b = 10
        for y in range(9):
            m = (((y % 2) * n // 2) + n // 4) % n
            for x in range(233):
                f.pixel(x, y, b * (x % n == m), 0, 0, b * (x % n == m))
        await f.write()
    elif sys.argv[1] == 'sparserainbow':
        f = Frame(233, 9)
        n = 60
        for y in range(9):
            m = (((y % 2) * n // 2) + n // 4) % n
            for x in range(233):
                r,g,b = rainbow.rainbow(random.randrange(2400))
                if (x % n == m):
                    f.pixel(x, y, r, g, b, 0)
        await f.write()
    elif sys.argv[1] == 'flash':
        i = 0
        while True:
            await color_raw(i % 4 == 0, i % 4 == 1, i % 4 == 2, i % 4 == 3)
            await asyncio.sleep(0.5)
            i += 1
    elif sys.argv[1] == 'sequence':
        i = 0
        while True:
            for beam in BEAMS:
                await beam.color(i % 4 == 0, i % 4 == 1, i % 4 == 2, i % 4 == 3)
                await beam.flush()
                i += 1
            await asyncio.sleep(0.2)
    elif sys.argv[1] == 'rainbowbeams':
        n = 0
        while True:
            for i, beam in enumerate(BEAMS):
                r, g, b = rainbow.rainbow((n + i * 2400 // len(BEAMS)) % 2400)
                d = 20
                await beam.color(r // d, g // d, b // d, 0)
                await beam.flush()
            n += 1
            # await asyncio.sleep(0.1)
    elif sys.argv[1] == 'on':
        for i in range(35):
            x = round(1.10**i)
            xw = round(1.17**i)-1
            await color_raw(x, x, x, xw)
        await color(x, x, x, xw)
    elif sys.argv[1] == 'off':
        for i in range(35):
            x = round(1.10**(34-i))-1
            xw = round(1.17**(34-i))-1
            await color_raw(x, x, x, xw)
        await color(x, x, x, xw)
    elif sys.argv[1] == 'interactive':
        r, g, b, w = 0, 0, 0, 0
        n = 1
        await color(r, g, b, w)
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            while True:
                c = sys.stdin.buffer.read(1)
                if c[0] == 3:
                    break
                if c[0] == ord('r'):
                    r -= n
                if c[0] == ord('R'):
                    r += n
                if c[0] == ord('g'):
                    g -= n
                if c[0] == ord('G'):
                    g += n
                if c[0] == ord('b'):
                    b -= n
                if c[0] == ord('B'):
                    b += n
                if c[0] == ord('w'):
                    w -= n
                if c[0] == ord('W'):
                    w += n
                if c[0] == ord('n'):
                    n -= 1
                if c[0] == ord('N'):
                    n += 1
                print(r, g, b, w, n, end="\r\n")
                await color(r, g, b, w)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    elif sys.argv[1] == 'test':
        i = 0
        while True:
            print(i)
            await BEAMS[2].color(0,0,0,i % 256)
            await BEAMS[2].flush()
            i += 1


if __name__ == '__main__':
    asyncio.run(main())
