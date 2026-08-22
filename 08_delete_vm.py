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
    print("Usage: uv run 08_delete_vm.py <vmid>")
    raise SystemExit(1)

vmid = int(sys.argv[1])

# Biar VM penting gak kehapus gara-gara typo wkwk
protected_vmids = {100, 101}

if vmid in protected_vmids:
    print(f"VM {vmid} is protected. Refusing to delete.")
    raise SystemExit(1)

with httpx.Client(
    verify=False,
    timeout=30,
    headers=headers,
) as client:
    # Cek dulu VM-nya
    response = client.get(
        f"{url}/api2/json/nodes/{node}/qemu/{vmid}/status/current"
    )
    response.raise_for_status()

    vm = response.json()["data"]

    print(f"VMID   : {vmid}")
    print(f"Name   : {vm.get('name')}")
    print(f"Status : {vm.get('status')}")

    if vm.get("status") != "stopped":
        print("VM must be stopped before deletion.")
        raise SystemExit(1)

    confirm = input(
        f"Delete VM {vmid} ({vm.get('name')}) permanently? [y/N]: "
    )

    if confirm.lower() != "y":
        print("Cancelled.")
        raise SystemExit(0)

    response = client.delete(
        f"{url}/api2/json/nodes/{node}/qemu/{vmid}"
    )
    response.raise_for_status()

    upid = response.json()["data"]

    print("Delete task submitted!")
    print("UPID:", upid)