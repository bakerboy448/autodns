"""
autodns.py

This module contains the implementation of a Flask application that interacts with the Cloudflare API.
It uses environment variables to configure the Cloudflare zone and API token, and provides a route to update DNS records.
The module also uses the Apprise library to send notifications, and loads a GUID to A record mapping from a file.

Modules:
    - json: Used to load the GUID to A record mapping from a JSON file.
    - os: Used to get environment variables.
    - apprise: Used to send notifications.
    - requests: Used to make requests to the Cloudflare API.
    - flask: Used to create the Flask application and handle requests.

Environment Variables:
    - CF_ZONE_ID: The ID of the Cloudflare zone to update.
    - CF_API_TOKEN: The API token to use when making requests to the Cloudflare API.
    - APPRISE_URLS: A comma-separated list of Apprise URLs to send notifications to.

Functions:
    - load_guid_mapping: Loads the GUID to A record mapping from a file.
"""
import json
import os
import apprise
import requests
from flask import Flask, request


app = Flask(__name__)

CF_ZONE_ID = os.getenv("CF_ZONE_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
CF_API_URL_BASE = (
    f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records"
)

APPRISE_URLS = os.getenv("APPRISE_URLS", "").split(",")

MAPPING_FILE = '/config/guid_mapping.json'


def load_guid_mapping():
    """Load GUID to A record mapping from a file."""
    try:
        with open(MAPPING_FILE, 'r') as file:
            return json.load(file)
    except Exception as e:  # Consider specifying exceptions for better handling
        print(f"Error loading GUID mapping: {e}")
        return {}


@app.route("/update-dns", methods=["GET"])
def update_dns():
    """Update DNS record based on GUID and automatically detected IP."""
    guid_to_a_record_mapping = load_guid_mapping()
    guid = request.args.get("guid")

    new_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]

    if guid not in guid_to_a_record_mapping:
        return "Unauthorized or unknown GUID", 401

    a_record_name = guid_to_a_record_mapping[guid]
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.get(
        f"{CF_API_URL_BASE}?type=A&name={a_record_name}", headers=headers, timeout=60
    )

    if response.status_code == 200 and response.json()["result"]:
        dns_record_id = response.json()["result"][0]["id"]
        data = {
            "type": "A",
            "name": a_record_name.strip(),
            "content": new_ip,
            "ttl": 1
        }

        update_response = requests.put(
            f"{CF_API_URL_BASE}/{dns_record_id}", json=data, headers=headers, timeout=60
        )

        if update_response.status_code == 200:
            send_notification(
                f"DNS record for {a_record_name} updated successfully to {new_ip}."
            )
            return "DNS record updated successfully."
        else:
            send_notification(f"Failed to update DNS record for {a_record_name}.")
            return "Failed to update DNS record.", 500
    else:
        send_notification(f"Failed to find DNS record for {a_record_name}.")
        return "Failed to find DNS record.", 500


def send_notification(message):
    """Send notification using Apprise."""
    notification = apprise.Apprise()
    for url in APPRISE_URLS:
        if url:
            notification.add(url)
    notification.notify(body=message)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
