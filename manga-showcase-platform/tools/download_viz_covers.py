"""
download_viz_covers.py - Downloads official One Piece volume covers from Viz Media
and optimizes them for the 360° 3D book renders.
"""

import os
import re
import io
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from PIL import Image

VIZ_SECTION_URL = "https://www.viz.com/manga-books/one-piece/series/5/section/62123/more"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

def fetch_cover_mappings():
    print(f"Fetching Viz volume list from: {VIZ_SECTION_URL}")
    r = requests.get(VIZ_SECTION_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    volume_map = {}

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        m = re.search(r"one-piece-volume-(\d+)", href)
        if m:
            vol_num = int(m.group(1))
            img = a.find("img") or (a.parent.find("img") if a.parent else None)
            if img:
                src = img.get("data-original") or img.get("src")
                if src and vol_num not in volume_map:
                    volume_map[vol_num] = src

    print(f"Extracted {len(volume_map)} volume cover URLs from Viz.")
    return volume_map

def download_and_save_covers(volume_map, dest_dir: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)
    total = len(volume_map)
    downloaded = 0
    skipped = 0

    print(f"Saving covers to: {dest_dir}")
    for vol_num in sorted(volume_map.keys()):
        url = volume_map[vol_num]
        jpg_path = dest_dir / f"cover-v{vol_num:02d}.jpg"
        webp_path = dest_dir / f"cover-v{vol_num:02d}.webp"

        # Check if already downloaded
        if jpg_path.exists() and webp_path.exists() and jpg_path.stat().st_size > 1000:
            skipped += 1
            continue

        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            if res.status_code == 200:
                raw_bytes = res.content
                # Save original JPEG
                with open(jpg_path, "wb") as f:
                    f.write(raw_bytes)

                # Save WebP version (optimized for 3D card display: 300x450, quality 90)
                try:
                    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
                    img.save(webp_path, "WEBP", quality=90)
                except Exception as pe:
                    print(f"PIL WebP conversion warning for Vol {vol_num}: {pe}")

                downloaded += 1
                if downloaded % 10 == 0 or downloaded == total:
                    print(f"Progress: [{downloaded + skipped}/{total}] - Vol {vol_num} downloaded ({len(raw_bytes)} bytes)")
            else:
                print(f"Failed to download Vol {vol_num} from {url} (HTTP {res.status_code})")
        except Exception as e:
            print(f"Error downloading Vol {vol_num} from {url}: {e}")

        # Tiny sleep to be polite
        time.sleep(0.05)

    print(f"\nDone! Downloaded: {downloaded}, Skipped (already cached): {skipped}, Total: {total}")

if __name__ == "__main__":
    # Target directory in frontend/public/comics/covers
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    covers_dir = repo_root / "frontend" / "public" / "comics" / "covers"
    
    mapping = fetch_cover_mappings()
    if mapping:
        download_and_save_covers(mapping, covers_dir)
    else:
        print("No covers found!")
