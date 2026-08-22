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
    timeout=30,
    headers=headers,
) as client:
    next_id_response = client.get(
        f"{url}/api2/json/cluster/nextid"
    )

    next_id_response.raise_for_status()

    vmid = int(next_id_response.json()["data"])

    print(f"Next available VMID: {vmid}")