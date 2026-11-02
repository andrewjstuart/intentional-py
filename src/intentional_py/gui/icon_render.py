"""Pure-stdlib rendering of the Intentional icon (a speech bubble around a
boxed checkmark, simplified from ``assets/icon-logo.png``) at any size and
accent color. The bubble's own outline keeps the reference logo's rainbow
sweep regardless of accent; only the cube and checkmark badge follow it.
Shared by ``assets/generate_icon.py`` (the static .ico/.png/favicon family,
baked at the default "blue" accent) and the GUI's window icon, which calls
:func:`render_png` again whenever the user picks a different accent so the
taskbar/title-bar icon matches (see ``gui/app.py``'s
``_window_icon``/``_set_accent``). No imaging library dependency: shapes are
antialiased by supersampling a handful of points per pixel.

All shape coordinates are in a fixed 64x64 design space, scaled to the
requested pixel size.
"""

from __future__ import annotations

import colorsys
import math
import struct
import zlib

Color = tuple[int, int, int]

WHITE: Color = (255, 255, 255)

# Speech bubble: a rounded-rect outline with a small tail, matching the
# reference logo's silhouette.
_BUBBLE_CX, _BUBBLE_CY = 32.0, 27.0
_BUBBLE_W, _BUBBLE_H = 56.0, 42.0
_BUBBLE_RADIUS = 12.0
_STROKE_WIDTH = 3.4
_TAIL = ((18.0, 48.0), (10.0, 60.0))

# Isometric cube (the "box" in "boxed checkmark"), three shaded faces meeting
# at a center point and a bottom tip.
_CUBE_T = (28.0, 16.0)
_CUBE_RT = (41.0, 22.5)
_CUBE_LT = (15.0, 22.5)
_CUBE_M = (28.0, 29.0)
_CUBE_BL = (15.0, 35.5)
_CUBE_BR = (41.0, 35.5)
_CUBE_B = (28.0, 42.0)
_CUBE_TOP = (_CUBE_T, _CUBE_RT, _CUBE_M, _CUBE_LT)
_CUBE_LEFT = (_CUBE_LT, _CUBE_M, _CUBE_B, _CUBE_BL)
_CUBE_RIGHT = (_CUBE_M, _CUBE_RT, _CUBE_BR, _CUBE_B)

# The checkmark badge, overlapping the cube's bottom-right corner.
_BADGE_CENTER = (46.0, 40.0)
_BADGE_RADIUS = 10.0
_CHECK_P1, _CHECK_P2, _CHECK_P3 = (42.0, 40.0), (45.0, 43.0), (51.0, 35.0)
_CHECK_STROKE = 2.8

_DESIGN_SIZE = 64.0


def _lighten(rgb: Color, amount: float) -> Color:
    return tuple(round(c + (255 - c) * amount) for c in rgb)  # type: ignore[return-value]


def _darken(rgb: Color, amount: float) -> Color:
    return tuple(round(c * (1 - amount)) for c in rgb)  # type: ignore[return-value]


def _rainbow_rgb(px: float, py: float) -> Color:
    """A fixed conic rainbow sweep around the bubble's center - the reference
    logo's colorful border, independent of the accent picker on purpose."""
    angle = math.atan2(py - _BUBBLE_CY, px - _BUBBLE_CX)
    hue = ((angle + math.pi) / (2 * math.pi)) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.78, 0.95)
    return (round(r * 255), round(g * 255), round(b * 255))


def _segment_distance(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    """Distance from point (px, py) to the segment a->b."""
    abx, aby = bx - ax, by - ay
    length_sq = abx * abx + aby * aby
    t = (
        0.0
        if length_sq == 0
        else max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / length_sq))
    )
    cx, cy = ax + t * abx, ay + t * aby
    return math.hypot(px - cx, py - cy)


def _in_segment_stroke(
    px: float, py: float, ax: float, ay: float, bx: float, by: float, width: float
) -> bool:
    return _segment_distance(px, py, ax, ay, bx, by) <= width / 2


def _in_rounded_rect_stroke(px: float, py: float) -> bool:
    dx = max(abs(px - _BUBBLE_CX) - (_BUBBLE_W / 2 - _BUBBLE_RADIUS), 0.0)
    dy = max(abs(py - _BUBBLE_CY) - (_BUBBLE_H / 2 - _BUBBLE_RADIUS), 0.0)
    distance = math.hypot(dx, dy) - _BUBBLE_RADIUS
    return -_STROKE_WIDTH <= distance <= 0


def _in_circle(px: float, py: float, cx: float, cy: float, radius: float) -> bool:
    return math.hypot(px - cx, py - cy) <= radius


def _point_in_polygon(
    px: float, py: float, poly: tuple[tuple[float, float], ...]
) -> bool:
    inside = False
    count = len(poly)
    for i in range(count):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % count]
        if (ay > py) != (by > py):
            x_at_y = (bx - ax) * (py - ay) / (by - ay) + ax
            if px < x_at_y:
                inside = not inside
    return inside


def _blend(
    color: tuple[float, float, float], alpha: float, shape_color: Color, coverage: float
) -> tuple[tuple[float, float, float], float]:
    if coverage <= 0:
        return color, alpha
    blended = tuple(
        color[i] * (1 - coverage) + shape_color[i] * coverage for i in range(3)
    )
    return blended, alpha + coverage * (1 - alpha)


def render_rgba(size: int, accent: Color) -> bytes:
    """RGBA pixel bytes (row-major, no filtering) for one icon size/accent."""
    scale = size / _DESIGN_SIZE
    light = _lighten(accent, 0.38)
    dark = _darken(accent, 0.32)
    # fewer supersamples at the largest sizes keeps a full SIZES run reasonably fast
    supersamples = 4 if size <= 128 else 2
    offsets = [(i + 0.5) / supersamples for i in range(supersamples)]
    total = supersamples * supersamples

    pixels = bytearray()
    for y in range(size):
        for x in range(size):
            rainbow = _rainbow_rgb((x + 0.5) / scale, (y + 0.5) / scale)
            outline_hits = top_hits = left_hits = right_hits = 0
            badge_hits = check_hits = 0
            for oy in offsets:
                py = (y + oy) / scale
                for ox in offsets:
                    px = (x + ox) / scale
                    if _in_rounded_rect_stroke(px, py) or _in_segment_stroke(
                        px, py, *_TAIL[0], *_TAIL[1], _STROKE_WIDTH
                    ):
                        outline_hits += 1
                    if _point_in_polygon(px, py, _CUBE_TOP):
                        top_hits += 1
                    elif _point_in_polygon(px, py, _CUBE_LEFT):
                        left_hits += 1
                    elif _point_in_polygon(px, py, _CUBE_RIGHT):
                        right_hits += 1
                    if _in_circle(px, py, *_BADGE_CENTER, _BADGE_RADIUS):
                        badge_hits += 1
                        if _in_segment_stroke(
                            px, py, *_CHECK_P1, *_CHECK_P2, _CHECK_STROKE
                        ) or _in_segment_stroke(
                            px, py, *_CHECK_P2, *_CHECK_P3, _CHECK_STROKE
                        ):
                            check_hits += 1

            color: tuple[float, float, float] = (0.0, 0.0, 0.0)
            alpha = 0.0
            color, alpha = _blend(color, alpha, rainbow, outline_hits / total)
            color, alpha = _blend(color, alpha, light, top_hits / total)
            color, alpha = _blend(color, alpha, accent, left_hits / total)
            color, alpha = _blend(color, alpha, dark, right_hits / total)
            color, alpha = _blend(color, alpha, accent, badge_hits / total)
            color, alpha = _blend(color, alpha, WHITE, check_hits / total)
            pixels += bytes(
                (round(color[0]), round(color[1]), round(color[2]), round(255 * alpha))
            )
    return bytes(pixels)


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data))
    )


def encode_png(size: int, rgba: bytes) -> bytes:
    raw = bytearray()
    stride = size * 4
    for row in range(size):
        raw += b"\x00"  # filter type 0 (none) per scanline
        raw += rgba[row * stride : (row + 1) * stride]
    ihdr = struct.pack(
        ">IIBBBBB", size, size, 8, 6, 0, 0, 0
    )  # 8-bit RGBA, no interlace
    idat = zlib.compress(bytes(raw), level=9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def render_png(size: int, accent: Color) -> bytes:
    """A PNG-encoded icon, ready for ``tk.PhotoImage(data=...)`` or writing to disk."""
    return encode_png(size, render_rgba(size, accent))
