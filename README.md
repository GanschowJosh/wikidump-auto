# Wikidump Auto

Fetch the newest **English Wikipedia** pages-articles-multistream dump every week, add it to a running **qBittorrent** instance, and prune old dumps automatically.

---

## Features

* **Latest dump, every run** – scrapes the unofficial Meta-Wiki torrent index.
* **qBittorrent Web API** – pushes the `.torrent` straight into your client.
* **Retention policy** – deletes dump files older than N days (default 30).
* **One-file, zero hassle** – just `pip install -r requirements.txt` and go.
* **CLI flags & env vars** – override everything without editing the code.

---

## 🔧 Requirements

```text
Python 3.9+
requests
beautifulsoup4
qbittorrent-api
```

> Install with `pip install -r requirements.txt`

---

## Quick Start

```bash
# clone repo
$ git clone https://github.com/GanschowJosh/wikidump-auto.git
$ cd wikidump-auto

# install deps
$ pip install -r requirements.txt

# run once (interactive)
$ python wikidump_auto.py \
      --user 'yourUser' --password 'yourPass' \
      --save-dir '/path/to/save/dir' \
      --host localhost --port 8080
```

Flags | Purpose | Default
----- | ------- | -------
`--host` | Web UI hostname / IP | `localhost`
`--port` | Web UI port | `8080`
`--user` | Web UI username | `admin`
`--password` | Web UI password | `adminadmin`
`--save-dir` | Destination directory **(must be writable by qB)** | `/mnt/wiki/enwiki`
`--category` | qBittorrent category label | `wikipedia`
`--retention` | Days to keep old dumps | `30`
`--quiet` | Silence info logs | off

Environment variables with the same names override the defaults as well.

---

## Automate with cron

```cron
# m h dom mon dow  command
15 3 * * 0 /usr/bin/python3 /opt/wikidump-auto/wikidump_auto.py >> /var/log/wikidump_auto.log 2>&1
```
Runs every **Sunday 03:15** local time.

### systemd-timer (optional)
```ini
[Unit]
Description=Weekly Wikipedia dump fetch

[Timer]
OnCalendar=Sun *-*-* 03:15:00
Persistent=true

[Install]
WantedBy=timers.target
```

---

## Docker example
```yaml
services:
  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent:latest
    environment:
      - WEBUI_PORT=8080
      - PUID=1000
      - PGID=1000
    volumes:
      - /mnt/wiki/enwiki:/downloads/wiki
    ports:
      - 8080:8080

  wikidump:
    build: .  # or image: python:3.12-slim + copy the script
    volumes:
      - /mnt/wiki/enwiki:/mnt/wiki/enwiki
    environment:
      - QB_HOST=qbittorrent
      - QB_PORT=8080
      - QB_USER=admin
      - QB_PASS=adminadmin
      - SAVE_DIR=/mnt/wiki/enwiki
      - RETENTION_DAYS=60
    entrypoint: ["python", "wikidump_auto.py"]
```

---

## How cleanup works
After each successful run the script scans `SAVE_DIR` for files matching
```
enwiki-YYYYMMDD-pages-articles-multistream*.bz2
```
and deletes any older than `--retention` days, ignoring partial `.bz2.!qB` files that are still downloading.

---

# Common Issues and Fixes
1. `Errored` status on qbittorent
  - Most common reason for this is that qbittorent does not have access to the folder you specified. Choose a different folder or edit permissions based on what user is running qbittorent client.
2. `ERROR: {"detail":"Method Not Allowed"}` or `[Errno 111] Connection refused`
  - Most likely the wrong port was specified to reach qbittorrent or qbittorrent webui was not enabled.

---

## License
[MIT](LICENSE) © 2025 **Joshua Ganschow**
