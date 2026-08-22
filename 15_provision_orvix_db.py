"""Provision `orvix-db` — VM ketiga, khusus tiga engine database OMD.

Beda dari 13_provision_instance.py:
  - spesifikasi diambil dari pengukuran kapasitas, bukan default template
  - disk di-resize (template 10 GiB tidak cukup untuk data pelanggan)
  - onboot=1, karena database harus kembali sendiri setelah node reboot

Dry-run secara default. Jalankan dengan --apply untuk benar-benar menulis.
"""
import os
import pathlib
import secrets
import string
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env")

PROXMOX_URL = os.getenv("PROXMOX_URL")
TOKEN_ID = os.getenv("PROXMOX_TOKEN_ID")
TOKEN_SECRET = os.getenv("PROXMOX_TOKEN_SECRET")

NODE = "proxmox"
TEMPLATE_VMID = 9000
STORAGE = "local-lvm"

# Dari 14_capacity_report.py: node 4 core / 31,2 GiB, dua VM running memakai
# 25,5 GiB. Sisa ~5,7 GiB, dikurangi overhead PVE. 4 GiB adalah yang bisa
# diambil tanpa membuat node kehabisan.
VM_NAME = "orvix-db"
CORES = 2          # overcommit 8 -> 10 vCPU di atas 4 core = 2,5x
MEMORY_MB = 4096
DISK_GB = 80       # template 10 GiB, jadi tambah 70
TEMPLATE_DISK_GB = 10
DISK_KEY = "scsi0"

HEADERS = {"Authorization": f"PVEAPIToken={TOKEN_ID}={TOKEN_SECRET}"}
APPLY = "--apply" in sys.argv


def generate_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def wait_task(client, upid, timeout=600):
    started_at = time.time()
    while True:
        if time.time() - started_at > timeout:
            raise TimeoutError(f"Task timeout: {upid}")
        response = client.get(f"{PROXMOX_URL}/api2/json/nodes/{NODE}/tasks/{upid}/status")
        response.raise_for_status()
        task = response.json()["data"]
        if task.get("status") == "stopped":
            if task.get("exitstatus") != "OK":
                raise RuntimeError(f"Proxmox task failed: {task.get('exitstatus')}")
            return
        time.sleep(2)


def wait_guest_agent(client, vmid, timeout=300):
    started_at = time.time()
    while True:
        if time.time() - started_at > timeout:
            raise TimeoutError(f"Guest Agent timeout for VM {vmid}")
        try:
            if client.post(f"{PROXMOX_URL}/api2/json/nodes/{NODE}/qemu/{vmid}/agent/ping").status_code == 200:
                return
        except httpx.HTTPError:
            pass
        print("      Guest Agent belum ready...")
        time.sleep(3)


def wait_vm_ip(client, vmid, timeout=120):
    started_at = time.time()
    while True:
        if time.time() - started_at > timeout:
            raise TimeoutError(f"IPv4 timeout for VM {vmid}")
        response = client.get(
            f"{PROXMOX_URL}/api2/json/nodes/{NODE}/qemu/{vmid}/agent/network-get-interfaces"
        )
        if response.status_code == 200:
            for interface in response.json()["data"]["result"]:
                for address in interface.get("ip-addresses", []):
                    ip = address.get("ip-address")
                    if address.get("ip-address-type") == "ipv4" and ip and not ip.startswith("127."):
                        return ip
        print("      Menunggu IPv4...")
        time.sleep(3)


with httpx.Client(verify=False, timeout=60, headers=HEADERS) as client:
    response = client.get(f"{PROXMOX_URL}/api2/json/cluster/nextid")
    response.raise_for_status()
    vmid = int(response.json()["data"])

    password = generate_password()

    print()
    print("=" * 60)
    print(f"PROVISION {VM_NAME}" + ("" if APPLY else "   [DRY-RUN]"))
    print("=" * 60)
    print(f"""
  node        {NODE}
  vmid        {vmid}
  nama        {VM_NAME}
  sumber      clone penuh dari {TEMPLATE_VMID} (ubuntu-24-template)
  storage     {STORAGE}
  vCPU        {CORES}
  RAM         {MEMORY_MB} MB
  disk        {TEMPLATE_DISK_GB} GiB -> {DISK_GB} GiB (+{DISK_GB - TEMPLATE_DISK_GB}G pada {DISK_KEY})
  jaringan    vmbr0, DHCP  (192.168.10.0/24, gw 192.168.10.1)
  onboot      1
  user        ubuntu
""")

    if not APPLY:
        print("  Tidak ada yang ditulis. Jalankan dengan --apply untuk eksekusi.\n")
        raise SystemExit(0)

    print("[1/6] Clone template...")
    response = client.post(
        f"{PROXMOX_URL}/api2/json/nodes/{NODE}/qemu/{TEMPLATE_VMID}/clone",
        data={"newid": vmid, "name": VM_NAME, "full": 1, "storage": STORAGE},
    )
    response.raise_for_status()
    wait_task(client, response.json()["data"])
    print("      Clone selesai")

    print("\n[2/6] Konfigurasi CPU, RAM, cloud-init...")
    response = client.put(
        f"{PROXMOX_URL}/api2/json/nodes/{NODE}/qemu/{vmid}/config",
        data={
            "cores": CORES,
            "memory": MEMORY_MB,
            "ciuser": "ubuntu",
            "cipassword": password,
            "ipconfig0": "ip=dhcp",
            "agent": "enabled=1",
            "onboot": 1,
            "description": "OMD shared database host — MySQL, MariaDB, PostgreSQL. Closed beta.",
        },
    )
    response.raise_for_status()
    print("      Konfigurasi selesai")

    print(f"\n[3/6] Resize {DISK_KEY} ke {DISK_GB} GiB...")
    response = client.put(
        f"{PROXMOX_URL}/api2/json/nodes/{NODE}/qemu/{vmid}/resize",
        data={"disk": DISK_KEY, "size": f"+{DISK_GB - TEMPLATE_DISK_GB}G"},
    )
    response.raise_for_status()
    print("      Resize selesai")

    print("\n[4/6] Start VM...")
    response = client.post(f"{PROXMOX_URL}/api2/json/nodes/{NODE}/qemu/{vmid}/status/start")
    response.raise_for_status()
    wait_task(client, response.json()["data"])
    print("      VM jalan")

    print("\n[5/6] Menunggu QEMU Guest Agent...")
    wait_guest_agent(client, vmid)
    print("      Guest Agent siap")

    print("\n[6/6] Mencari alamat IPv4...")
    ip = wait_vm_ip(client, vmid)
    print(f"      IP: {ip}")

    print()
    print("=" * 60)
    print("SIAP")
    print("=" * 60)
    print(f"""
  vmid      {vmid}
  nama      {VM_NAME}
  ip        {ip}
  user      ubuntu
  password  {password}

  Berikutnya:
    - kunci IP-nya (reservasi DHCP atau ipconfig0 statis) sebelum gateway
      dikonfigurasi menunjuk ke sini
    - `sudo growpart /dev/sda 1 && sudo resize2fs /dev/sda1` kalau cloud-init
      belum otomatis memperluas partisi ke {DISK_GB} GiB
    - pasang Docker, lalu compose tiga engine dengan network_mode: host
""")
