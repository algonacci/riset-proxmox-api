import os

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
vmid = 102

with httpx.Client(
    verify=False,
    timeout=10,
    headers=headers,
) as client:
    response = client.get(
        f"{url}/api2/json/nodes/{node}/qemu/{vmid}/config"
    )

    response.raise_for_status()

    config = response.json()["data"]

    print(f"Name   : {config.get('name')}")
    print(f"Cores  : {config.get('cores')}")
    print(f"Memory : {config.get('memory')} MB")
    print(f"CPU    : {config.get('cpu')}")
    print(f"Network: {config.get('net0')}")