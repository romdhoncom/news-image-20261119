#!/usr/bin/env python3
"""19 November 2026 in one image.

A pure-Python (standard library only) picture generator. It draws a
newspaper front page: a masthead naming the day, and six panels, one per
story of Thursday 19 November 2026, each with a hand-drawn scene and a
headline. No network, no clock, no randomness: the same bytes come out
on every run. Writes $MAKEFUN_OUTPUT_DIR/entry.png (or /output/entry.png).
"""

import binascii
import os
import struct
import zlib

W, H = 1024, 1024

PAPER = (247, 241, 222)   # cream newsprint
INK = (26, 26, 26)        # near-black ink
RED = (179, 35, 27)       # masthead red
GREY = (90, 86, 76)
WHITE = (255, 255, 255)
SKY = (126, 178, 217)
SEA = (46, 109, 164)
SAND = (217, 179, 128)
DARK = (20, 24, 30)

# ---------------------------------------------------------------- font
# A 5x7 bitmap font, written for this entry. Each glyph is 7 rows of 5
# bits, bit 4 (value 16) is the leftmost pixel. Only capitals are drawn.
FONT = {
    'A': (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'B': (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    'C': (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    'D': (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    'E': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    'F': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    'G': (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    'H': (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'I': (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'J': (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    'K': (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    'L': (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    'M': (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    'N': (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    'O': (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'P': (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    'Q': (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    'R': (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    'S': (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    'T': (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    'U': (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'V': (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'W': (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    'X': (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    'Y': (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    'Z': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    '0': (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    '1': (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    '2': (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    '3': (0x1E, 0x01, 0x01, 0x0E, 0x01, 0x01, 0x1E),
    '4': (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    '5': (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    '6': (0x0E, 0x10, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    '7': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    '8': (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    '9': (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x01, 0x0E),
    ' ': (0, 0, 0, 0, 0, 0, 0),
    '.': (0, 0, 0, 0, 0, 0x0C, 0x0C),
    ',': (0, 0, 0, 0, 0x0C, 0x04, 0x08),
    ':': (0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0),
    ';': (0, 0x0C, 0x0C, 0, 0x0C, 0x04, 0x08),
    '!': (0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04),
    '?': (0x0E, 0x11, 0x01, 0x06, 0x04, 0, 0x04),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    '-': (0, 0, 0, 0x0E, 0, 0, 0),
    '$': (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    '%': (0x19, 0x1A, 0x02, 0x04, 0x08, 0x0B, 0x13),
    '(': (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ')': (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    '/': (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    '&': (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    '+': (0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0),
    '=': (0, 0, 0x1F, 0, 0x1F, 0, 0),
    '"': (0x0A, 0x0A, 0, 0, 0, 0, 0),
}

# ---------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = c


def rect(x, y, w, h, c):
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        for xx in range(x0, x1):
            buf[i], buf[i + 1], buf[i + 2] = c
            i += 3


def hline(x0, x1, y, c):
    if x1 < x0:
        x0, x1 = x1, x0
    rect(x0, y, x1 - x0 + 1, 1, c)


def vline(x, y0, y1, c):
    if y1 < y0:
        y0, y1 = y1, y0
    rect(x, y0, 1, y1 - y0 + 1, c)


def line(x0, y0, x1, y1, c):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        px(x0, y0, c)
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def disc(cx, cy, r, c):
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        hline(cx - dx, cx + dx, cy + dy, c)


def poly(pts, c):
    # Scanline fill for a simple polygon given as [(x, y), ...].
    ys = [p[1] for p in pts]
    for y in range(max(min(ys), 0), min(max(ys), H - 1) + 1):
        xs = []
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) // (y1 - y0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            hline(xs[i], xs[i + 1], y, c)


def text(s, x, y, sc, c):
    for ch in s:
        g = FONT.get(ch, FONT[' '])
        for r in range(7):
            row = g[r]
            for col in range(5):
                if row & (16 >> col):
                    rect(x + col * sc, y + r * sc, sc, sc, c)
        x += 6 * sc


def text_w(s, sc):
    return len(s) * 6 * sc - sc if s else 0


def ctext(s, cx, y, sc, c):
    text(s, cx - text_w(s, sc) // 2, y, sc, c)


# ---------------------------------------------------------------- png
def chunk(typ, data):
    return (struct.pack('>I', len(data)) + typ + data +
            struct.pack('>I', binascii.crc32(typ + data) & 0xFFFFFFFF))


def png_bytes():
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += buf[y * W * 3:(y + 1) * W * 3]
    idat = zlib.compress(bytes(raw), 9)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
            chunk(b'IDAT', idat) + chunk(b'IEND', b''))

# ---------------------------------------------------------------- scenes
# Each scene draws inside a panel: scene box is (x+3, y+3, 484, 177).
# Colours are flat on purpose: a clean newspaper illustration.

def scene_summit(x, y):
    rect(x + 3, y + 3, 484, 177, (214, 206, 188))
    rect(x + 3, y + 150, 484, 30, (186, 164, 128))
    # Three flags on poles.
    poles = [x + 95, x + 245, x + 395]
    for i, px0 in enumerate(poles):
        vline(px0, y + 18, y + 118, (60, 52, 40))
        fx = px0 + 4
        if i == 0:  # United States: stripes + blue canton
            for s in range(7):
                rect(fx, y + 18 + s * 7, 66, 7,
                     (178, 34, 52) if s % 2 == 0 else WHITE)
            rect(fx, y + 18, 28, 24, (40, 60, 130))
            for dy in (4, 12, 20):
                for dx in (5, 15):
                    px(fx + dx, y + 18 + dy, WHITE)
        elif i == 1:  # China: red field, yellow stars
            rect(fx, y + 18, 66, 49, (222, 41, 16))
            disc(fx + 14, y + 32, 6, (255, 222, 0))
            for sx, sy in ((36, 24), (46, 30), (46, 40), (36, 44)):
                disc(fx + sx, y + sy, 3, (255, 222, 0))
        else:  # Russia: white, blue, red bands
            rect(fx, y + 18, 66, 17, WHITE)
            rect(fx, y + 35, 66, 16, (30, 80, 180))
            rect(fx, y + 51, 66, 16, (200, 30, 30))
    # Table with three seated figures.
    rect(x + 40, y + 122, 410, 10, (122, 84, 48))
    rect(x + 52, y + 132, 8, 18, (122, 84, 48))
    rect(x + 430, y + 132, 8, 18, (122, 84, 48))
    for cx in poles:
        rect(cx - 16, y + 96, 32, 26, (38, 38, 48))
        disc(cx, y + 88, 11, (224, 184, 148))


def scene_gaza(x, y):
    rect(x + 3, y + 3, 484, 100, (236, 222, 178))
    rect(x + 3, y + 103, 484, 77, SAND)
    disc(x + 420, y + 42, 22, (240, 205, 120))
    # Distant tents.
    for tx in (x + 60, x + 120, x + 175):
        poly([(tx, y + 103), (tx + 22, y + 82), (tx + 44, y + 103)],
             (190, 168, 132))
    # Tank.
    rect(x + 190, y + 128, 130, 24, (74, 74, 48))
    rect(x + 222, y + 106, 62, 22, (74, 74, 48))
    line(x + 284, y + 116, x + 340, y + 108, (52, 52, 34))
    line(x + 284, y + 118, x + 340, y + 110, (52, 52, 34))
    for wx in range(196, 316, 24):
        disc(x + wx, y + 152, 7, (52, 52, 34))
    # Smoke.
    disc(x + 240, y + 88, 12, (150, 140, 128))
    disc(x + 258, y + 74, 9, (170, 160, 148))


def scene_crimea(x, y):
    rect(x + 3, y + 3, 484, 72, (205, 224, 238))
    rect(x + 3, y + 75, 484, 105, SEA)
    for wy in (y + 130, y + 152, y + 170):
        for wx in range(x + 20, x + 480, 46):
            hline(wx, wx + 22, wy, (150, 190, 220))
    # Bridge deck and towers.
    rect(x + 3, y + 98, 484, 10, (70, 70, 78))
    for tx in (x + 120, x + 350):
        rect(tx, y + 48, 10, 50, (70, 70, 78))
        line(tx + 5, y + 48, tx - 70, y + 98, (120, 120, 130))
        line(tx + 5, y + 48, tx + 80, y + 98, (120, 120, 130))
    # Explosion on the span.
    disc(x + 245, y + 92, 26, (240, 120, 30))
    disc(x + 245, y + 92, 16, (250, 200, 60))
    disc(x + 245, y + 92, 8, WHITE)
    for ang in range(0, 360, 45):
        import math
        r = 34
        ex = x + 245 + int(r * math.cos(math.radians(ang)))
        ey = y + 92 + int(r * math.sin(math.radians(ang)))
        line(x + 245, y + 92, ex, ey, (240, 120, 30))
    disc(x + 222, y + 62, 12, (140, 140, 140))
    disc(x + 268, y + 56, 10, (160, 160, 160))


def scene_gta(x, y):
    bands = [(58, 28, 84), (122, 44, 110), (198, 68, 110),
             (240, 110, 80), (250, 160, 80), (255, 205, 115)]
    for i, c in enumerate(bands):
        rect(x + 3, y + 3 + i * 30, 484, 30, c)
    disc(x + 245, y + 105, 40, (255, 236, 170))
    # Skyline silhouettes.
    for bx, bh in ((20, 46), (70, 70), (130, 52), (330, 60), (380, 44),
                   (425, 74)):
        rect(x + 3 + bx, y + 180 - bh, 42, bh, (24, 18, 38))
    # Palm trees.
    for tx, lean in ((x + 60, -1), (x + 430, 1)):
        line(tx, y + 178, tx + lean * 14, y + 108, (24, 18, 38))
        line(tx + 2, y + 178, tx + lean * 14 + 2, y + 108, (24, 18, 38))
        top = (tx + lean * 14, y + 108)
        for dx, dy in ((-34, -6), (-24, -18), (-8, -24), (10, -22),
                       (26, -12), (34, 2)):
            line(top[0], top[1], top[0] + dx, top[1] + dy, (24, 18, 38))
    text("VI", x + 245 - text_w("VI", 8) // 2 + 4, y + 16 + 4, 8,
         (58, 28, 84))
    text("VI", x + 245 - text_w("VI", 8) // 2, y + 16, 8, WHITE)


def scene_ipo(x, y):
    rect(x + 3, y + 3, 484, 177, (14, 42, 28))
    for gy in range(y + 30, y + 170, 28):
        hline(x + 12, x + 472, gy, (28, 70, 48))
    text("$83", x + 22, y + 16, 6, WHITE)
    text("ANT", x + 380, y + 22, 4, (80, 220, 140))
    # Rising candlesticks, left to right.
    bars = [(26, 30), (34, 26), (30, 34), (44, 24), (40, 30), (52, 22),
            (48, 28), (60, 20)]
    bx = x + 30
    tops = []
    for hgt, wick in bars:
        base = y + 168
        body = hgt
        up = (bx // 40) % 2 == 0
        c = (46, 190, 100) if up else (210, 70, 60)
        vline(bx + 12, base - body - wick, base + 4, (140, 160, 140))
        rect(bx, base - body, 24, body, c)
        tops.append((bx + 12, base - body - 6))
        bx += 56
    for i in range(len(tops) - 1):
        line(tops[i][0], tops[i][1], tops[i + 1][0], tops[i + 1][1],
             (255, 255, 255))
    ex, ey = tops[-1]
    poly([(ex, ey - 14), (ex + 16, ey + 2), (ex - 2, ey + 2)], WHITE)


def scene_voyager(x, y):
    rect(x + 3, y + 3, 484, 177, (8, 10, 18))
    # Fixed-seed stars: the same sky on every run.
    s = 12345
    for _ in range(70):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        sx = x + 3 + s % 484
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        sy = y + 3 + s % 177
        px(sx, sy, WHITE if s % 3 else (170, 180, 200))
        if s % 7 == 0:
            px(sx + 1, sy, (200, 200, 220))
    # Earth, bottom left.
    disc(x + 82, y + 138, 34, (46, 110, 200))
    disc(x + 72, y + 130, 12, (70, 160, 90))
    disc(x + 96, y + 148, 9, (70, 160, 90))
    line(x + 56, y + 128, x + 104, y + 124, (200, 220, 240))
    # Dashed trajectory from Earth to the probe.
    for t in range(0, 11):
        fx = x + 110 + t * 22
        fy = y + 128 - t * 6
        line(fx, fy, fx + 12, fy - 3, (200, 200, 220))
    # The probe: gold body, dish, boom.
    rect(x + 330, y + 62, 46, 26, (212, 175, 55))
    poly([(x + 330, y + 62), (x + 296, y + 48), (x + 296, y + 102),
          (x + 330, y + 88)], (230, 195, 80))
    line(x + 376, y + 75, x + 420, y + 68, (180, 180, 190))
    disc(x + 424, y + 67, 4, (230, 230, 240))
    text("1 LIGHT-DAY", x + 250, y + 146, 3, WHITE)

# ---------------------------------------------------------------- compose
PANELS = [
    ("SUMMIT", (44, 82, 130), scene_summit,
     "TRUMP, XI AND PUTIN", "MEET IN SHENZHEN",
     "NUCLEAR ARMS ON THE AGENDA"),
    ("GAZA", (150, 90, 30), scene_gaza,
     "ISRAEL PUSHES INTO", "GAZA BEYOND THE LINE",
     "TROOPS CROSS CEASEFIRE LINE"),
    ("CRIMEA", (120, 30, 30), scene_crimea,
     "CRIMEA BRIDGE HIT", "AGAIN, TRAFFIC HALTED",
     "UKRAINE STRIKES KEY LINK"),
    ("GAMES", (200, 40, 120), scene_gta,
     "GTA VI IS OUT", "AFTER 13 LONG YEARS",
     "PS5 AND XBOX, AT MIDNIGHT"),
    ("MARKETS", (20, 120, 60), scene_ipo,
     "ANTHROPIC'S RECORD", "IPO DEBUTS AT $83",
     "BIGGEST DEBUT IN HISTORY"),
    ("SPACE", (30, 30, 60), scene_voyager,
     "VOYAGER 1, ONE", "LIGHT-DAY FROM EARTH",
     "16 BILLION MILES AND COUNTING"),
]


def compose():
    rect(0, 0, W, H, PAPER)
    # Masthead.
    ctext("THE WORLD IN ONE DAY", 512, 20, 6, INK)
    ctext("THURSDAY 19 NOVEMBER 2026", 512, 72, 4, RED)
    hline(16, 1007, 110, INK)
    hline(16, 1007, 113, RED)
    ctext("SIX STORIES FROM AROUND THE GLOBE", 512, 122, 2, GREY)
    # Panels: 2 columns x 3 rows.
    for i, (kick, kc, draw, l1, l2, cap) in enumerate(PANELS):
        px0 = 16 + (i % 2) * 502
        py0 = 140 + (i // 2) * 293
        # Border.
        rect(px0, py0, 490, 3, INK)
        rect(px0, py0 + 278, 490, 3, INK)
        rect(px0, py0, 3, 281, INK)
        rect(px0 + 487, py0, 3, 281, INK)
        # Scene and kicker tab.
        draw(px0, py0)
        rect(px0 + 3, py0 + 3, text_w(kick, 2) + 22, 26, kc)
        text(kick, px0 + 14, py0 + 10, 2, WHITE)
        # Headlines and caption.
        text(l1, px0 + 14, py0 + 192, 3, INK)
        text(l2, px0 + 14, py0 + 220, 3, INK)
        text(cap, px0 + 14, py0 + 252, 2, (138, 31, 26))


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out, exist_ok=True)
    compose()
    with open(os.path.join(out, "entry.png"), "wb") as f:
        f.write(png_bytes())


if __name__ == "__main__":
    main()
