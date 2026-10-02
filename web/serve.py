"""Serves this folder on localhost and opens it in a browser; Ctrl+C to stop.

No real hosting involved: Pyodide needs assets served over http(s) rather than
a bare file:// URL (browser CORS/MIME restrictions on WebAssembly), so this is
the smallest thing that satisfies that without running any real server.
"""

import http.server
import os
import socketserver
import webbrowser
from pathlib import Path

PORT = 8765


def main() -> None:
    os.chdir(Path(__file__).parent)
    with socketserver.TCPServer(
        ("", PORT), http.server.SimpleHTTPRequestHandler
    ) as httpd:
        url = f"http://localhost:{PORT}/"
        print(f"Serving {Path.cwd()} at {url} (Ctrl+C to stop)")
        webbrowser.open(url)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
