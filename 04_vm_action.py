import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("PROXMOX_URL")
token_id = os.getenv("PROXMOX_TOKEN_ID")
token_secret = os.getenv("PROXMOX_TOKEN_SECRET")

headers = {
    "Authorization": f"PVEAPIToken={token_id}={token_secret}"
}

node = "proxmox"

if len(sys.argv) != 3:
    print("Usage: uv run 04_vm_action.py <vmid> <start|stop|shutdown|reboot>")
    raise SystemExit(1)

vmid = sys.argv[1]
action = sys.argv[2]

allowed_actions = {"start", "stop", "shutdown", "reboot"}

if action not in allowed_actions:
    print(f"Invalid action: {action}")
    raise SystemExit(1)

with httpx.Client(
    verify=False,
    timeout=10,
    headers=headers,
) as client:
    status_response = client.get(
        f"{url}/api2/json/nodes/{node}/qemu/{vmid}/status/current"
    )
    status_response.raise_for_status()

    current = status_response.json()["data"]

    print(f"VMID   : {vmid}")
    print(f"Name   : {current.get('name')}")
    print(f"Status : {current.get('status')}")

    confirm = input(f"Execute '{action}'? [y/N]: ")

    if confirm.lower() != "y":
        print("Cancelled.")
        raise SystemExit(0)

    response = client.post(
        f"{url}/api2/json/nodes/{node}/qemu/{vmid}/status/{action}"
    )

    response.raise_for_status()

    print("Task submitted!")
    print("UPID:", response.json()["data"])