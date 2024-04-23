# Cloudflare DNS Updater

The Cloudflare DNS Updater is a Flask-based application designed to automate the updating of A records on Cloudflare. Using GUIDs for DNS record identification, it features automatic IP detection from incoming requests and integrates with Apprise for sending notifications upon successful updates or when errors occur.

## Features

- **Automatic IP Detection:** Automatically determines the IP address from incoming requests, including handling of `X-Forwarded-For` headers for proxied requests.
- **GUID-based Identification:** Securely identifies the DNS record to update using GUIDs.
- **Notifications:** Sends notifications through a variety of services using Apprise upon successful updates or errors.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Docker and Docker Compose installed on your machine.
- A Cloudflare account and API token with DNS edit permissions.

## Docker

Command/Variable,Description
CF_ZONE_ID,Cloudflare Zone ID for the DNS records you are updating.
CF_API_TOKEN,API token used to authenticate with Cloudflare’s API.
APPRISE_URLS,Comma-separated URLs for notification services

```shell
docker run -d --name autodns \
  -p 4295:4295 \
  -v /your/path/to/config:/config \
  -e CF_ZONE_ID="your-zone-id" \
  -e CF_API_TOKEN="your-api-token" \
  -e APPRISE_URLS="your-apprise-urls-separated-by-commas" \
  -e FLASK_RUN_PORT="4295" \
  --restart unless-stopped \
  autodns
```

## Setup

**Coming Soon**
