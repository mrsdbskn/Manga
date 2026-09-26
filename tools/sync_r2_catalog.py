"""
Syncs frontend/public/comics/index.json with the remote Cloudflare R2 inventory.
Marks uploaded volumes as available=True and populates cbzUrl with the public R2 domain.
"""

import json
import os
import sys
import urllib.parse
from pathlib import Path

# Add tools dir to path
sys.path.insert(0, os.path.dirname(__file__))
from r2_sync import load_r2_config, list_remote_r2_objects

def sync_catalog(index_file_path: str = None):
    if not index_file_path:
        index_file_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "comics", "index.json")

    index_path = Path(index_file_path).resolve()
    if not index_path.exists():
        print(f"[Error] Catalog index file not found: {index_path}")
        return

    cfg = load_r2_config()
    public_base = cfg.get("public_url", "").rstrip("/")
    if not public_base:
        print("[Warning] No public_url found in r2_config.json.")

    print(f"Connecting to Cloudflare R2 bucket: {cfg.get('bucket_name')}...")
    remote_objs = list_remote_r2_objects(cfg)
    print(f"Found {len(remote_objs)} objects in R2:")
    for name, size in remote_objs.items():
        print(f"  - {name} ({size / (1024*1024):.1f} MB)")

    with open(index_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    if public_base:
        catalog["r2PublicUrl"] = public_base

    matched_count = 0
    for vol in catalog.get("volumes", []):
        cbz_name = vol.get("cbzFile")
        if cbz_name and cbz_name in remote_objs:
            encoded_name = urllib.parse.quote(cbz_name)
            remote_url = f"{public_base}/{encoded_name}"
            vol["cbzUrl"] = remote_url
            vol["available"] = True
            matched_count += 1
            print(f"Volume {vol.get('volumeNumber')} matched -> {remote_url}")

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"\n[DONE] Successfully updated {matched_count} volume(s) in {index_path.name} with Cloudflare R2 streaming URLs!")

if __name__ == "__main__":
    idx = sys.argv[1] if len(sys.argv) > 1 else None
    sync_catalog(idx)
