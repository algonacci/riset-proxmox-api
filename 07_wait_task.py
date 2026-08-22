import os
import sys
import time

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
    print("Usage: uv run 06_wait_task.py '<UPID>'")
    raise SystemExit(1)

upid = sys.argv[1]

with httpx.Client(
    verify=False,
    timeout=10,
    headers=headers,
) as client:

    while True:
        response = client.get(
            f"{url}/api2/json/nodes/{node}/tasks/{upid}/status"
        )

        response.raise_for_status()

        task = response.json()["data"]

        print(
            "status =", task.get("status"),
            "| exitstatus =", task.get("exitstatus")
        )

        if task.get("status") == "stopped":
            break

        time.sleep(1)

    if task.get("exitstatus") == "OK":
        print("Task completed successfully ✅")
    else:
        print("Task failed ❌")