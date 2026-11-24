#!/usr/bin/env python3
"""One-page newspaper front page for Tuesday 24 November 2026.

Pure Python 3.13 standard library. Every letter is drawn with a hand-built
vector stroke alphabet; every picture is drawn from rectangles, discs and
polygons. No fonts, no images, no network, no clock, no randomness.
Deterministic: the same run always writes the same bytes.

Usage: MAKEFUN_OUTPUT_DIR=<dir> python3 main.py
Writes <dir>/entry.png (1024x1024) and prints the layout checker's verdict.
"""

import math
import os
import struct
import sys
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
INK = (16, 16, 16)
PAPER = (251, 248, 239)
PAPER2 = (243, 237, 222)
RED = (176, 32, 26)
NAVY = (16, 32, 64)
BLUE = (28, 68, 116)
TEAL = (12, 94, 88)
GOLD = (178, 128, 24)
GREY = (98, 96, 90)
LIGHTGREY = (208, 202, 188)
RULE = (58, 56, 50)
SKY = (206, 226, 236)
SKY2 = (158, 192, 210)
SEA = (172, 200, 216)
LAND = (233, 223, 191)
LAND2 = (210, 200, 164)
WHITE = (255, 255, 255)
NIGHT = (14, 22, 46)
NIGHT2 = (28, 40, 76)
AMBER = (240, 176, 40)
FLAME = (232, 98, 24)
GREEN = (46, 110, 58)
PURPLE = (110, 80, 140)
BROWN = (96, 64, 40)
DARKBROWN = (58, 38, 26)
BEIGE = (238, 228, 205)
PALE_GREEN = (214, 232, 205)
PALE_TAN = (236, 222, 190)
SKIN1 = (232, 190, 150)
SKIN2 = (196, 140, 100)
SKIN3 = (150, 100, 70)
ORANGE = (230, 120, 30)

# ---------------------------------------------------------------- canvas
_buf = bytearray(W * H * 3)
_CLIP = None          # (x0, y0, x1, y1) or None: pixels may not leave it
_DROPPED = [0]        # pixels refused by the clip (must stay 0)
_SCENE_EXTENT = None  # [minx, miny, maxx, maxy] of pixels drawn while clipped


def _fill_paper():
    row = bytes(PAPER) * W
    for y in range(H):
        _buf[y * W * 3:(y + 1) * W * 3] = row


def set_clip(rect):
    """rect is (x, y, w, h) or None. While set, no pixel may leave it."""
    global _CLIP, _SCENE_EXTENT
    if rect is None:
        _CLIP = None
        _SCENE_EXTENT = None
    else:
        x, y, w, h = rect
        _CLIP = (int(x), int(y), int(x + w), int(y + h))
        _SCENE_EXTENT = [W, H, -1, -1]


def scene_extent():
    return _SCENE_EXTENT


def dropped_count():
    return _DROPPED[0]


def _px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        if _CLIP is not None:
            cx0, cy0, cx1, cy1 = _CLIP
            if not (cx0 <= x < cx1 and cy0 <= y < cy1):
                _DROPPED[0] += 1
                return
            e = _SCENE_EXTENT
            if x < e[0]:
                e[0] = x
            if x > e[2]:
                e[2] = x
            if y < e[1]:
                e[1] = y
            if y > e[3]:
                e[3] = y
        i = (y * W + x) * 3
        _buf[i] = c[0]
        _buf[i + 1] = c[1]
        _buf[i + 2] = c[2]


def _row_span(y, x0, x1, c):
    """Fill pixels [x0, x1) on row y, honouring canvas bounds and clip."""
    if y < 0 or y >= H or x1 <= x0:
        return
    if _CLIP is not None:
        cx0, cy0, cx1, cy1 = _CLIP
        if not (cy0 <= y < cy1):
            return
        x0 = max(x0, cx0)
        x1 = min(x1, cx1)
        if x1 <= x0:
            return
    else:
        x0 = max(x0, 0)
        x1 = min(x1, W)
        if x1 <= x0:
            return
    if _CLIP is not None:
        e = _SCENE_EXTENT
        if x0 < e[0]:
            e[0] = x0
        if x1 - 1 > e[2]:
            e[2] = x1 - 1
        if y < e[1]:
            e[1] = y
        if y > e[3]:
            e[3] = y
    seg = bytes(c) * (x1 - x0)
    i = (y * W + x0) * 3
    _buf[i:i + len(seg)] = seg


def rect(x0, y0, x1, y1, c):
    """Fill rectangle [x0, x1) x [y0, y1)."""
    x0 = int(math.floor(x0))
    y0 = int(math.floor(y0))
    x1 = int(math.ceil(x1))
    y1 = int(math.ceil(y1))
    for y in range(y0, y1):
        _row_span(y, x0, x1, c)


def hline(x0, x1, y, c, w=1):
    rect(x0, y - w / 2.0, x1, y + w / 2.0, c)


def vline(x, y0, y1, c, w=1):
    rect(x - w / 2.0, y0, x + w / 2.0, y1, c)


def disc(cx, cy, r, c):
    """Filled disc, centre (cx, cy), radius r (floats allowed).
    Edges are computed from the exact float centre, not a rounded one,
    so curved and diagonal strokes stay smooth instead of stepping."""
    r = float(r)
    if r <= 0:
        return
    y0 = int(math.floor(cy - r))
    y1 = int(math.ceil(cy + r))
    for y in range(y0, y1 + 1):
        dy = y - cy
        if abs(dy) > r:
            continue
        dx = math.sqrt(max(0.0, r * r - dy * dy))
        _row_span(y, int(math.ceil(cx - dx)), int(math.floor(cx + dx)) + 1, c)


def line(x0, y0, x1, y1, w, c):
    """Thick round-ended line, sampled finely so diagonals stay smooth."""
    w = float(w)
    if w <= 0:
        return
    dx = x1 - x0
    dy = y1 - y0
    length = math.hypot(dx, dy)
    if length < 0.001:
        disc(x0, y0, w / 2.0, c)
        return
    step = max(0.3, w * 0.28)
    n = max(1, int(length / step) + 1)
    for i in range(n + 1):
        t = i / n
        disc(x0 + dx * t, y0 + dy * t, w / 2.0, c)


def polyline(pts, w, c):
    for i in range(len(pts) - 1):
        line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], w, c)
    if len(pts) == 1:
        disc(pts[0][0], pts[0][1], w / 2.0, c)


def polygon(pts, c):
    """Fill a polygon (even-odd scanline fill). pts: list of (x, y)."""
    if len(pts) < 3:
        return
    ys = [p[1] for p in pts]
    y0 = int(math.ceil(min(ys)))
    y1 = int(math.floor(max(ys)))
    n = len(pts)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x0, yy0 = pts[i]
            x1, yy1 = pts[(i + 1) % n]
            if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                t = (y - yy0) / (yy1 - yy0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            _row_span(y, int(math.ceil(xs[i])), int(math.floor(xs[i + 1])) + 1, c)


def frame(x, y, w, h, c, t=1):
    """Thin rectangular frame, drawn exactly on the band boundary."""
    rect(x, y, x + w, y + t, c)
    rect(x, y + h - t, x + w, y + h, c)
    rect(x, y, x + t, y + h, c)
    rect(x + w - t, y, x + w, y + h, c)


# ---------------------------------------------------------------- PNG output
def _png_chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += _buf[y * W * 3:(y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += _png_chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ------------------------------------------------------- stroke alphabet
# Each glyph is a list of polylines on an 8-unit em: cap top y=0,
# baseline y=8, descender floor y=10. Lowercase renders as small caps
# from the same outlines. A one-point polyline draws a dot.
_O = [(4.0, 0.0), (5.8, 0.7), (6.8, 2.0), (7.0, 4.0), (6.8, 6.0),
      (5.8, 7.3), (4.0, 8.0), (2.2, 7.3), (1.2, 6.0), (1.0, 4.0),
      (1.2, 2.0), (2.2, 0.7), (4.0, 0.0)]
GLYPHS = {
    "A": [[(1.0, 8.0), (4.0, 0.0), (7.0, 8.0)], [(2.6, 5.0), (5.4, 5.0)]],
    "B": [[(1.0, 0.0), (1.0, 8.0)],
          [(1.0, 0.0), (5.0, 0.0), (6.5, 1.5), (6.5, 3.0), (5.0, 4.0), (1.0, 4.0)],
          [(1.0, 4.0), (5.0, 4.0), (6.5, 5.5), (6.5, 7.0), (5.0, 8.0), (1.0, 8.0)]],
    "C": [[(6.5, 1.5), (5.0, 0.0), (2.0, 0.0), (0.5, 1.5), (0.5, 6.5),
           (2.0, 8.0), (5.0, 8.0), (6.5, 6.5)]],
    "D": [[(1.0, 0.0), (1.0, 8.0)],
          [(1.0, 0.0), (5.0, 0.0), (7.0, 2.0), (7.0, 6.0), (5.0, 8.0), (1.0, 8.0)]],
    "E": [[(1.0, 0.0), (1.0, 8.0)], [(1.0, 0.0), (6.0, 0.0)],
          [(1.0, 4.0), (5.0, 4.0)], [(1.0, 8.0), (6.0, 8.0)]],
    "F": [[(1.0, 0.0), (1.0, 8.0)], [(1.0, 0.0), (6.0, 0.0)],
          [(1.0, 4.0), (5.0, 4.0)]],
    "G": [[(6.5, 1.5), (5.0, 0.0), (2.0, 0.0), (0.5, 1.5), (0.5, 6.5),
           (2.0, 8.0), (5.0, 8.0), (6.5, 6.5), (6.5, 4.0), (4.0, 4.0)]],
    "H": [[(1.0, 0.0), (1.0, 8.0)], [(7.0, 0.0), (7.0, 8.0)],
          [(1.0, 4.0), (7.0, 4.0)]],
    "I": [[(4.0, 0.0), (4.0, 8.0)], [(2.0, 0.0), (6.0, 0.0)],
          [(2.0, 8.0), (6.0, 8.0)]],
    "J": [[(2.5, 0.0), (6.5, 0.0)], [(6.0, 0.0), (6.0, 6.0),
           (5.0, 8.0), (3.0, 8.0), (1.5, 6.5)]],
    "K": [[(1.0, 0.0), (1.0, 8.0)], [(6.5, 0.0), (1.5, 4.5)],
          [(3.0, 3.5), (6.5, 8.0)]],
    "L": [[(1.0, 0.0), (1.0, 8.0)], [(1.0, 8.0), (6.0, 8.0)]],
    "M": [[(1.0, 8.0), (1.0, 0.0), (4.0, 4.0), (7.0, 0.0), (7.0, 8.0)]],
    "N": [[(1.0, 8.0), (1.0, 0.0), (7.0, 8.0), (7.0, 0.0)]],
    "O": [_O],
    "P": [[(1.0, 0.0), (1.0, 8.0)],
          [(1.0, 0.0), (5.0, 0.0), (6.5, 1.5), (6.5, 3.0), (5.0, 4.0), (1.0, 4.0)]],
    "Q": [_O, [(5.0, 6.0), (7.5, 8.5)]],
    "R": [[(1.0, 0.0), (1.0, 8.0)],
          [(1.0, 0.0), (5.0, 0.0), (6.5, 1.5), (6.5, 3.0), (5.0, 4.0), (1.0, 4.0)],
          [(3.5, 4.0), (6.5, 8.0)]],
    "S": [[(6.0, 1.0), (4.5, 0.0), (2.5, 0.0), (1.0, 1.0), (1.0, 3.0),
           (2.5, 4.0), (5.5, 4.0), (7.0, 5.0), (7.0, 7.0), (5.5, 8.0),
           (3.5, 8.0), (2.0, 7.0)]],
    "T": [[(1.0, 0.0), (7.0, 0.0)], [(4.0, 0.0), (4.0, 8.0)]],
    "U": [[(1.0, 0.0), (1.0, 6.0), (2.0, 8.0), (4.0, 8.0), (6.0, 8.0),
           (7.0, 6.0), (7.0, 0.0)]],
    "V": [[(1.0, 0.0), (4.0, 8.0), (7.0, 0.0)]],
    "W": [[(1.0, 0.0), (2.5, 8.0), (4.0, 4.0), (5.5, 8.0), (7.0, 0.0)]],
    "X": [[(1.0, 0.0), (7.0, 8.0)], [(7.0, 0.0), (1.0, 8.0)]],
    "Y": [[(1.0, 0.0), (4.0, 4.0), (7.0, 0.0)], [(4.0, 4.0), (4.0, 8.0)]],
    "Z": [[(1.0, 0.0), (7.0, 0.0), (1.0, 8.0), (7.0, 8.0)]],
    "0": [_O],
    "1": [[(3.0, 1.5), (5.0, 0.0), (5.0, 8.0)], [(3.0, 8.0), (7.0, 8.0)]],
    "2": [[(1.5, 1.0), (3.0, 0.0), (5.0, 0.0), (6.5, 1.5), (6.0, 3.5),
           (4.0, 5.0), (1.0, 8.0), (7.0, 8.0)]],
    "3": [[(1.5, 0.5), (3.0, 0.0), (5.0, 0.0), (6.5, 1.5), (6.0, 3.0),
           (4.5, 4.0), (6.0, 5.0), (6.5, 6.5), (5.0, 8.0), (3.0, 8.0),
           (1.5, 7.5)]],
    "4": [[(1.0, 5.5), (5.5, 0.0), (5.5, 8.0)], [(1.0, 5.5), (6.5, 5.5)]],
    "5": [[(6.5, 0.0), (1.0, 0.0), (1.0, 4.0), (5.0, 4.0), (6.5, 5.5),
           (6.5, 7.0), (5.0, 8.0), (2.0, 8.0), (1.0, 7.0)]],
    "6": [[(6.0, 1.5), (5.0, 0.0), (2.0, 0.5), (1.0, 2.0), (1.0, 6.0),
           (2.0, 8.0), (5.0, 8.0), (6.5, 6.5), (6.5, 4.5), (5.0, 3.5),
           (2.0, 3.5), (1.0, 5.0)]],
    "7": [[(1.0, 0.0), (7.0, 0.0), (3.5, 8.0)]],
    "8": [[(4.0, 0.0), (6.0, 1.0), (6.5, 2.5), (5.0, 4.0), (3.0, 4.0),
           (1.5, 2.5), (2.0, 1.0), (4.0, 0.0)],
          [(3.0, 4.0), (5.0, 4.0), (6.5, 5.5), (6.5, 7.0), (5.0, 8.0),
           (3.0, 8.0), (1.5, 7.0), (1.5, 5.5), (3.0, 4.0)]],
    "9": [[(1.0, 6.5), (1.0, 4.0), (2.0, 2.0), (4.0, 1.0), (6.0, 2.0),
           (6.5, 4.0), (6.0, 6.0), (5.0, 8.0), (2.0, 8.0), (1.0, 7.0)]],
    ".": [[(4.0, 7.7), (4.0, 7.7)]],
    ",": [[(4.0, 7.5), (4.0, 8.2), (3.0, 9.5)]],
    ":": [[(4.0, 2.5), (4.0, 2.5)], [(4.0, 7.7), (4.0, 7.7)]],
    ";": [[(4.0, 2.5), (4.0, 2.5)], [(4.0, 7.5), (4.0, 8.2), (3.0, 9.5)]],
    "!": [[(4.0, 0.0), (4.0, 6.0)], [(4.0, 7.7), (4.0, 7.7)]],
    "?": [[(2.0, 1.0), (3.0, 0.0), (5.0, 0.0), (6.0, 1.0), (6.0, 2.5),
           (5.0, 4.0), (4.0, 4.5), (4.0, 6.0)], [(4.0, 7.7), (4.0, 7.7)]],
    "-": [[(1.0, 4.5), (7.0, 4.5)]],
    "\u2013": [[(0.5, 4.5), (7.5, 4.5)]],
    "\u2014": [[(0.0, 4.5), (8.0, 4.5)]],
    "(": [[(5.0, 0.0), (3.0, 2.0), (3.0, 6.0), (5.0, 8.0)]],
    ")": [[(3.0, 0.0), (5.0, 2.0), (5.0, 6.0), (3.0, 8.0)]],
    "'": [[(4.5, 0.0), (4.0, 2.0)]],
    "\u2019": [[(4.5, 0.0), (4.0, 2.0)]],
    '"': [[(2.5, 0.0), (2.0, 2.0)], [(5.5, 0.0), (5.0, 2.0)]],
    "/": [[(6.0, 0.0), (2.0, 8.0)]],
    "%": [[(1.5, 0.0), (6.5, 8.0)],
          [(2.5, 0.5), (3.8, 0.5), (4.3, 1.5), (3.8, 2.8), (2.5, 2.8),
           (1.8, 1.5), (2.5, 0.5)],
          [(5.5, 5.2), (6.8, 5.2), (7.3, 6.2), (6.8, 7.5), (5.5, 7.5),
           (4.8, 6.2), (5.5, 5.2)]],
    "$": [[(6.0, 1.0), (4.5, 0.0), (2.5, 0.0), (1.0, 1.0), (1.0, 3.0),
           (2.5, 4.0), (5.5, 4.0), (7.0, 5.0), (7.0, 7.0), (5.5, 8.0),
           (3.5, 8.0), (2.0, 7.0)],
          [(4.0, -0.5), (4.0, 8.5)]],
    "\u00b0": [[(4.0, 0.0), (5.2, 0.6), (5.5, 1.8), (4.5, 2.8),
               (3.2, 2.5), (2.8, 1.2), (4.0, 0.0)]],
    "\u2022": [[(4.0, 4.3), (4.0, 4.3)]],
    "\u00b7": [[(4.0, 4.0), (4.0, 4.0)]],
    "+": [[(4.0, 1.5), (4.0, 6.5)], [(1.5, 4.0), (6.5, 4.0)]],
    "=": [[(1.0, 3.0), (7.0, 3.0)], [(1.0, 5.5), (7.0, 5.5)]],
    "<": [[(6.0, 1.0), (2.0, 4.0), (6.0, 7.0)]],
    ">": [[(2.0, 1.0), (6.0, 4.0), (2.0, 7.0)]],
    "[": [[(6.0, 0.0), (2.0, 0.0), (2.0, 8.0), (6.0, 8.0)]],
    "]": [[(2.0, 0.0), (6.0, 0.0), (6.0, 8.0), (2.0, 8.0)]],
    "*": [[(4.0, 1.0), (4.0, 7.0)], [(1.5, 2.5), (6.5, 5.5)],
          [(6.5, 2.5), (1.5, 5.5)]],
    "#": [[(2.5, 0.5), (2.5, 7.5)], [(5.5, 0.5), (5.5, 7.5)],
          [(0.5, 3.0), (7.5, 3.0)], [(0.5, 5.5), (7.5, 5.5)]],
    "&": [[(6.0, 1.0), (5.0, 0.0), (3.0, 0.0), (2.0, 1.0), (2.0, 3.0),
           (4.0, 4.5), (6.0, 5.5), (6.5, 7.0), (5.0, 8.0), (3.0, 8.0),
           (1.5, 7.0)],
          [(2.0, 3.0), (6.0, 8.0)]],
}
# Advance widths in em units. Most glyphs take their advance from their
# actual drawn span plus tracking; the overrides below are for glyphs
# whose drawn span understates their visual width (space, dots).
XSCALE = 0.72  # condensed horizontal scale: glyphs and advances are
# squeezed so long tile bodies still fit two lines at a readable size.
ADV = {" ": 4.4, ".": 3.2, ",": 3.2, ":": 3.2, ";": 3.6, "!": 3.6,
       "'": 2.8, "\u2019": 2.8, '"': 5.6, "\u00b0": 4.6, "\u2022": 4.2,
       "\u00b7": 4.2}
LOWER_ADV = 5.9  # lowercase letters render as small caps, slightly narrower


def _span(ch):
    g = GLYPHS.get(ch)
    if g is None and ch.islower():
        g = GLYPHS.get(ch.upper())
    if g is None:
        return None
    xs = [x for stroke in g for (x, y) in stroke]
    return max(xs) - min(xs)


def _adv_units(ch):
    if ch in ADV:
        return ADV[ch]
    span = _span(ch)
    if span is None:
        return 7.3
    return span + 1.4


def _glyph(ch):
    if ch == " ":
        return None
    g = GLYPHS.get(ch)
    if g is None and ch.islower():
        g = GLYPHS.get(ch.upper())
    return g


# Serif ticks for the masthead face: (stem x in units, y in units) points
# where a short horizontal tick is drawn at the foot / top of a stem.
SERIF_TICKS = {
    "B": [(1.0, 0.0), (1.0, 8.0)], "D": [(1.0, 0.0), (1.0, 8.0)],
    "E": [(1.0, 0.0), (1.0, 8.0)], "F": [(1.0, 0.0)],
    "H": [(1.0, 0.0), (1.0, 8.0), (7.0, 0.0), (7.0, 8.0)],
    "I": [(4.0, 0.0), (4.0, 8.0)], "K": [(1.0, 0.0), (1.0, 8.0)],
    "L": [(1.0, 0.0), (1.0, 8.0)], "M": [(1.0, 0.0), (1.0, 8.0),
                                          (7.0, 0.0), (7.0, 8.0)],
    "N": [(1.0, 0.0), (1.0, 8.0), (7.0, 0.0), (7.0, 8.0)],
    "P": [(1.0, 0.0)], "R": [(1.0, 0.0)],
    "T": [(4.0, 0.0), (4.0, 8.0)], "U": [(1.0, 0.0), (7.0, 0.0)],
    "Y": [(4.0, 8.0)], "1": [(5.0, 0.0), (5.0, 8.0)],
    "4": [(5.5, 0.0), (5.5, 8.0)],
}


# ------------------------------------------------------------- text engine
def text_width(s, cap):
    """Width in pixels of s at cap height cap."""
    scale = cap / 8.0
    return sum(_adv_units(ch) for ch in s) * scale * XSCALE


def _draw_glyph(ch, ox, oy, scale, weight, color, serif):
    g = _glyph(ch)
    if g is None:
        return
    for stroke in g:
        pts = [(ox + x * scale * XSCALE, oy + y * scale) for (x, y) in stroke]
        polyline(pts, weight, color)
    if serif:
        key = ch.upper() if ch.islower() else ch
        for (sx, sy) in SERIF_TICKS.get(key, []):
            tick = 1.25 * scale * XSCALE
            line(ox + sx * scale * XSCALE - tick, oy + sy * scale,
                 ox + sx * scale * XSCALE + tick, oy + sy * scale, weight,
                 color)


def draw_text(s, x, y_top, cap, color, weight_frac=0.12, align="left",
              box_w=None, serif=False):
    """Draw one line. y_top is the cap top. Returns the baseline y."""
    scale = cap / 8.0
    weight = max(1.0, weight_frac * cap)
    w = text_width(s, cap)
    if align == "center":
        x = x + (box_w - w) / 2.0 if box_w is not None else x - w / 2.0
    elif align == "right":
        x = x + box_w - w if box_w is not None else x - w
    cx = x
    for ch in s:
        if ch != " ":
            _draw_glyph(ch, cx, y_top, scale, weight, color, serif)
        cx += _adv_units(ch) * scale * XSCALE
    return y_top + cap


def fit_cap(s, cap, max_w):
    """Largest cap height <= cap at which s fits in max_w."""
    w = text_width(s, cap)
    if w <= max_w:
        return cap
    return cap * max_w / w


def wrap_text(s, cap, max_w):
    """Greedy word wrap. Returns a list of lines (each fits max_w)."""
    words = s.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, cap) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(s, x, y_top, cap, max_w, color, weight_frac=0.12,
                 line_h=None, max_lines=None, shrink=True, max_bottom=None):
    """Draw wrapped text; shrink cap until it fits max_lines (if given)
    and above max_bottom (if given). Returns (bottom y, cap used, lines)."""
    if line_h is None:
        line_h = cap * 1.32
    use_cap = cap
    if shrink:
        while use_cap > 5.0:
            lines = wrap_text(s, use_cap, max_w)
            if max_lines is not None:
                lines = lines[:max_lines]
            lh = use_cap * 1.32
            bottom = y_top + (len(lines) - 1) * lh + use_cap
            too_many = (max_lines is not None and
                        len(wrap_text(s, use_cap, max_w)) > max_lines)
            too_low = max_bottom is not None and bottom > max_bottom
            if not too_many and not too_low:
                break
            use_cap -= 0.5
    lines = wrap_text(s, use_cap, max_w)
    if max_lines is not None:
        lines = lines[:max_lines]
    lh = use_cap * 1.32
    y = y_top
    for ln in lines:
        draw_text(ln, x, y, use_cap, color, weight_frac)
        y += lh
    return y - (lh - use_cap), use_cap, len(lines)

# ------------------------------------------------------------------ scenes
# Every scene is drawn ONLY with fractions of its band (x, y, w, h):
# a point is x + f*w, y + g*h with 0 <= f, g <= 1. The clip rectangle is
# set to the band while a scene draws, so no pixel can escape it.


class Scene:
    def __init__(self, band):
        self.x, self.y, self.w, self.h = band

    def X(self, f):
        return self.x + f * self.w

    def Y(self, g):
        return self.y + g * self.h

    def rect(self, f0, g0, f1, g1, c):
        rect(self.X(f0), self.Y(g0), self.X(f1), self.Y(g1), c)

    def disc(self, f, g, r_frac, c):
        disc(self.X(f), self.Y(g), r_frac * min(self.w, self.h), c)

    def line(self, f0, g0, f1, g1, w_frac, c):
        line(self.X(f0), self.Y(g0), self.X(f1), self.Y(g1),
             w_frac * min(self.w, self.h), c)

    def poly(self, pts, c):
        polygon([(self.X(f), self.Y(g)) for (f, g) in pts], c)

    def text(self, s, f, g, cap, c, weight_frac=0.12, align="left"):
        draw_text(s, self.X(f), self.Y(g), cap, c, weight_frac, align)


def draw_scene(band, painter):
    """Draw a scene clipped to its band; return its pixel extent."""
    set_clip(band)
    painter(Scene(band))
    ext = list(scene_extent())
    set_clip(None)
    return ext


# ------------------------------------------------------------ lead scenes
def scene_kyiv(s):
    s.rect(0, 0, 1, 1, NIGHT)
    s.disc(0.82, 0.16, 0.07, (210, 214, 230))  # moon
    # skyline blocks
    blocks = [(0.02, 0.42, 0.16, 1.0), (0.18, 0.55, 0.30, 1.0),
              (0.32, 0.38, 0.46, 1.0), (0.48, 0.52, 0.60, 1.0),
              (0.62, 0.45, 0.76, 1.0), (0.78, 0.58, 0.92, 1.0),
              (0.93, 0.66, 1.0, 1.0)]
    for (a, b, c2, d) in blocks:
        s.rect(a, b, c2, d, NIGHT2)
    # broken tall block
    s.poly([(0.32, 0.38), (0.40, 0.30), (0.43, 0.36), (0.46, 0.38),
            (0.46, 1.0), (0.32, 1.0)], NIGHT2)
    # lit amber windows
    for (fx, gy) in [(0.06, 0.55), (0.10, 0.70), (0.22, 0.65), (0.36, 0.50),
                     (0.40, 0.65), (0.52, 0.62), (0.66, 0.55), (0.70, 0.72),
                     (0.84, 0.68), (0.38, 0.80)]:
        s.rect(fx, gy, fx + 0.02, gy + 0.06, AMBER)
    # searchlight beam
    s.poly([(0.60, 1.0), (0.64, 1.0), (0.80, 0.05), (0.72, 0.05)],
           (214, 220, 235))
    # three drones with trails
    for (fx, gy) in [(0.25, 0.14), (0.55, 0.09), (0.78, 0.22)]:
        s.line(fx - 0.10, gy + 0.05, fx - 0.015, gy, 0.012, AMBER)
        s.disc(fx, gy, 0.022, AMBER)
    # smoke puffs
    for (fx, gy, r) in [(0.38, 0.28, 0.035), (0.42, 0.22, 0.028),
                        (0.35, 0.20, 0.022)]:
        s.disc(fx, gy, r, (120, 120, 125))


def scene_cop(s):
    s.rect(0, 0, 1, 0.62, (240, 224, 196))
    s.rect(0, 0.62, 1, 1, (214, 186, 148))
    s.disc(0.78, 0.42, 0.11, (232, 130, 40))  # low sun
    # cracked earth
    s.line(0.05, 0.72, 0.30, 0.85, 0.012, BROWN)
    s.line(0.30, 0.85, 0.55, 0.78, 0.012, BROWN)
    s.line(0.62, 0.74, 0.85, 0.88, 0.012, BROWN)
    s.line(0.30, 0.85, 0.38, 0.97, 0.010, BROWN)
    # conference table
    s.rect(0.10, 0.66, 0.90, 0.78, (120, 84, 52))
    s.rect(0.10, 0.66, 0.90, 0.70, (150, 110, 70))
    # six delegates, alternating navy / teal heads
    for i in range(6):
        fx = 0.16 + i * 0.136
        s.disc(fx, 0.56, 0.045, NAVY if i % 2 == 0 else TEAL)
        s.rect(fx - 0.045, 0.60, fx + 0.045, 0.67,
               NAVY if i % 2 == 0 else TEAL)
    # torn pact document, two halves with a red tear
    s.poly([(0.42, 0.18), (0.50, 0.18), (0.50, 0.26), (0.47, 0.30),
            (0.50, 0.34), (0.47, 0.38), (0.50, 0.42), (0.42, 0.42)],
           WHITE)
    s.poly([(0.50, 0.18), (0.58, 0.18), (0.58, 0.42), (0.50, 0.42),
            (0.53, 0.38), (0.50, 0.34), (0.53, 0.30), (0.50, 0.26)],
           WHITE)
    s.line(0.50, 0.18, 0.50, 0.42, 0.012, RED)
    s.text("NO DEAL", 0.03, 0.04, 11, RED, 0.16)


def scene_markets(s):
    s.rect(0, 0, 1, 1, (10, 12, 20))
    # falling red candlesticks
    tops = [(0.06, 0.18), (0.18, 0.28), (0.30, 0.36), (0.42, 0.44),
            (0.54, 0.55), (0.66, 0.62), (0.78, 0.70), (0.88, 0.78)]
    for (fx, gy) in tops:
        s.line(fx + 0.03, gy - 0.06, fx + 0.03, gy + 0.22, 0.008, RED)
        s.rect(fx, gy, fx + 0.06, gy + 0.16, RED)
    # plunging gold line
    s.poly([(0.04, 0.16), (0.20, 0.26), (0.38, 0.34), (0.55, 0.50),
            (0.72, 0.62), (0.90, 0.82), (0.94, 0.86), (0.90, 0.88),
            (0.70, 0.68), (0.52, 0.54), (0.36, 0.38), (0.18, 0.28),
            (0.04, 0.20)], GOLD)
    s.disc(0.93, 0.86, 0.02, GOLD)
    s.text("-10%", 0.04, 0.04, 12, GOLD, 0.16)


# ------------------------------------------------------------ tile scenes
def scene_train(s):
    s.rect(0, 0, 1, 0.72, SKY)
    s.rect(0, 0.72, 1, 1, GREEN)
    # flag poles: orange flag, red flag
    s.line(0.06, 0.06, 0.06, 0.72, 0.012, INK)
    s.poly([(0.06, 0.06), (0.16, 0.10), (0.06, 0.16)], (240, 120, 30))
    s.line(0.90, 0.06, 0.90, 0.72, 0.012, INK)
    s.poly([(0.90, 0.06), (0.80, 0.10), (0.90, 0.16)], RED)
    # train: blue loco, red carriage, blue carriage
    s.rect(0.10, 0.42, 0.32, 0.68, BLUE)
    s.rect(0.34, 0.46, 0.58, 0.68, RED)
    s.rect(0.60, 0.46, 0.86, 0.68, BLUE)
    for fx in (0.14, 0.20, 0.26, 0.38, 0.46, 0.52, 0.64, 0.72, 0.80):
        s.rect(fx, 0.50, fx + 0.035, 0.58, (230, 240, 245))
    for fx in (0.16, 0.28, 0.40, 0.52, 0.66, 0.80):
        s.disc(fx, 0.70, 0.035, INK)
    s.line(0.04, 0.76, 0.96, 0.76, 0.012, INK)


def scene_fire(s):
    s.rect(0, 0, 1, 1, DARKBROWN)
    # factory block
    s.rect(0.12, 0.48, 0.88, 0.94, (110, 108, 104))
    s.rect(0.12, 0.48, 0.88, 0.54, (88, 86, 82))
    for fx in (0.20, 0.34, 0.48, 0.62, 0.76):
        s.rect(fx, 0.60, fx + 0.06, 0.72, AMBER)
    # flames rising from the block (kept below the band top)
    s.poly([(0.24, 0.50), (0.30, 0.16), (0.36, 0.50)], FLAME)
    s.poly([(0.44, 0.50), (0.50, 0.08), (0.56, 0.50)], AMBER)
    s.poly([(0.62, 0.50), (0.68, 0.20), (0.74, 0.50)], FLAME)
    s.disc(0.30, 0.42, 0.05, AMBER)
    s.disc(0.50, 0.38, 0.055, FLAME)
    s.disc(0.68, 0.44, 0.045, AMBER)
    # smoke above
    s.disc(0.30, 0.10, 0.05, (150, 148, 144))
    s.disc(0.50, 0.06, 0.055, (150, 148, 144))
    s.disc(0.68, 0.12, 0.045, (150, 148, 144))


def scene_protest(s):
    s.rect(0, 0, 1, 1, BEIGE)
    # five placards on sticks, alternating white / pale yellow
    for i in range(5):
        fx = 0.07 + i * 0.185
        s.line(fx + 0.05, 0.52, fx + 0.05, 0.86, 0.012, INK)
        col = WHITE if i % 2 == 0 else (250, 238, 180)
        s.rect(fx, 0.12, fx + 0.13, 0.52, col)
        frame(s.X(fx), s.Y(0.12), 0.13 * s.w, 0.40 * s.h, INK, 1)
        s.line(fx + 0.025, 0.30, fx + 0.105, 0.30, 0.014, RED if i % 2 else BLUE)
    # row of heads and shoulders
    skins = [SKIN1, SKIN2, SKIN3, SKIN1, SKIN2]
    shirts = [BLUE, RED, GREEN, TEAL, GOLD]
    for i in range(5):
        fx = 0.10 + i * 0.20
        s.disc(fx, 0.78, 0.055, skins[i])
        s.rect(fx - 0.075, 0.86, fx + 0.075, 1.0, shirts[i])


def scene_warship(s):
    s.rect(0, 0, 1, 0.72, NIGHT)
    s.rect(0, 0.72, 1, 1, (20, 48, 84))
    s.disc(0.84, 0.16, 0.07, (225, 228, 235))  # moon
    # corvette listing slightly
    s.poly([(0.14, 0.66), (0.60, 0.60), (0.66, 0.66), (0.60, 0.74),
            (0.18, 0.76)], (120, 122, 126))
    s.rect(0.30, 0.52, 0.44, 0.62, (100, 102, 106))
    s.line(0.52, 0.58, 0.52, 0.44, 0.012, (100, 102, 106))
    # explosion with amber core and smoke
    s.disc(0.66, 0.58, 0.09, FLAME)
    s.disc(0.66, 0.58, 0.05, AMBER)
    s.disc(0.70, 0.46, 0.045, (150, 148, 144))
    s.disc(0.62, 0.44, 0.04, (150, 148, 144))
    # sea drone approaching with a wake
    s.disc(0.82, 0.82, 0.03, AMBER)
    s.line(0.70, 0.82, 0.79, 0.82, 0.012, WHITE)


def scene_cargo(s):
    s.rect(0, 0, 1, 0.74, SEA)
    s.rect(0, 0.74, 1, 1, (110, 150, 175))
    s.line(0.0, 0.80, 1.0, 0.80, 0.012, WHITE)
    # cargo hull
    s.poly([(0.10, 0.58), (0.86, 0.58), (0.80, 0.74), (0.16, 0.74)], (120, 82, 52))
    # three containers
    s.rect(0.18, 0.38, 0.34, 0.58, RED)
    s.rect(0.36, 0.38, 0.52, 0.58, GREEN)
    s.rect(0.54, 0.38, 0.70, 0.58, (220, 190, 40))
    # mast with a small red flag
    s.line(0.80, 0.58, 0.80, 0.24, 0.012, INK)
    s.poly([(0.80, 0.24), (0.88, 0.27), (0.80, 0.31)], RED)
    # flame and smoke at the bow
    s.poly([(0.10, 0.58), (0.14, 0.34), (0.18, 0.58)], FLAME)
    s.disc(0.14, 0.30, 0.045, (150, 148, 144))
    s.disc(0.18, 0.22, 0.035, (150, 148, 144))


def scene_ballot(s):
    s.rect(0, 0, 1, 1, BEIGE)
    # ballot box with darker lid and slot
    s.rect(0.28, 0.52, 0.72, 0.94, BLUE)
    s.rect(0.24, 0.44, 0.76, 0.54, (20, 48, 90))
    s.rect(0.42, 0.47, 0.58, 0.51, INK)
    # ballot paper going into the slot
    s.poly([(0.44, 0.48), (0.56, 0.48), (0.58, 0.10), (0.46, 0.10)], WHITE)
    frame(s.X(0.44), s.Y(0.10), 0.14 * s.w, 0.38 * s.h, LIGHTGREY, 1)
    # red check mark on the paper
    s.line(0.48, 0.26, 0.51, 0.32, 0.02, RED)
    s.line(0.51, 0.32, 0.57, 0.16, 0.02, RED)


def scene_scroll(s):
    s.rect(0, 0, 1, 1, (242, 236, 222))
    # scroll: white document, brown frame, gold side rods
    s.rect(0.22, 0.12, 0.78, 0.88, WHITE)
    frame(s.X(0.22), s.Y(0.12), 0.56 * s.w, 0.76 * s.h, BROWN, 2)
    s.rect(0.16, 0.08, 0.22, 0.92, GOLD)
    s.rect(0.78, 0.08, 0.84, 0.92, GOLD)
    for i, gy in enumerate((0.24, 0.34, 0.44, 0.54)):
        s.line(0.28, gy, 0.72, gy, 0.012, INK)
    s.text("LAW", 0.40, 0.64, 9, RED, 0.16)


def scene_care(s):
    s.rect(0, 0, 1, 1, PALE_GREEN)
    # elder in blue-grey and child in red-orange, holding hands
    s.disc(0.38, 0.30, 0.075, (110, 120, 140))
    s.poly([(0.30, 0.92), (0.32, 0.42), (0.44, 0.42), (0.46, 0.92)], (110, 120, 140))
    s.disc(0.62, 0.44, 0.06, (220, 100, 60))
    s.poly([(0.56, 0.92), (0.57, 0.54), (0.67, 0.54), (0.68, 0.92)], (220, 100, 60))
    # joined hands
    s.line(0.44, 0.62, 0.57, 0.62, 0.02, SKIN1)
    s.disc(0.505, 0.62, 0.025, SKIN1)
    # small red heart above them
    s.disc(0.47, 0.12, 0.03, RED)
    s.disc(0.53, 0.12, 0.03, RED)
    s.poly([(0.44, 0.13), (0.56, 0.13), (0.50, 0.22)], RED)


def scene_gavel(s):
    s.rect(0, 0, 1, 1, (242, 236, 222))
    # bench
    s.rect(0.10, 0.78, 0.90, 0.92, (120, 84, 52))
    # gavel head and handle
    s.rect(0.30, 0.52, 0.56, 0.68, BROWN)
    s.line(0.56, 0.60, 0.78, 0.72, 0.03, BROWN)
    # sounding block
    s.rect(0.62, 0.70, 0.74, 0.78, (90, 62, 38))
    # red sound lines
    s.line(0.82, 0.52, 0.88, 0.46, 0.016, RED)
    s.line(0.84, 0.62, 0.90, 0.62, 0.016, RED)
    s.text("WARRANT", 0.05, 0.06, 9, RED, 0.16)


def scene_cricket(s):
    s.rect(0, 0, 1, 1, PALE_GREEN)
    # pitch strip down the middle
    s.rect(0.44, 0.0, 0.58, 1.0, (232, 220, 180))
    # three yellow stumps at the bottom
    for fx in (0.46, 0.505, 0.55):
        s.rect(fx, 0.72, fx + 0.018, 0.94, (220, 190, 40))
    s.rect(0.46, 0.70, 0.57, 0.73, (220, 190, 40))
    # bat and red ball with a motion line
    s.poly([(0.20, 0.30), (0.26, 0.28), (0.34, 0.55), (0.30, 0.60),
            (0.22, 0.55)], (150, 110, 70))
    s.line(0.16, 0.30, 0.22, 0.28, 0.02, (150, 110, 70))
    s.disc(0.70, 0.30, 0.035, RED)
    s.line(0.60, 0.30, 0.66, 0.30, 0.014, RED)
    s.text("128", 0.05, 0.06, 11, RED, 0.16)


def scene_sensex(s):
    s.rect(0, 0, 1, 1, (242, 236, 222))
    # white chart panel with a thin grey frame
    s.rect(0.06, 0.14, 0.94, 0.90, WHITE)
    frame(s.X(0.06), s.Y(0.14), 0.88 * s.w, 0.76 * s.h, LIGHTGREY, 1)
    # eight bars falling left to right: first green, then red
    for i in range(8):
        fx = 0.11 + i * 0.105
        top = 0.22 + i * 0.065
        col = GREEN if i == 0 else RED
        s.rect(fx, top, fx + 0.06, 0.84, col)
    s.text("-1,484", 0.62, 0.16, 9, RED, 0.16)


def scene_tehran(s):
    s.rect(0, 0, 1, 1, PALE_TAN)
    # grey dome silhouette with a small minaret (left side)
    s.poly([(0.06, 0.92), (0.06, 0.72), (0.10, 0.60), (0.16, 0.52),
            (0.22, 0.60), (0.26, 0.72), (0.26, 0.92)], (120, 118, 112))
    s.rect(0.28, 0.66, 0.32, 0.92, (120, 118, 112))
    s.disc(0.30, 0.62, 0.02, (120, 118, 112))
    # warning triangle, ENTIRELY inside the band
    s.poly([(0.60, 0.10), (0.86, 0.88), (0.34, 0.88)], AMBER)
    s.rect(0.585, 0.36, 0.615, 0.62, INK)
    s.disc(0.60, 0.72, 0.022, INK)


TILE_SCENES = [scene_train, scene_fire, scene_protest, scene_warship,
               scene_cargo, scene_ballot, scene_scroll, scene_care,
               scene_gavel, scene_cricket, scene_sensex, scene_tehran]
LEAD_SCENES = [scene_kyiv, scene_cop, scene_markets]

# --------------------------------------------------------------------- data
MX = 28            # left margin
CW = 968           # content width
RX = MX + CW       # right edge (996)
EMDASH = "\u2014"
MIDOT = "\u00b7"

TOP_STRIP = ("THE WORLD IN ONE DAY  " + MIDOT + "  36 STORIES  " + MIDOT +
             "  7 REGIONS  " + MIDOT +
             "  EVERY ONE DATED TUESDAY 24 NOVEMBER 2026")
MASTHEAD = "Tuesday 24 November 2026"
SUBHEAD = ("Kyiv hit again as the war reaches Libya's shores  " + MIDOT +
           "  COP31's collapse sinks in  " + MIDOT +
           "  Trump blames Democrats for the $6tn rout")

NUMBERS = [
    ("$6tn", "market value lost since the US midterms"),
    ("15,000", "Rs crore in India's Nepal package"),
    ("1,484", "points lost by the Sensex"),
    ("300", "on shift at the Serang factory"),
    ("128", "Pant's runs in Wellington"),
    ("24", "dead in the Serang factory fire"),
]

REGIONS = [
    ("EUROPE 7", BLUE), ("MIDDLE EAST 1", RED), ("AMERICAS 7", TEAL),
    ("ASIA-PACIFIC 17", GOLD), ("AFRICA 2", GREEN), ("OCEANIA 1", PURPLE),
    ("WORLD 1", GREY),
]

LEADS = [
    ("1 " + MIDOT + " KYIV REGION, UKRAINE " + EMDASH + " WAR",
     "Russian drones hit Kyiv region; several missing",
     "Air defences down most of the drones, but a five-storey block near "
     "Kyiv is hit and 11 people are killed, police say.",
     scene_kyiv),
    ("2 " + MIDOT + " ANTALYA AFTERMATH " + EMDASH + " CLIMATE",
     "COP31's collapse sinks in: 130 nations vow to act alone",
     "Two days after the talks collapsed with no mention of fossil fuels, "
     "130 nations vow to push a phase-out outside the UN process.",
     scene_cop),
    ("3 " + MIDOT + " WASHINGTON " + EMDASH + " MARKETS",
     "Trump blames Democrats for $6tn market rout",
     "On Truth Social he calls the rout since the midterms '100% the "
     "Democrats' fault'. The Nasdaq is down 10% in a week.",
     scene_markets),
]

TILES = [
    (4, "NEW DELHI", "INDIA / NEPAL",
     "Modi, Shah open rail link to Nepal",
     "Modi and Nepal PM Shah flag off the Saryu-Kamala Express; 8 MoUs signed."),
    (5, "CIKANDE, INDONESIA", "FIRE",
     "Candy-factory fire: 24 dead, 30 missing",
     "Search goes on in the unstable ruin; DNA tests will take weeks."),
    (6, "LISBON", "PROTEST",
     "Thousands march on living costs",
     "Streets fill as prices bite; unions demand relief as living costs climb."),
    (7, "BENGHAZI, LIBYA", "FALLOUT",
     "UN seeks probe into warship strike",
     "Kyiv claims it sank the corvette Merkury with seven sea drones on Sunday."),
    (8, "GULF OF FINLAND", "SEA",
     "Russian cargo ship still burning",
     "Hit by drones in the Baltic, the Sparta II drifts; Finland leads rescue."),
    (9, "SEOUL", "POLITICS",
     "Seoul names new ministers",
     "The president names a new foreign minister and intelligence chief."),
    (10, "YEREVAN", "CONSTITUTION",
     "Armenia proposes new constitution",
     "Yerevan tables a new constitution, a step toward peace with Azerbaijan."),
    (11, "BEIJING", "WELFARE",
     "China sets 2030 care targets",
     "Beijing sets 2030 targets to strengthen elderly care and childcare."),
    (12, "DHAKA", "POLITICS",
     "Bangladesh vows to arrest Hasina",
     "Dhaka says it will arrest the former prime minister if she returns."),
    (13, "WELLINGTON", "CRICKET",
     "Pant's 128 as Test ends in draw",
     "Pant hits 128, a record for an Asian keeper, as the Test ends in a draw."),
    (14, "MUMBAI", "MARKETS",
     "Sensex falls 1,484 points",
     "The Sensex falls 1,484 to 82,435 and the Nifty drops 451 as tech slides."),
    (15, "TEHRAN", "NUCLEAR",
     "Trump warns Iran of 'traumatic' outcome",
     "Trump warns of a 'very traumatic' outcome if no nuclear deal is reached."),
]

ALSO = [
    (16, "NAYPYIDAW", "Junta calls ASEAN move unfair"),
    (17, "WASHINGTON", "Trump: bring back Jensen Huang"),
    (18, "OTTAWA", "Carney laughs at Trump lookalike"),
    (19, "NEW DELHI", "Court warrant for Dhruv Rathee"),
    (20, "NEW DELHI", "FSSAI acts on Bisleri water"),
    (21, "WASHINGTON", "Senate to vote on $9.4bn cuts"),
    (22, "TOKYO", "Japan trade deal; Nikkei rallies"),
    (23, "JAKARTA", "Indonesia trade deal sealed"),
    (24, "MOSCOW", "Putin pledges free grain to Africa"),
    (25, "MADRID", "Ferrari unveils two new 296s"),
    (26, "NEW DELHI", "SpiceJet crisis deepens"),
    (27, "NEW DELHI", "Oil import bill up 60% in Oct"),
    (28, "SENEGAL", "Migrant boat capsizes; 4 dead"),
    (29, "CALIFORNIA", "Waymo pulls freeway robotaxis"),
    (30, "SHENZHEN", "Trump, Xi, Putin to meet at APEC"),
    (31, "TOKYO", "SoftBank to invest $2bn in Intel"),
    (32, "BANGKOK", "Thai-Cambodia truce holds"),
    (33, "DHAKA", "Mass typhoid vaccination begins"),
    (34, "NEW YORK", "Two die in varsity shooting"),
    (35, "WASHINGTON", "Citizenship, H-1B tests change"),
    (36, "MOSCOW", "Kremlin 'takes note' of Libya claim"),
]

DATE_CHECK = ("Left out because they happened on earlier days: COP31 collapse "
              "(Sun 22 Nov) " + MIDOT + " Merkury sunk (Sun 22 Nov) " + MIDOT +
              " Serang fire breaks out (Sat 21 Nov) " + MIDOT +
              " Verstappen wins Las Vegas GP (Sun 22 Nov) " + MIDOT +
              " Hong Kong turnout (Sun 22 Nov) " + MIDOT +
              " Gaza: four killed (Sun 22 Nov) " + MIDOT +
              " Nov 5 rout, -$2.8tn (Thu 5 Nov)")

FOOTER = ("Sources: Reuters " + MIDOT + " AP " + MIDOT + " AFP " + MIDOT +
          " BBC " + MIDOT + " The Guardian " + MIDOT + " CNN " + MIDOT +
          " WSJ " + MIDOT + " Le Monde " + EMDASH +
          " wires read to press time 04:00 WIB, Tue 24 Nov 2026 " + MIDOT +
          " Scenes are drawn illustrations")

CONTINENTS = [
    [(-168, 66), (-140, 70), (-120, 71), (-100, 68), (-85, 66), (-75, 62),
     (-60, 55), (-55, 47), (-70, 42), (-75, 35), (-80, 26), (-90, 21),
     (-97, 16), (-105, 20), (-115, 28), (-125, 40), (-125, 49), (-140, 60),
     (-158, 58), (-168, 66)],
    [(-80, 10), (-70, 12), (-60, 8), (-52, 5), (-42, -5), (-35, -9),
     (-40, -20), (-48, -28), (-58, -35), (-65, -42), (-70, -52), (-73, -40),
     (-72, -25), (-78, -12), (-80, 2), (-80, 10)],
    [(-17, 15), (-10, 30), (0, 36), (10, 37), (20, 32), (30, 31), (35, 28),
     (43, 12), (51, 11), (48, 0), (40, -10), (36, -20), (32, -29),
     (20, -35), (12, -18), (12, -6), (8, 4), (-8, 5), (-17, 15)],
    [(-10, 36), (-9, 43), (-2, 48), (0, 51), (5, 53), (8, 57), (12, 55),
     (18, 56), (21, 59), (24, 60), (28, 62), (32, 70), (45, 68), (60, 69),
     (75, 73), (90, 75), (105, 77), (120, 73), (135, 72), (150, 70),
     (162, 66), (170, 66), (162, 60), (156, 52), (142, 50), (140, 40),
     (132, 35), (127, 34), (122, 30), (120, 23), (110, 20), (105, 9),
     (100, 7), (97, 15), (92, 21), (88, 22), (80, 13), (77, 8), (72, 20),
     (66, 25), (60, 25), (55, 26), (50, 29), (48, 30), (44, 29), (40, 31),
     (35, 36), (30, 36), (26, 38), (22, 37), (19, 40), (15, 44), (12, 44),
     (8, 44), (3, 43), (0, 40), (-2, 37), (-9, 37), (-10, 36)],
    [(114, -22), (122, -14), (132, -12), (137, -15), (142, -11), (146, -19),
     (150, -23), (153, -27), (150, -37), (145, -38), (140, -38), (136, -35),
     (132, -32), (126, -32), (118, -35), (114, -30), (114, -22)],
]

PINS = [(-95, 39, 3), (-100, 45, 17), (-45, -15, 15), (-3, 54, 6),
        (10, 45, 25), (19, 52, 8), (30, 50, 1), (45, 40, 10), (51, 35, 15),
        (78, 21, 4), (90, 24, 12), (100, 13, 32), (107, -6, 5),
        (121, 31, 11), (127, 36, 9), (133, -25, 13), (44, 15, 7),
        (-17, 14, 28)]


# ------------------------------------------------------------------ checker
TEXT_BLOCKS = []   # (description, box_bottom, text_bottom)
SCENE_LOG = []     # (description, band, extent, dropped_delta)


def note_text(desc, box_bottom, bottom):
    TEXT_BLOCKS.append((desc, box_bottom, bottom))


def note_scene(desc, band, extent, dropped_delta):
    SCENE_LOG.append((desc, band, extent, dropped_delta))


def run_checker():
    issues = []
    for (desc, box_bottom, bottom) in TEXT_BLOCKS:
        if bottom > box_bottom - 4:
            issues.append("%s: text ends at %d, box bottom %d (needs 4px "
                          "clearance)" % (desc, bottom, box_bottom))
        if bottom > H or bottom < 0:
            issues.append("%s: text outside canvas (%d)" % (desc, bottom))
    for (desc, band, ext, dropped) in SCENE_LOG:
        bx, by, bw, bh = band
        if dropped:
            issues.append("%s: %d pixels refused by the clip" % (desc, dropped))
        if ext[2] < 0:
            continue
        if (ext[0] < bx or ext[1] < by or ext[2] > bx + bw - 1
                or ext[3] > by + bh - 1):
            issues.append("%s: scene pixels escape band %s (extent %s)"
                          % (desc, band, ext))
    if dropped_count():
        issues.append("total clipped pixels refused: %d" % dropped_count())
    return issues


def draw_scene_checked(desc, band, painter):
    before = dropped_count()
    ext = draw_scene(band, painter)
    note_scene(desc, band, ext, dropped_count() - before)
    frame(band[0], band[1], band[2], band[3], RULE, 1)


# -------------------------------------------------------------------- page
def build_page():
    _fill_paper()
    y = 0

    # 1. Top strip
    rect(0, 0, W, 26, NAVY)
    strip_cap = fit_cap(TOP_STRIP, 13, 960)
    draw_text(TOP_STRIP, MX, (26 - strip_cap) / 2.0, strip_cap, WHITE, 0.12,
              "center", CW)
    y = 26

    # 2. Masthead: refined serif face, thin strokes, serif ticks.
    date_top = y + 7
    date_cap = fit_cap(MASTHEAD, 55, CW)
    draw_text(MASTHEAD, MX, date_top, date_cap, INK, 0.09, "center", CW,
              serif=True)
    rule_y = date_top + date_cap + 8
    rect(MX, rule_y, RX, rule_y + 3, RED)
    sub_cap = fit_cap(SUBHEAD, 17, CW)
    sub_top = rule_y + 3 + 5
    draw_text(SUBHEAD, MX, sub_top, sub_cap, RED, 0.12, "center", CW)
    dark_y = int(math.floor(sub_top + sub_cap + 6))
    rect(MX, dark_y, RX, dark_y + 2, RULE)
    y = dark_y + 2

    # 3. Numbers row
    y += 6
    num_top = y
    col_w = CW / 6.0
    cap_bottom = num_top
    for i, (num, cap_text) in enumerate(NUMBERS):
        cx = MX + i * col_w
        draw_text(num, cx, num_top, 28, RED, 0.14, "center", col_w)
        bottom, _c, _n = draw_wrapped(cap_text, cx + 5, num_top + 28 + 5,
                                      10.5, col_w - 10, GREY, 0.12,
                                      max_lines=2)
        cap_bottom = max(cap_bottom, bottom)
        if i:
            vline(cx, num_top, cap_bottom, LIGHTGREY, 1)
    rule_y = int(math.floor(cap_bottom)) + 5
    rect(MX, rule_y, RX, rule_y + 2, RULE)
    y = rule_y + 2

    # 4. Region bar
    y += 4
    bar_h = 24
    seg_w = CW / 7.0
    for i, (label, col) in enumerate(REGIONS):
        rect(MX + i * seg_w, y, MX + (i + 1) * seg_w, y + bar_h, col)
        cap = fit_cap(label, 12, seg_w - 8)
        draw_text(label, MX + i * seg_w, y + (bar_h - cap) / 2.0, cap,
                  WHITE, 0.12, "center", seg_w)
    y += bar_h

    # 5. Three lead stories
    y += 4
    lead_w = 308
    lead_gap = 12
    section_bottom = y
    for i, (kicker, headline, body, painter) in enumerate(LEADS):
        lx = MX + i * (lead_w + lead_gap)
        band = (lx, y, lead_w, 100)
        draw_scene_checked("lead %d scene" % (i + 1), band, painter)
        k_top = y + 100 + 4
        draw_text(kicker, lx, k_top, 10.5, RED, 0.14)
        h_top = k_top + 10.5 + 3
        h_bottom, _c, _n = draw_wrapped(headline, lx, h_top, 19, lead_w,
                                        INK, 0.14, max_lines=3)
        b_top = h_bottom + 3
        b_bottom, _c, _n = draw_wrapped(body, lx, b_top, 11.5, lead_w,
                                        INK, 0.12, max_lines=3)
        note_text("lead %d body" % (i + 1), y + 100 + 4 + 10.5 + 3 +
                  3 * 19 * 1.32 + 3 + 3 * 11.5 * 1.32, b_bottom)
        section_bottom = max(section_bottom, b_bottom)
    rule_y = int(math.floor(section_bottom)) + 6
    rect(MX, rule_y, RX, rule_y + 2, RULE)
    y = rule_y + 2

    # 6. Twelve illustrated tiles: 4 columns x 3 rows, row height 112.
    y += 4
    tile_w = (CW - 3 * 12) / 4.0
    tile_h = 112
    for row in range(3):
        for col in range(4):
            idx = row * 4 + col
            num, place, tag, headline, body = TILES[idx]
            tx = MX + col * (tile_w + 12)
            ty = y + row * (tile_h + 3)
            band = (tx, ty, tile_w, 40)
            draw_scene_checked("tile %d scene" % num, band,
                               TILE_SCENES[idx])
            kicker = "%d %s %s %s" % (num, MIDOT, place, EMDASH + " " + tag)
            k_top = ty + 40 + 4
            k_cap = fit_cap(kicker, 9, tile_w)
            draw_text(kicker, tx, k_top, k_cap, RED, 0.14)
            h_top = k_top + k_cap + 3
            h_bottom, _c, _n = draw_wrapped(headline, tx, h_top, 12.5,
                                            tile_w, INK, 0.14, max_lines=2)
            b_top = h_bottom + 2
            b_bottom, _c, _n = draw_wrapped(body, tx, b_top, 10, tile_w,
                                            INK, 0.12, max_lines=2,
                                            max_bottom=ty + tile_h - 4)
            note_text("tile %d text" % num, ty + tile_h, b_bottom)
    y += 3 * tile_h + 2 * 3

    # 7. World map plus ALSO list
    y += 4
    map_x = MX
    map_w = 380
    map_h = 126
    title_y = y
    draw_text("WHERE IT HAPPENED", map_x, title_y, 11, NAVY, 0.14)
    draw_text("pins = story numbers", map_x, title_y, 9.5, GREY, 0.12,
              "right", map_w)
    map_y = title_y + 12
    rect(map_x, map_y, map_x + map_w, map_y + map_h, SKY)

    def proj(lon, lat):
        return (map_x + (lon + 170) / 360.0 * map_w,
                map_y + (78 - lat) / 136.0 * map_h)

    for lon in range(-150, 181, 30):
        x0, _ = proj(lon, 0)
        vline(x0, map_y, map_y + map_h, WHITE, 1)
    for lat in range(-40, 61, 20):
        _, y0 = proj(0, lat)
        hline(map_x, map_x + map_w, y0, WHITE, 1)
    for cont in CONTINENTS:
        polygon([proj(lon, lat) for (lon, lat) in cont], LAND)
    for (lon, lat, n) in PINS:
        px, py = proj(lon, lat)
        disc(px, py, 7.5, WHITE)
        disc(px, py, 6, RED)
        draw_text(str(n), px - 7, py - 3.25, 6.5, WHITE, 0.14, "center", 14)
    map_bottom = map_y + map_h

    also_x = map_x + map_w + 16
    also_w = RX - also_x
    draw_text("ALSO ON TUESDAY 24 NOVEMBER " + EMDASH + " 21 MORE STORIES",
              also_x, title_y, 12, RED, 0.14)
    rect(also_x, title_y + 12, RX, title_y + 14, RED)
    col_w = (also_w - 12) / 2.0
    also_cap = 10.0
    items = ["%d %s %s %s" % (n, place, EMDASH, text)
             for (n, place, text) in ALSO]
    while also_cap > 7.5 and any(text_width(s, also_cap) > col_w
                                 for s in items):
        also_cap -= 0.5
    also_top = title_y + 18
    also_bottom = also_top
    for i, s in enumerate(items):
        c = i // 11
        r = i % 11
        draw_text(s, also_x + c * (col_w + 12), also_top + r * 11.5,
                  also_cap, INK, 0.12)
        also_bottom = max(also_bottom, also_top + r * 11.5 + also_cap)
    y = int(math.floor(max(map_bottom, also_bottom)))

    # 8. DATE CHECK
    y += 4
    label = "DATE CHECK"
    label_cap = 11
    label_w = text_width(label, label_cap)
    inner_x = MX + 8
    inner_w = CW - 16
    first_w = inner_w - label_w - 10
    # wrap with a narrower first line (the label sits to its left)
    words = DATE_CHECK.split(" ")
    lines = []
    cur = ""
    limit = first_w
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, 10) <= limit or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
            limit = inner_w
    if cur:
        lines.append(cur)
    box_h = 6 + len(lines) * 13 + 6
    frame(MX, y, CW, box_h, RED, 2)
    draw_text(label, inner_x, y + 6, label_cap, RED, 0.14)
    for i, ln in enumerate(lines):
        lx = inner_x + label_w + 10 if i == 0 else inner_x
        draw_text(ln, lx, y + 6 + i * 13, 10, INK, 0.12)
    y += box_h

    # 9. Footer
    y += 4
    foot_cap = fit_cap(FOOTER, 10, CW)
    draw_text(FOOTER, MX, y, foot_cap, GREY, 0.12, "center", CW)
    y += foot_cap
    note_text("footer", H, y)


# --------------------------------------------------------------------- main
def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    build_page()
    issues = run_checker()
    print("layout checker: %d issue(s)" % len(issues))
    for issue in issues:
        print("  - " + issue)
    if issues:
        return 1
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path)
    print("wrote %s (%d bytes)" % (path, size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
