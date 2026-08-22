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
    print("Usage: uv run 10_configure_cloudinit.py <vmid>")
    raise SystemExit(1)

vmid = int(sys.argv[1])

payload = {
    "cores": 1,
    "memory": 1024,
    "ciuser": "ubuntu",
    "ipconfig0": "ip=dhcp",
}

with httpx.Client(
    verify=False,
    timeout=30,
    headers=headers,
) as client:
    response = client.put(
        f"{url}/api2/json/nodes/{node}/qemu/{vmid}/config",
        data=payload,
    )

    response.raise_for_status()

    print(f"VM {vmid} configured!")