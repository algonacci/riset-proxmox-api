"""Stop lalu hapus orvix-db (102) dan orvix-fadil (103)."""

import os
import pathlib
import time

import httpx
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env")

PROXMOX_URL = os.getenv("PROXMOX_URL")
TOKEN_ID = os.getenv("PROXMOX_TOKEN_ID")
TOKEN_SECRET = os.getenv("PROXMOX_TOKEN_SECRET")

NODE = "proxmox"
HEADERS = {"Authorization": f"PVEAPIToken={TOKEN_ID}={TOKEN_SECRET}"}

TARGETS = [
    (102, "orvix-db"),
    (103, "orvix-fadil"),
]


def wait_task(client, upid, timeout=120):
    started_at = time.time()
    while True:
        if time.time() - started_at > timeout:
            raise TimeoutError(f"Task timeout: {upid}")
        r = client.get(f"{PROXMOX_URL}/api2/json/nodes/{NODE}/tasks/{upid}/status")
        r.raise_for_status()
        task = r.json()["data"]
        print(f"    Task status: {task.get('status')} exit: {task.get('exitstatus')}")
        if task.get("status") == "stopped":
            if task.get("exitstatus") != "OK":
                raise RuntimeError(f"Task gagal: {task.get('exitstatus')}")
            return
        time.sleep(2)


with httpx.Client(verify=False, timeout=60, headers=HEADERS) as client:
    for vmid, name in TARGETS:
        print(f"\n{'='*60}")
        print(f"PROSES: {name} (VMID {vmid})")
        print(f"{'='*60}")

        # Cek status
        r = client.get(
            f"{PROXMOX_URL}/api2/json/nodes/{NODE}/qemu/{vmid}/status/current"
        )
        r.raise_for_status()
        vm = r.json()["data"]
        status = vm["status"]
        print(f"  Status saat ini: {status}")

        # Stop jika running
        if status != "stopped":
            print(f"  >> Mengirim perintah stop...")
            r = client.post(
                f"{PROXMOX_URL}/api2/json/nodes/{NODE}/qemu/{vmid}/status/stop"
            )
            r.raise_for_status()
            upid = r.json()["data"]
            print(f"  UPID: {upid}")
            print(f"  Menunggu VM berhenti...")
            wait_task(client, upid)
            # Verifikasi stopped
            time.sleep(3)
            print(f"  >> VM {vmid} sudah berhenti")
        else:
            print(f"  -- VM sudah berhenti")

        # Hapus VM
        print(f"  >> Menghapus VM {vmid}...")
        r = client.delete(
            f"{PROXMOX_URL}/api2/json/nodes/{NODE}/qemu/{vmid}"
        )
        r.raise_for_status()
        upid = r.json()["data"]
        print(f"  UPID: {upid}")
        print(f"  Menunggu task hapus selesai...")
        wait_task(client, upid)
        print(f"  >> {name} (VMID {vmid}) BERHASIL DIHAPUS!")

    print(f"\n{'='*60}")
    print(f"SELESAI! orvix-db (102) dan orvix-fadil (103) telah dihapus.")
    print(f"{'='*60}")
