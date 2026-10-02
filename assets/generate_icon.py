"""Generates the project's simple icon (assets/icon.png, assets/icon.ico) and
copies a web-sized favicon into web/. Not part of the package: a one-off/
occasionally-rerun tool, kept here so the icon can be regenerated or restyled
without needing an image editor. Uses only the standard library on purpose, so
building the icon doesn't require adding an imaging library as a project
dependency.

Run: python assets/generate_icon.py
"""

from __future__ import annotations

import math
import shutil
import struct
import zlib
from pathlib import Path

ASSETS_DIR = Path(__file__).parent
WEB_DIR = ASSETS_DIR.parent / "web"
# the GUI loads its window icon from inside the installable package (works from
# source, frozen, or pip-installed), rather than from this repo-root folder
GUI_PACKAGE_DIR = ASSETS_DIR.parent / "src" / "intentional_py" / "gui"

# Matches CustomTkinter's default accent blue, so the icon looks at home next
# to the GUI's own buttons.
BACKGROUND = (31, 106, 165, 255)  # #1F6AA5
MARK = (255, 255, 255, 255)  # white checkmark, echoing the ✔ used throughout
# the CLI/GUI output tables (rich_reporter.py's _OK, gui/actions.py's detail_tables)

SIZES = (16, 24, 32, 48, 64, 128, 256)


def _rounded_rect_mask(x: float, y: float, size: int, radius: float) -> float:
    """1.0 inside a rounded square of the given size/corner radius, 0.0 outside,
    with a one-pixel-ish antialiased edge in between."""
    half = size / 2
    dx = max(abs(x - half) - (half - radius), 0.0)
    dy = max(abs(y - half) - (half - radius), 0.0)
    dist = math.hypot(dx, dy) - radius
    return _edge(dist)


def _edge(signed_distance: float) -> float:
    """Antialiasing falloff: >=1 inside, 0 outside, smooth across ~1px."""
    return max(0.0, min(1.0, 0.5 - signed_distance))


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


def _checkmark_coverage(x: float, y: float, size: int) -> float:
    """1.0 on a checkmark stroke scaled to the icon size, 0.0 off it."""
    scale = size / 64
    stroke = 5.0 * scale
    # three points describing the two segments of a check, in 64x64 space
    p1 = (18.0 * scale, 34.0 * scale)
    p2 = (27.0 * scale, 43.0 * scale)
    p3 = (47.0 * scale, 20.0 * scale)
    distance = min(
        _segment_distance(x, y, *p1, *p2),
        _segment_distance(x, y, *p2, *p3),
    )
    return _edge(distance - stroke / 2)


def _render(size: int) -> bytes:
    """RGBA pixel bytes (row-major, no filtering) for one icon size."""
    radius = size * 0.22
    pixels = bytearray()
    for y in range(size):
        for x in range(size):
            # sample the pixel center for a touch of antialiasing
            bg_coverage = _rounded_rect_mask(x + 0.5, y + 0.5, size, radius)
            mark_coverage = (
                _checkmark_coverage(x + 0.5, y + 0.5, size) if size >= 16 else 0.0
            )
            if bg_coverage <= 0.0:
                pixels += bytes(4)
                continue
            r, g, b, _a = BACKGROUND
            if mark_coverage > 0.0:
                r = round(r + (MARK[0] - r) * mark_coverage)
                g = round(g + (MARK[1] - g) * mark_coverage)
                b = round(b + (MARK[2] - b) * mark_coverage)
            alpha = round(255 * bg_coverage)
            pixels += bytes((r, g, b, alpha))
    return bytes(pixels)


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data))
    )


def _encode_png(size: int, rgba: bytes) -> bytes:
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


def _encode_ico(pngs: dict[int, bytes]) -> bytes:
    """ICO container holding each size as an embedded PNG (supported since Vista)."""
    count = len(pngs)
    header = struct.pack("<HHH", 0, 1, count)
    entries = bytearray()
    images = bytearray()
    offset = 6 + count * 16
    for size, png_bytes in sorted(pngs.items()):
        width_byte = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII", width_byte, width_byte, 0, 0, 1, 32, len(png_bytes), offset
        )
        images += png_bytes
        offset += len(png_bytes)
    return header + bytes(entries) + bytes(images)


def main() -> None:
    pngs = {size: _encode_png(size, _render(size)) for size in SIZES}

    icon_png = ASSETS_DIR / "icon.png"
    icon_png.write_bytes(pngs[256])

    icon_ico = ASSETS_DIR / "icon.ico"
    icon_ico.write_bytes(_encode_ico(pngs))

    WEB_DIR.mkdir(exist_ok=True)
    shutil.copy(icon_png, WEB_DIR / "icon.png")
    shutil.copy(icon_ico, WEB_DIR / "favicon.ico")
    shutil.copy(icon_png, GUI_PACKAGE_DIR / "icon.png")

    print(
        f"Wrote {icon_png}, {icon_ico}, and copies in {WEB_DIR} and {GUI_PACKAGE_DIR}"
    )


if __name__ == "__main__":
    main()
