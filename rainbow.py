import math

def rainbow(i):
    spos = math.sin(math.pi/6)
    i = (i % 2400)/2400
    tpi = 2 * math.pi * i
    r = 150 * (spos + max(-spos, math.sin(tpi)))
    g = 150 * (spos + max(-spos, math.sin(tpi + 2*math.pi/3)))
    b = 150 * (spos + max(-spos, math.sin(tpi + 4*math.pi/3)))
    return int(r/1), int(2*g/3), int(b/2)
