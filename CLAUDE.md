# AutoDNS

Flask-based Cloudflare DNS updater. Automatically updates A records using GUID-based identification with Apprise notifications.

## Stack
- Python 3 / Flask
- Cloudflare API (DNS management)
- Apprise (notifications)
- Docker (deployment)

## Dev
```bash
pip install -r requirements.txt
python autodns.py
```

## Docker
```bash
docker compose up -d
```

## Config
Environment variables: `CF_ZONE_ID`, `CF_API_TOKEN`, `APPRISE_URLS`, `AUTODNS_PORT`, `AUTODNS_HOST`.

## Architecture
Single-file app (`autodns.py`). Receives HTTP requests, extracts client IP (respects X-Forwarded-For), updates Cloudflare DNS via API, sends notifications via Apprise.

## Default Branch
`develop` (not main).
