"""
fetch_viz_metadata.py - Scrapes official Viz Media descriptions, release dates,
ISBNs, and metadata for all 113 One Piece volumes from viz.com.
Saves the cached catalog to frontend/public/comics/covers/viz_volumes_metadata.json.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

ALL_VOLUMES_URL = "https://www.viz.com/manga-books/manga/one-piece/all"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "frontend" / "public" / "comics" / "covers" / "viz_volumes_metadata.json"


def fetch_all_volume_urls() -> Dict[int, str]:
    """Fetches the main One Piece catalog page from Viz and extracts product URLs for all volumes."""
    print("Fetching One Piece series catalog from viz.com...")
    r = requests.get(ALL_VOLUMES_URL, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch series page from Viz (HTTP {r.status_code})")

    soup = BeautifulSoup(r.text, "html.parser")
    volume_urls: Dict[int, str] = {}

    for a in soup.find_all("a", href=re.compile(r"/manga-books/manga/one-piece-volume-")):
        href = a["href"]
        m = re.search(r"one-piece-volume-(\d+)", href)
        if m:
            v_num = int(m.group(1))
            full_url = "https://www.viz.com" + href if href.startswith("/") else href
            volume_urls[v_num] = full_url

    print(f"Discovered {len(volume_urls)} official One Piece volume URLs on Viz.")
    return volume_urls


def scrape_single_volume(vol_num: int, url: str, session: Optional[requests.Session] = None) -> Dict[str, Any]:
    """Scrapes description and metadata table for a single volume from its Viz product page with retry/backoff."""
    client = session or requests
    max_retries = 4
    for attempt in range(max_retries):
        try:
            r = client.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 429:
                wait_time = (attempt + 1) * 2.5
                time.sleep(wait_time)
                continue
            if r.status_code != 200:
                return {"volume": vol_num, "url": url, "error": f"HTTP {r.status_code}"}

            soup = BeautifulSoup(r.text, "html.parser")

            # 1. Synopsis / Description
            p_tags = soup.find_all("p")
            candidates = [
                p.text.strip() for p in p_tags 
                if len(p.text.strip()) > 80 
                and not p.text.strip().startswith("Read Free") 
                and not "Cookies" in p.text
                and not "Subscribe" in p.text
            ]
            description = max(candidates, key=len) if candidates else ""

            # Clean whitespace and artifacts
            description = re.sub(r"\s+", " ", description).strip()

            # 2. Key-value metadata table
            meta = {}
            for div in soup.find_all(["div", "tr", "dl"]):
                text = div.text.strip()
                for k in ["Story and Art", "Release", "ISBN-13", "UPC", "Trim Size", "Imprint", "Length", "Category", "Age Rating", "Series"]:
                    if k in text and len(text) < 150 and k not in meta:
                        parts = [s.strip() for s in div.stripped_strings if s.strip()]
                        if len(parts) >= 2 and k in parts[0]:
                            meta[k] = parts[1]
                        elif ":" in text:
                            sp = text.split(":", 1)
                            if k in sp[0]:
                                meta[k] = sp[1].strip()

            # Volume title
            h2 = soup.find("h2") or soup.find("h1")
            vol_title = f"Volume {vol_num}"
            if h2:
                vol_title = h2.text.strip()

            return {
                "volume": vol_num,
                "title": vol_title,
                "url": url,
                "description": description,
                "story_and_art": meta.get("Story and Art", "Eiichiro Oda"),
                "release": meta.get("Release", ""),
                "isbn13": meta.get("ISBN-13", ""),
                "upc": meta.get("UPC", ""),
                "trim_size": meta.get("Trim Size", "5 × 7 1/2"),
                "imprint": meta.get("Imprint", "SHONEN JUMP"),
                "length": meta.get("Length", "200 pages"),
                "series": meta.get("Series", "One Piece"),
                "category": meta.get("Category", "Manga"),
                "age_rating": meta.get("Age Rating", "Teen"),
            }
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return {"volume": vol_num, "url": url, "error": str(e)}

    return {"volume": vol_num, "url": url, "error": "HTTP 429 Too Many Requests"}


def build_and_save_viz_metadata(force_refresh: bool = False) -> Dict[int, Dict[str, Any]]:
    """Builds and caches the complete Viz volumes metadata JSON, resuming missing/error volumes."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing_data: Dict[str, Any] = {}
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            existing_data = {}

    volume_urls = fetch_all_volume_urls()
    results: Dict[int, Dict[str, Any]] = {}

    # Identify which volumes need to be scraped
    needed_vols = {}
    for v_num, url in volume_urls.items():
        str_k = str(v_num)
        if not force_refresh and str_k in existing_data:
            entry = existing_data[str_k]
            if not entry.get("error") and entry.get("description"):
                results[v_num] = entry
                continue
        needed_vols[v_num] = url

    if not needed_vols:
        print(f"All {len(results)} volumes already cached and valid in {OUTPUT_FILE}.")
        return results

    print(f"Loaded {len(results)} valid volumes from cache. Need to scrape/resume {len(needed_vols)} volumes...")

    session = requests.Session()
    # Scrape with controlled concurrency (2 workers) and polite delays to prevent 429
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_to_vol = {
            executor.submit(scrape_single_volume, v_num, url, session): v_num
            for v_num, url in needed_vols.items()
        }

        completed = 0
        total = len(future_to_vol)
        for future in concurrent.futures.as_completed(future_to_vol):
            v_num = future_to_vol[future]
            try:
                data = future.result()
                results[v_num] = data
                completed += 1
                if completed % 10 == 0 or completed == total:
                    print(f"   [{completed}/{total}] Volume metadata fetched...")
                    # Intermittent save
                    sorted_temp = {str(k): results[k] for k in sorted(results.keys())}
                    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                        json.dump(sorted_temp, f, indent=2, ensure_ascii=False)
            except Exception as exc:
                print(f"   Vol {v_num} generated an exception: {exc}")

    # Final save
    sorted_results = {str(k): results[k] for k in sorted(results.keys())}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted_results, f, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully saved Viz volumes metadata to: {OUTPUT_FILE} ({len(sorted_results)} volumes)")
    return {int(k): v for k, v in sorted_results.items()}


if __name__ == "__main__":
    build_and_save_viz_metadata(force_refresh="--force" in sys.argv)

