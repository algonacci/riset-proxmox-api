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
    print("Usage: uv run 11_check_guest_agent.py <vmid>")
    raise SystemExit(1)

vmid = int(sys.argv[1])

with httpx.Client(
    verify=False,
    timeout=10,
    headers=headers,
) as client:
    response = client.post(
        f"{url}/api2/json/nodes/{node}/qemu/{vmid}/agent/ping"
    )

    if response.status_code == 200:
        print(f"VM {vmid}: QEMU Guest Agent is available ✅")
        print(response.json())
    else:
        print(f"VM {vmid}: Guest Agent unavailable ❌")
        print("Status:", response.status_code)
        print("Response:", response.text)