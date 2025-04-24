#!/usr/bin/env python3
"""wikidump_auto.py – Weekly Wikipedia‑dump fetcher

Fetches the latest *English* pages‑articles‑multistream dump torrent from the
unofficial Meta‑Wiki torrent list, adds it to a running qBittorrent WebUI, and
cleans up old dumps (> retention days) in the target directory.

Put it in cron, systemd‑timer, or GitHub Actions self‑hosted runner.

Example:
    python wikidump_auto.py --save-dir /mnt/wiki/enwiki --retention 30

Requirements: requests, beautifulsoup4, qbittorrent-api
    pip install -r requirements.txt

MIT License – © 2025 Joshua Ganschow
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import qbittorrentapi
import requests
from bs4 import BeautifulSoup

META_URL = "https://meta.wikimedia.org/wiki/Data_dump_torrents"
TORRENT_NAME_RE = re.compile(r"enwiki-.*pages-articles-multistream.*\.torrent$", re.I)
DUMP_FILE_RE = re.compile(r"enwiki-\d{8}-pages-articles-multistream.*\.bz2$", re.I)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def latest_torrent_url() -> str:
    """Return absolute URL of newest enwiki torrent found on Meta‑Wiki."""
    logging.info("Fetching torrent index…")
    html = requests.get(META_URL, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if TORRENT_NAME_RE.search(href):
            if href.startswith("//"):
                return "https:" + href
            if href.startswith("/"):
                return "https://meta.wikimedia.org" + href
            return href
    raise RuntimeError("Meta‑Wiki page did not contain expected enwiki torrent link.")


def download_torrent(url: str) -> Path:
    """Download the .torrent file to the system tmp dir and return its Path."""
    fn = Path(tempfile.gettempdir()) / os.path.basename(url)
    logging.info("Downloading %s → %s", url, fn)
    with requests.get(url, stream=True, timeout=60) as r, fn.open("wb") as f:
        r.raise_for_status()
        for chunk in r.iter_content(1 << 14):
            f.write(chunk)
    return fn


def push_to_qb(torrent_path: Path, host: str, port: int, user: str, pw: str,
               save_dir: Path, category: str):
    """Log in and add torrent. Raises on login failure."""
    qbt = qbittorrentapi.Client(host=host, port=port, username=user, password=pw)
    qbt.auth_log_in()
    logging.info("Connected to qBittorrent %s (WebAPI %s)", qbt.app.version, qbt.app.web_api_version)

    if not save_dir.is_dir():
        logging.info("Creating save directory %s", save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

    with torrent_path.open("rb") as tf:
        qbt.torrents_add(
            torrent_files=tf,
            save_path=str(save_dir),
            category=category,
            use_auto_torrent_management=False,
            paused=False,
        )
    logging.info("Torrent queued ⇒ %s", torrent_path.name)


def prune_old_dumps(directory: Path, keep_days: int):
    """Delete dump files older than *keep_days* to free space."""
    cutoff = datetime.now() - timedelta(days=keep_days)
    removed = 0
    for file in directory.iterdir():
        if not file.is_file():
            continue
        if not DUMP_FILE_RE.match(file.name):
            continue
        if file.name.endswith(".!qB"):
            # still downloading
            continue
        if datetime.fromtimestamp(file.stat().st_mtime) < cutoff:
            logging.info("Removing old dump → %s", file.name)
            file.unlink(missing_ok=True)
            removed += 1
    logging.info("Pruned %d old dump(s)", removed)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Fetch latest enwiki dump torrent and clean up old ones.")
    parser.add_argument("--host", default=os.getenv("QB_HOST", "localhost"), help="qBittorrent WebUI host name")
    parser.add_argument("--port", type=int, default=int(os.getenv("QB_PORT", 8080)), help="WebUI port")
    parser.add_argument("--user", default=os.getenv("QB_USER", "admin"), help="WebUI username")
    parser.add_argument("--password", default=os.getenv("QB_PASS", "adminadmin"), help="WebUI password")
    parser.add_argument("--save-dir", default=os.getenv("SAVE_DIR", "/mnt/wiki/enwiki"), help="Where to store Wikipedia dumps")
    parser.add_argument("--category", default=os.getenv("QB_CATEGORY", "wikipedia"), help="qBittorrent category tag")
    parser.add_argument("--retention", type=int, default=int(os.getenv("RETENTION_DAYS", 30)), help="Days to keep old dumps")
    parser.add_argument("--quiet", action="store_true", help="Suppress info logs")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(levelname)s: %(message)s")

    try:
        url = latest_torrent_url()
        torrent_path = download_torrent(url)
        push_to_qb(torrent_path, args.host, args.port, args.user, args.password,
                   Path(args.save_dir), args.category)
        prune_old_dumps(Path(args.save_dir), args.retention)
    except Exception as exc:
        logging.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
