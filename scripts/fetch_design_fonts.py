"""Fetch licensed IBM Plex assets from the official repository; no third-party code runs."""

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://raw.githubusercontent.com/IBM/plex/master/"
FILES = {
    "IBMPlexSans-Regular.woff2": "packages/plex-sans/fonts/complete/woff2/IBMPlexSans-Regular.woff2",
    "IBMPlexSans-SemiBold.woff2": "packages/plex-sans/fonts/complete/woff2/IBMPlexSans-SemiBold.woff2",
    "IBMPlexSansCondensed-Bold.woff2": "packages/plex-sans-condensed/fonts/complete/woff2/IBMPlexSansCondensed-Bold.woff2",
    "LICENSE.txt": "LICENSE.txt",
}


def main():
    folder = ROOT / "app/static/fonts"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, relative in FILES.items():
        with urllib.request.urlopen(BASE + relative, timeout=40) as response:
            payload = response.read()
        (folder / name).write_bytes(payload)
        manifest.append(
            {"file": name, "source": BASE + relative, "sha256": hashlib.sha256(payload).hexdigest()}
        )
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Saved local IBM Plex fonts and original license")


if __name__ == "__main__":
    main()
