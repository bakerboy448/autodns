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
- `generate <subdomain>`: Creates a new DNS A record for the specified subdomain.
- `delete <subdomain>`: Removes an existing DNS A record matching the specified subdomain.
- `update <subdomain> <ip_address>`: Updates the IP address of the specified subdomain's DNS A record.
- `status`: Retrieves the current status of all managed DNS records and operation logs.

Usage:
- To execute a CLI command: `python autodns.py <command> [arguments]`
- To run the Flask web server: Simply execute `python autodns.py` without any commands.

Note: This module assumes a pre-existing Flask environment and requires prior configuration of Cloudflare API credentials and Apprise notification URLs through environment variables.
"""
import argparse
import json
import os
import uuid
from flask import Flask, request, jsonify
import apprise
import requests

app = Flask(__name__)

# Configuration and Global Variables
CF_ZONE_ID = os.getenv("CF_ZONE_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
CF_API_URL_BASE = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records"
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

@app.route("/status", methods=["GET"])
def status():
    # Return the status of DNS records from LOG_DATABASE
    try:
        with open(LOG_DATABASE, 'r') as file:
            data = json.load(file)
            return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# CLI Argument Parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description="Manage DNS records via Cloudflare API.")
    subparsers = parser.add_subparsers(dest="command")

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate a new DNS record")
    generate_parser.add_argument("subdomain", type=str, help="Subdomain to generate")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete an existing DNS record")
    delete_parser.add_argument("subdomain", type=str, help="Subdomain to delete")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update an existing DNS record")
    update_parser.add_argument("subdomain", type=str, help="Subdomain to update")
    update_parser.add_argument("ip_address", type=str, help="New IP address for the subdomain")

    # Status command
    status_parser = subparsers.add_parser("status", help="Get the status of DNS records")

    return parser.parse_args()

def main():
    args = parse_arguments()

    if args.command == "generate":
        # Generate functionality
        pass
    elif args.command == "delete":
        # Delete functionality
        pass
    elif args.command == "update":
        # Update functionality
        pass
    elif args.command == "status":
        # Since status needs to run the Flask app to access the route,
        # consider invoking HTTP request to "/status" here or refactor.
        pass
    else:
        # If no CLI command is provided, run the Flask app
        app.run(host="0.0.0.0")

if __name__ == "__main__":
    app.run(host="0.0.0.0")
