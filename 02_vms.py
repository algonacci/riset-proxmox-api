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

with httpx.Client(
    verify=False,
    timeout=10,
    headers=headers,
) as client:
    response = client.get(
        f"{url}/api2/json/nodes/proxmox/qemu"
    )

    response.raise_for_status()

    for vm in response.json()["data"]:
        print(
            vm["vmid"],
            vm["name"],
            vm["status"],
        )