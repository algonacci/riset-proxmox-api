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

if len(sys.argv) != 2:
    print("Usage: uv run 12_get_vm_ip.py <vmid>")
    raise SystemExit(1)

vmid = int(sys.argv[1])

with httpx.Client(
    verify=False,
    timeout=10,
    headers=headers,
) as client:
    response = client.get(
        f"{url}/api2/json/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces"
    )

    response.raise_for_status()

    interfaces = response.json()["data"]["result"]

    for interface in interfaces:
        name = interface.get("name")

        for address in interface.get("ip-addresses", []):
            ip = address.get("ip-address")
            ip_type = address.get("ip-address-type")

            if ip_type == "ipv4" and not ip.startswith("127."):
                print(f"{name}: {ip}")