"""Check GitHub for a newer release of Intentional."""

import json
import re
import urllib.request

REPOSITORY = "andrewjstuart/intentional-py"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
LATEST_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version)[:4])


def is_newer(latest: str, current: str) -> bool:
    return version_tuple(latest) > version_tuple(current)


def latest_release(timeout: float = 5.0) -> tuple[str, str]:
    """The latest release's version and web page; raises OSError or ValueError when unavailable."""
    request = urllib.request.Request(
        LATEST_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "intentional"},
    )
    with urllib.request.urlopen(
        request, timeout=timeout
    ) as response:  # fixed https URL
        release = json.loads(response.read().decode("utf-8"))
    return release["tag_name"].lstrip("v"), release.get("html_url") or RELEASES_URL
