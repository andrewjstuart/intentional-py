"""Builds the wheel if needed, then serves this folder on localhost and opens
it in a browser; Ctrl+C to stop. The one command needed to try the web version:

    python web/serve.py

No real hosting involved: Pyodide needs assets served over http(s) rather than
a bare file:// URL (browser CORS/MIME restrictions on WebAssembly), so this is
the smallest thing that satisfies that without running any real server.
"""

import http.server
import os
import re
import shutil
import socketserver
import subprocess
import webbrowser
from pathlib import Path

PORT = 8765
WEB_DIR = Path(__file__).parent
REPO_ROOT = WEB_DIR.parent


def _version() -> str:
    match = re.search(
        r'^version\s*=\s*"([^"]+)"',
        (REPO_ROOT / "pyproject.toml").read_text(),
        re.MULTILINE,
    )
    if not match:
        raise RuntimeError("Could not find the version in pyproject.toml")
    return match[1]


def _source_mtime() -> float:
    return max(
        path.stat().st_mtime
        for path in (REPO_ROOT / "src" / "intentional_py").rglob("*.py")
    )


def _ensure_wheel() -> None:
    """(Re)build the project wheel into web/ if it's missing or source has changed since,
    and record its name in wheel-filename.txt so app.js never hardcodes the version."""
    wheel = WEB_DIR / f"intentional_py-{_version()}-py3-none-any.whl"
    if not (wheel.exists() and wheel.stat().st_mtime >= _source_mtime()):
        uv = shutil.which("uv")
        if uv is None:
            raise RuntimeError(
                "uv is required to build the wheel but wasn't found on PATH; "
                "see https://docs.astral.sh/uv/getting-started/installation/"
            )
        print("Building the wheel (source changed or first run)…")
        subprocess.run([uv, "build", "--wheel"], cwd=REPO_ROOT, check=True)
        for old_wheel in WEB_DIR.glob("intentional_py-*.whl"):
            old_wheel.unlink()
        shutil.copy(REPO_ROOT / "dist" / wheel.name, wheel)
    (WEB_DIR / "wheel-filename.txt").write_text(wheel.name)


def main() -> None:
    _ensure_wheel()
    os.chdir(WEB_DIR)
    # lets the server restart immediately after being stopped, instead of
    # failing with "Address already in use" while the port is in TIME_WAIT
    socketserver.TCPServer.allow_reuse_address = True
    # bind to localhost only - "" (all interfaces) would expose this to the LAN
    with socketserver.TCPServer(
        ("127.0.0.1", PORT), http.server.SimpleHTTPRequestHandler
    ) as httpd:
        url = f"http://localhost:{PORT}/"
        print(f"Serving {Path.cwd()} at {url} (Ctrl+C to stop)")
        webbrowser.open(url)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
