"""
DNS Management Tool for Cloudflare

This script automates the management of DNS records for domains hosted on Cloudflare, enabling direct interactions from the command line or through a Flask-based web interface. It uses environment variables for configuration, supports operations such as creating, updating, and deleting DNS A records based on GUID mappings, and features automatic IP detection for incoming web requests. The tool also includes a configurable notification system for operation alerts.

Features:
- CLI for DNS record management.
- Flask web server for DNS updates via web requests.
- GUID to DNS A record mapping for secure record management.
- Automatic IP detection from web requests, supporting both direct and proxied connections.
- Configurable notification system using Apprise.

Usage:
- For CLI operations: `python autodns.py generate <subdomain>`
- To run the Flask server: `python autodns.py`, then access `http://localhost:<port>/update-dns?guid=<GUID>`

Configuration:
- Set Cloudflare API credentials (`CF_ZONE_ID`, `CF_API_TOKEN`), notification service URLs (`APPRISE_URLS`), enable notifications (`ENABLE_NOTIFICATIONS`), and optionally the Flask server port (`FLASK_RUN_PORT`) via environment variables.

Dependencies:
- Flask, Apprise, requests, hashlib, datetime, and standard Python libraries.
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

# Constants
RATE_LIMIT_MINUTES = 10  # Time between updates in minutes

app = Flask(__name__)

# Environment Variables
CF_ZONE_ID = os.getenv("CF_ZONE_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
CF_API_URL_BASE = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records"
ENABLE_NOTIFICATIONS = os.getenv("ENABLE_NOTIFICATIONS", "false").lower() in ["true", "1", "t"]
APPRISE_URLS = os.getenv("APPRISE_URLS", "").split(",")
MAPPING_FILE = '/config/guid_mapping.json'

def load_guid_mapping():
    """Load GUID to A record mapping and last update timestamps from a JSON file."""
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
    """Save the updated GUID mapping and timestamps back to the JSON file."""
    try:
        with open(MAPPING_FILE, 'w') as file:
            json.dump(mapping, file, indent=4)
    except Exception as e:
        sys.exit(f"Error saving GUID mapping: {e}")

def generate_guid(subdomain):
    """Generate a 64-character SHA-256 hash GUID based on subdomain and current time."""
    unique_string = f"{subdomain}"
    return hashlib.sha256(unique_string.encode()).hexdigest()

def is_update_allowed(guid):
    """Check if the update is allowed based on the last updated timestamp."""
    mapping = load_guid_mapping()
    if guid not in mapping:
        return True
    last_update = datetime.fromisoformat(mapping[guid]["lastUpdated"])
    return datetime.now() - last_update > timedelta(minutes=RATE_LIMIT_MINUTES)

def send_notification(message):
    """Send notification using Apprise if notifications are enabled and configured."""
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
    """Web endpoint to update DNS record based on GUID and detected IP."""
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

def parse_arguments():
    """Parse command line arguments for the DNS management script."""
    parser = argparse.ArgumentParser(description="Manage DNS records via Cloudflare API.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    generate_parser = subparsers.add_parser("generate", help="Generate a new GUID for a subdomain")
    generate_parser.add_argument("subdomain", type=str, help="Subdomain for which to generate a GUID")
    generate_parser.set_defaults(func=handle_generate_command)

    return parser.parse_args()

def handle_generate_command(args):
    """Handle the 'generate' command to create a new GUID for a subdomain."""
    subdomain = args.subdomain
    guid = generate_guid(subdomain)
    mapping = load_guid_mapping()
    if subdomain in [m["subdomain"] for m in mapping.values()]:
        print(f"Subdomain {subdomain} already has a GUID assigned.")
        return
    mapping[guid] = {"subdomain": subdomain, "lastUpdated": datetime.now().isoformat()}
    save_guid_mapping(mapping)
    print(f"Generated GUID for {subdomain}: {guid}")
    send_notification(f"Generated new GUID for {subdomain}.")

def main():
    """Main function to run the Flask app or handle CLI commands."""
    args = parse_arguments()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        # Run autodns daemon by default
        port = int(os.getenv("AUTODNS_PORT", "5000"))
        listen_on = os.getenv("AUTODNS_HOST", "0.0.0.0")
        app.run(host=listen_on, port=port)
        if name == "main":
            main()
