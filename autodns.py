"""
The `autodns.py` module automates DNS record management for Cloudflare-hosted domains directly from the command line or through a Flask-based web interface. Utilizing environment variables for configuration, it supports creating, updating, and deleting DNS A records based on GUID mappings, with automatic IP detection for incoming web requests. Notifications on operation outcomes are dispatched using the Apprise library.

Features include:
- Command Line Interface (CLI) for direct script interactions to manage DNS records.
- Flask web server integration for handling DNS updates via web requests.
- GUID to DNS A record mapping, facilitating secure and identifiable record management.
- Automatic IP detection from incoming web requests, supporting both direct and proxied connections.
- Notification system powered by Apprise, supporting a broad array of services for real-time operation alerts.

Modules Used:
- `json`: For loading and handling the GUID to A record mappings from a JSON file.
- `os`: To access environment variables for Cloudflare API credentials and Apprise configuration.
- `apprise`: Utilized for sending operation outcome notifications across various platforms.
- `requests`: Employed to interact with the Cloudflare API for DNS record management.
- `flask`: Facilitates the creation of the web interface, enabling DNS updates through HTTP requests.

Environment Variables:
- `CF_ZONE_ID`: Specifies the Cloudflare zone ID where DNS records will be managed.
- `CF_API_TOKEN`: The API token used for authentication with the Cloudflare API.
- `APPRISE_URLS`: Defines a comma-separated list of URLs for Apprise notification services.

Available Commands:
- `generate <subdomain>`: Creates a new GUID record for the specified subdomain.
- `create <subdomain>`: Creates a new DNS A record for the specified subdomain.
- `delete <subdomain>`: Removes an existing DNS A record matching the specified subdomain.
- `update <subdomain> <ip_address>`: Updates the IP address of the specified subdomain's DNS A record.
- `status`: Retrieves the current status of all managed DNS records and operation logs.
- `server`: Run the flask server and listen to incoming requests with the specified guid to update a subdomain's A record 

Usage:
- To execute a CLI command: `python autodns.py <command> [arguments]`
- To run the Flask web server: Simply execute `python autodns.py` without any commands.

Note: This module assumes a pre-existing Flask environment and requires prior configuration of Cloudflare API credentials and Apprise notification URLs through environment variables.
"""
import argparse
import hashlib
import json
import os
import requests
import sys
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import apprise

app = Flask(__name__)

# Environment Variables
CF_ZONE_ID = os.getenv("CF_ZONE_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
CF_API_URL_BASE = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records"
ENABLE_NOTIFICATIONS = os.getenv("ENABLE_NOTIFICATIONS", "false").lower() in ["true", "1", "t"]
APPRISE_URLS = os.getenv("APPRISE_URLS", "").split(",")

MAPPING_FILE = 'guid_mapping.json'

def load_guid_mapping():
    try:
        with open(MAPPING_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        sys.exit("Error decoding JSON from the mapping file.")
    except Exception as e:
        sys.exit(f"Error loading GUID mapping: {e}")

def save_guid_mapping(mapping):
    try:
        with open(MAPPING_FILE, 'w') as file:
            json.dump(mapping, file, indent=4)
    except Exception as e:
        sys.exit(f"Error saving GUID mapping: {e}")

def generate_guid(subdomain):
    unique_string = f"{subdomain}{time.time()}"
    return hashlib.sha256(unique_string.encode()).hexdigest()

def is_update_allowed(guid):
    mapping = load_guid_mapping()
    if guid not in mapping:
        return True
    last_update = datetime.fromisoformat(mapping[guid]["lastUpdated"])
    return datetime.now() - last_update > timedelta(minutes=10)

def send_notification(message):
    if not ENABLE_NOTIFICATIONS or not APPRISE_URLS:
        print("Notifications are disabled or not configured.")
        return
    notification = apprise.Apprise()
    for url in APPRISE_URLS:
        if url:
            notification.add(url)
    success = notification.notify(body=message)
    if success:
        print("Notification sent successfully.")
    else:
        print("Failed to send notification.")

@app.route("/update-dns", methods=["GET"])
def update_dns_web():
    guid = request.args.get("guid")
    if not guid:
        return jsonify({"error": "GUID parameter is missing"}), 400
    mapping = load_guid_mapping()
    if guid not in mapping or not is_update_allowed(guid):
        return jsonify({"error": "Update not allowed or unknown GUID"}), 429
    new_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]

    headers = {"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"}
    dns_record = mapping[guid]["subdomain"]
    data = {"type": "A", "name": dns_record, "content": new_ip, "ttl": 1}

    response = requests.get(f"{CF_API_URL_BASE}?name={dns_record}&type=A", headers=headers)
    if response.status_code == 200 and response.json()["result"]:
        dns_record_id = response.json()["result"][0]["id"]
        update_response = requests.put(f"{CF_API_URL_BASE}/{dns_record_id}", headers=headers, json=data)
        if update_response.status_code == 200:
            mapping[guid]["lastUpdated"] = datetime.now().isoformat()
            save_guid_mapping(mapping)
            send_notification(f"DNS record for {dns_record} updated successfully to {new_ip}.")
            return jsonify({"success": True, "message": "DNS record updated."})
        else:
            return jsonify({"error": "Failed to update DNS record."}), 500
    else:
        return jsonify({"error": "DNS record does not exist or Cloudflare API error."}), 404

def handle_generate_command(subdomain):
    guid = generate_guid(subdomain)
    mapping = load_guid_mapping()
    if subdomain in [m["subdomain"] for m in mapping.values()]:
        print(f"Subdomain {subdomain} already has a GUID assigned.")
        return
    mapping[guid] = {"subdomain": subdomain, "lastUpdated": datetime.now().isoformat()}
    save_guid_mapping(mapping)
    print(f"Generated GUID for {subdomain}: {guid}")
    send_notification(f"Generated new GUID for {subdomain}.")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Manage DNS records via Cloudflare API.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    generate_parser = subparsers.add_parser("generate", help="Generate a new GUID for a subdomain")
    generate_parser.add_argument("subdomain", type=str, help="Subdomain for which to generate a GUID")
    generate_parser.set_defaults(func=handle_generate_command)

    return parser.parse_args()

def main():
    args = parse_arguments()
    if hasattr(args, 'func'):
        args.func(args.subdomain)
    else:
        app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
