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
vmid = 120

payload = {
    "vmid": vmid,
    "name": "omd-test-120",
    "cores": 1,
    "memory": 1024,
    "net0": "virtio,bridge=vmbr0",
    "ostype": "l26",
}

with httpx.Client(
    verify=False,
    timeout=30,
    headers=headers,
) as client:
    response = client.post(
        f"{url}/api2/json/nodes/{node}/qemu",
        data=payload,
    )

    response.raise_for_status()

    print("VM created!")
    print("VMID :", vmid)
    print("Task :", response.json()["data"])


