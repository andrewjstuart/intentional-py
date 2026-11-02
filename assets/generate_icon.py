"""Generates the project's icon (assets/icon.png, assets/icon.ico) and copies a
web-sized favicon into web/. Not part of the package: a one-off/occasionally-
rerun tool, kept here so the icon can be regenerated or restyled without
needing an image editor.

The actual shape (a speech bubble around a boxed checkmark, simplified from
the ChatGPT-generated assets/icon-logo.png) and its pure-stdlib rendering live
in intentional_py.gui.icon_render, shared with the GUI: this script bakes the
static file family at the default "blue" accent, while the GUI calls the same
renderer again at runtime to recolor the window icon to match the user's
chosen accent (see gui/app.py's _window_icon/_set_accent).

Run: uv run python assets/generate_icon.py
"""

from __future__ import annotations

import shutil
import struct
from pathlib import Path

from intentional_py.gui.icon_render import Color, render_png

ASSETS_DIR = Path(__file__).parent
WEB_DIR = ASSETS_DIR.parent / "web"
# the GUI loads its window icon from inside the installable package (works from
# source, frozen, or pip-installed), rather than from this repo-root folder
GUI_PACKAGE_DIR = ASSETS_DIR.parent / "src" / "intentional_py" / "gui"

# Matches the GUI's default accent, so the icon looks at home next to its own buttons.
ACCENT: Color = (31, 106, 165)  # #1F6AA5

SIZES = (16, 24, 32, 48, 64, 128, 256)


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
    pngs = {size: render_png(size, ACCENT) for size in SIZES}

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
