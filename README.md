# Cloudflare DNS Updater

[![Docker](https://github.com/baker-scripts/autodns/actions/workflows/docker-image.yml/badge.svg)](https://github.com/baker-scripts/autodns/actions/workflows/docker-image.yml)

The Cloudflare DNS Updater (AutoDNS) is a Flask-based application designed to automate the updating of A records on Cloudflare. Using GUIDs for DNS record identification, it features automatic IP detection from incoming requests and integrates with Apprise for sending notifications upon successful updates or when errors occur.

## Features

- **Automatic IP Detection:** Determines the client IP from incoming requests. When behind a trusted reverse proxy, trusts `X-Forwarded-For` only from configured proxy IPs.
- **GUID-based Identification:** Securely identifies the DNS record to update using GUIDs.
- **Notifications:** Sends notifications through a variety of services using Apprise upon successful updates or errors.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Docker and Docker Compose installed on your machine.
- A Cloudflare account and API token with DNS edit permissions.

## Environmental Variables

- `CF_ZONE_ID` - Cloudflare Zone ID for the DNS records you are updating.
- `CF_API_TOKEN` - API token used to authenticate with Cloudflare’s API.
- `APPRISE_URLS`- Comma-separated URLs for notification services
- `TRUSTED_PROXIES` - Comma-separated IPs of trusted reverse proxies. When set, `X-Forwarded-For` is only trusted from these IPs. When empty, `remote_addr` is always used.

```shell
docker run -d \
  --name autodns \
  --restart unless-stopped \
  -p 4295:4295 \
  -v /your/path/to/config:/config \
  -e CF_ZONE_ID="your-zone-id" \
  -e CF_API_TOKEN="your-api-token" \
  -e APPRISE_URLS="your-apprise-urls-separated-by-commas" \
  -e AUTODNS_PORT=4295 \
  -e AUTODNS_HOST=0.0.0.0 \
  -e TRUSTED_PROXIES="" \
  ghcr.io/baker-scripts/autodns:develop
```

## Contributors

<a href="https://github.com/baker-scripts/autodns/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=baker-scripts/autodns" alt="Contributors" />
</a>

## Disclaimer

This software is provided as-is with no warranty. Always review configurations before applying and test in a non-production environment first. The authors are not responsible for any DNS issues or service disruptions resulting from its use.

## License

[GPL-3.0](LICENSE)
