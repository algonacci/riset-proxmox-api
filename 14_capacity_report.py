"""Berapa sisa kapasitas untuk VM baru (DB/OMD).

Read-only: hanya GET, tidak ada satu pun panggilan yang mengubah state.
"""
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


def gib(value):
    return (value or 0) / 1024**3


def bar(used, total, width=26):
    if not total:
        return "." * width
    filled = min(width, int(width * used / total))
    return "#" * filled + "." * (width - filled)


with httpx.Client(verify=False, timeout=30, headers=headers) as client:

    def get(path, **params):
        response = client.get(f"{url}/api2/json{path}", params=params)
        response.raise_for_status()
        return response.json()["data"]

    print("=" * 78)
    print("NODES")
    print("=" * 78)
    cores_total = 0
    ram_total = 0
    for node in sorted(get("/nodes"), key=lambda n: n["node"]):
        status = node.get("status")
        if status == "online":
            cores_total += node.get("maxcpu", 0)
            ram_total += node.get("maxmem", 0)
        print(f"\n  {node['node']}  [{status}]  uptime {(node.get('uptime') or 0) // 86400}d")
        print(f"    CPU   {node.get('maxcpu', 0)} core, load {node.get('cpu', 0) * 100:.1f}%")
        print(f"    RAM   {gib(node.get('mem')):7.1f} / {gib(node.get('maxmem')):7.1f} GiB  "
              f"{bar(node.get('mem'), node.get('maxmem'))}")
        print(f"    root  {gib(node.get('disk')):7.1f} / {gib(node.get('maxdisk')):7.1f} GiB  "
              f"{bar(node.get('disk'), node.get('maxdisk'))}")

    print("\n" + "=" * 78)
    print("GUESTS")
    print("=" * 78)
    run_cpu = run_ram = stop_cpu = stop_ram = disk_prov = 0
    guests = sorted(get("/cluster/resources", type="vm"),
                    key=lambda g: (g.get("node", ""), g.get("vmid", 0)))

    print(f"\n  {'VMID':>5} {'TIPE':<5} {'NAMA':<28} {'STATUS':<8} {'vCPU':>4} "
          f"{'RAM':>7} {'DISK':>8} {'RAM DIPAKAI':>12}")
    print("  " + "-" * 84)
    for g in guests:
        cpu = g.get("maxcpu") or 0
        ram = g.get("maxmem") or 0
        disk_prov += g.get("maxdisk") or 0
        if g.get("status") == "running":
            run_cpu += cpu
            run_ram += ram
        else:
            stop_cpu += cpu
            stop_ram += ram
        print(f"  {g.get('vmid'):>5} {g.get('type', '?'):<5} {str(g.get('name'))[:28]:<28} "
              f"{g.get('status', '?'):<8} {cpu:>4} {gib(g.get('maxmem')):>6.1f}G "
              f"{gib(g.get('maxdisk')):>7.1f}G {gib(g.get('mem')):>11.1f}G")

    print("\n" + "=" * 78)
    print("STORAGE")
    print("=" * 78)
    for node in get("/nodes"):
        if node.get("status") != "online":
            continue
        for store in get(f"/nodes/{node['node']}/storage"):
            total = store.get("total") or 0
            if not total:
                continue
            print(f"\n  {store['storage']:<18} {store.get('type', '?'):<10} "
                  f"{'shared' if store.get('shared') else 'local'}")
            print(f"    {gib(store.get('used')):8.1f} / {gib(total):8.1f} GiB  "
                  f"{bar(store.get('used'), total)}  bebas {gib(store.get('avail')):.1f} GiB")
            print(f"    isi: {store.get('content', '-')}")
        break

    print("\n" + "=" * 78)
    print("SISA UNTUK VM BARU")
    print("=" * 78)
    print(f"""
  Fisik (node online)        {cores_total:>4} core   {gib(ram_total):>8.1f} GiB
  Dialokasikan, running      {run_cpu:>4} vCPU   {gib(run_ram):>8.1f} GiB
  Dialokasikan, mati         {stop_cpu:>4} vCPU   {gib(stop_ram):>8.1f} GiB

  Sisa RAM (vs yang running)                {gib(ram_total - run_ram):>8.1f} GiB
  Sisa RAM (kalau semua dinyalakan)         {gib(ram_total - run_ram - stop_ram):>8.1f} GiB
  Overcommit vCPU sekarang                  {run_cpu / cores_total if cores_total else 0:>8.2f}x
  Disk ter-provision ke guest               {gib(disk_prov):>8.1f} GiB
""")
