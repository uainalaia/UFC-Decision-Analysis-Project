"""Download published archive files, never scrape UFCStats or execute upstream code."""

import argparse
import hashlib
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "Greco1899/scrape_ufc_stats"
FILES = [
    "ufc_event_details.csv",
    "ufc_fight_results.csv",
    "ufc_fight_stats.csv",
    "ufc_fighter_details.csv",
    "LICENSE",
    "README.md",
]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "MMA-Decision-Lab/0.1 research"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", help="40-character archive commit; otherwise resolve main once")
    args = parser.parse_args()
    manifest_path = ROOT / "data/manifests/snapshot.json"
    if manifest_path.exists() and not args.commit:
        commit = json.loads(manifest_path.read_text())["upstream_commit"]
    else:
        commit = (
            args.commit
            or json.loads(fetch(f"https://api.github.com/repos/{REPOSITORY}/commits/main"))["sha"]
        )
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected a full Git commit SHA")
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    for name in FILES:
        url = f"https://raw.githubusercontent.com/{REPOSITORY}/{commit}/{name}"
        payload = fetch(url)
        (raw / name).write_bytes(payload)
        entries.append(
            {
                "file": name,
                "url": url,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
        )
        print(name, len(payload), "bytes")
    manifest = {
        "dataset_version": "greco-" + commit[:12],
        "upstream_commit": commit,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "source": "UFCStats via community CSV archive",
        "repository": f"https://github.com/{REPOSITORY}",
        "license": "Repository declares GPL-3.0; original-source rights not independently established. Local research copy; no data redistribution in Git.",
        "extraction_version": "0.1.0",
        "files": entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Snapshot:", manifest["dataset_version"])


if __name__ == "__main__":
    main()
