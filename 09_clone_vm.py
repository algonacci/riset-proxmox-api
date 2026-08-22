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
template_vmid = 9000

with httpx.Client(
    verify=False,
    timeout=30,
    headers=headers,
) as client:

    # Ambil VMID baru
    response = client.get(
        f"{url}/api2/json/cluster/nextid"
    )
    response.raise_for_status()

    vmid = int(response.json()["data"])

    print(f"New VMID: {vmid}")

    # Clone template
    response = client.post(
        f"{url}/api2/json/nodes/{node}/qemu/{template_vmid}/clone",
        data={
            "newid": vmid,
            "name": f"omd-clone-{vmid}",
            "full": 1,
            "storage": "local-lvm",
        },
    )

    response.raise_for_status()

    upid = response.json()["data"]

    print("Clone submitted!")
    print("UPID:", upid)