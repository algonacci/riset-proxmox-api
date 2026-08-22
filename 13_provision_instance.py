import os
import time
import secrets
import string

import httpx
from dotenv import load_dotenv


load_dotenv()

PROXMOX_URL = os.getenv("PROXMOX_URL")
TOKEN_ID = os.getenv("PROXMOX_TOKEN_ID")
TOKEN_SECRET = os.getenv("PROXMOX_TOKEN_SECRET")

NODE = "proxmox"
TEMPLATE_VMID = 9000
STORAGE = "local-lvm"

HEADERS = {
    "Authorization": f"PVEAPIToken={TOKEN_ID}={TOKEN_SECRET}"
}


def generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )


def wait_task(
    client: httpx.Client,
    upid: str,
    timeout: int = 300,
):
    started_at = time.time()

    while True:
        if time.time() - started_at > timeout:
            raise TimeoutError(
                f"Task timeout: {upid}"
            )

        response = client.get(
            f"{PROXMOX_URL}/api2/json/nodes/"
            f"{NODE}/tasks/{upid}/status"
        )
        response.raise_for_status()

        task = response.json()["data"]

        status = task.get("status")
        exit_status = task.get("exitstatus")

        if status == "stopped":
            if exit_status != "OK":
                raise RuntimeError(
                    f"Proxmox task failed: {exit_status}"
                )

            return

        time.sleep(1)


def wait_guest_agent(
    client: httpx.Client,
    vmid: int,
    timeout: int = 180,
):
    started_at = time.time()

    while True:
        if time.time() - started_at > timeout:
            raise TimeoutError(
                f"Guest Agent timeout for VM {vmid}"
            )

        try:
            response = client.post(
                f"{PROXMOX_URL}/api2/json/nodes/"
                f"{NODE}/qemu/{vmid}/agent/ping"
            )

            if response.status_code == 200:
                return

        except httpx.HTTPError:
            pass

        print("      Guest Agent belum ready...")
        time.sleep(2)


def get_vm_ipv4(
    client: httpx.Client,
    vmid: int,
):
    response = client.get(
        f"{PROXMOX_URL}/api2/json/nodes/"
        f"{NODE}/qemu/{vmid}/agent/"
        f"network-get-interfaces"
    )
    response.raise_for_status()

    interfaces = response.json()["data"]["result"]

    for interface in interfaces:
        for address in interface.get(
            "ip-addresses",
            [],
        ):
            ip = address.get("ip-address")
            ip_type = address.get(
                "ip-address-type"
            )

            if (
                ip_type == "ipv4"
                and ip
                and not ip.startswith("127.")
            ):
                return ip

    return None


def wait_vm_ip(
    client: httpx.Client,
    vmid: int,
    timeout: int = 60,
):
    started_at = time.time()

    while True:
        if time.time() - started_at > timeout:
            raise TimeoutError(
                f"IPv4 timeout for VM {vmid}"
            )

        ip = get_vm_ipv4(
            client,
            vmid,
        )

        if ip:
            return ip

        print("      Menunggu IPv4...")
        time.sleep(2)


with httpx.Client(
    verify=False,
    timeout=30,
    headers=HEADERS,
) as client:

    print()
    print("=== OMD Instance Provisioner ===")
    print()

    #
    # 1. GET NEXT VMID
    #
    print("[1/6] Getting next VMID...")

    response = client.get(
        f"{PROXMOX_URL}/api2/json/cluster/nextid"
    )
    response.raise_for_status()

    vmid = int(
        response.json()["data"]
    )

    vm_name = f"omd-instance-{vmid}"

    print(f"      VMID: {vmid}")
    print(f"      Name: {vm_name}")

    #
    # Generate per-instance password
    #
    username = "ubuntu"
    password = generate_password()

    #
    # 2. CLONE TEMPLATE
    #
    print()
    print(
        f"[2/6] Cloning template "
        f"{TEMPLATE_VMID}..."
    )

    response = client.post(
        f"{PROXMOX_URL}/api2/json/nodes/"
        f"{NODE}/qemu/{TEMPLATE_VMID}/clone",
        data={
            "newid": vmid,
            "name": vm_name,
            "full": 1,
            "storage": STORAGE,
        },
    )
    response.raise_for_status()

    clone_upid = response.json()["data"]

    wait_task(
        client,
        clone_upid,
    )

    print("      Clone complete ✅")

    #
    # 3. CONFIGURE CLOUD-INIT
    #
    print()
    print("[3/6] Configuring instance...")

    response = client.put(
        f"{PROXMOX_URL}/api2/json/nodes/"
        f"{NODE}/qemu/{vmid}/config",
        data={
            "cores": 1,
            "memory": 1024,
            "ciuser": username,
            "cipassword": password,
            "ipconfig0": "ip=dhcp",
            "agent": "enabled=1",
        },
    )
    response.raise_for_status()

    print("      Configuration complete ✅")

    #
    # 4. START VM
    #
    print()
    print("[4/6] Starting VM...")

    response = client.post(
        f"{PROXMOX_URL}/api2/json/nodes/"
        f"{NODE}/qemu/{vmid}/status/start"
    )
    response.raise_for_status()

    start_upid = response.json()["data"]

    wait_task(
        client,
        start_upid,
    )

    print("      VM started ✅")

    #
    # 5. WAIT FOR AGENT
    #
    print()
    print(
        "[5/6] Waiting for QEMU Guest Agent..."
    )

    wait_guest_agent(
        client,
        vmid,
    )

    print("      Guest Agent ready ✅")

    #
    # 6. DISCOVER IP
    #
    print()
    print("[6/6] Discovering IP address...")

    ip = wait_vm_ip(
        client,
        vmid,
    )

    print(f"      IP discovered: {ip} ✅")

    #
    # RESULT
    #
    print()
    print("==============================")
    print("INSTANCE READY 🎉")
    print("==============================")
    print()
    print(f"VMID     : {vmid}")
    print(f"Name     : {vm_name}")
    print(f"IP       : {ip}")
    print(f"Username : {username}")
    print(f"Password : {password}")
    print("Status   : READY")
    print()