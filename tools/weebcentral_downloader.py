"""
weebcentral_downloader.py - Downloads official Viz English Black & White One Piece chapters
from WeebCentral (formerly MangaSee / MangaLife).
Provides complete coverage for all chapters 1 to 1193+ (including the middle chapters
that are app-locked on MangaPlus and external on MangaDex).

Embeds ComicRack-compliant ComicInfo.xml, outputs Chapter {number} - {title}.cbz,
and synchronizes frontend/public/comics/index.json.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup

try:
    from tools.comic_info import build_comic_info_xml, format_chapter_filename, format_chapter_display_title, clean_chapter_sub_title
    from tools.catalog_indexer import scan_and_index_volumes
except ImportError:
    from comic_info import build_comic_info_xml, format_chapter_filename, format_chapter_display_title, clean_chapter_sub_title
    from catalog_indexer import scan_and_index_volumes

WEEBCENTRAL_SERIES_ID = "01J76XY7E9FNDZ1DBBM6PBJPFK"
WEEBCENTRAL_BASE = "https://weebcentral.com"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# Cache file for WeebCentral chapter mapping
CACHE_FILE = Path(__file__).resolve().parent / ".weebcentral_cache.json"
CACHE_TTL_SECONDS = 86400  # 24 hours


def parse_chapter_range(range_str: str) -> List[int]:
    """
    Parses strings like '1-1190', '1 - 1190', '1, 2, 5-10', or '4' into a sorted list of unique integers.
    """
    chapters: Set[int] = set()
    parts = str(range_str).split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            for c in range(min(start, end), max(start, end) + 1):
                chapters.add(c)
        elif part.isdigit():
            chapters.add(int(part))
    return sorted(chapters)


def is_chapter_already_downloaded(output_dir: Path, chapter_num: int) -> Optional[Path]:
    """
    Checks if a CBZ archive for this chapter already exists in output_dir.
    Returns the Path if found, otherwise None.
    """
    patterns = [
        f"Chapter {chapter_num} - *.cbz",
        f"Chapter {chapter_num}.cbz",
        f"Chapter {chapter_num:03d} - *.cbz",
        f"Chapter {chapter_num:04d} - *.cbz",
        f"*c{chapter_num:04d}*.cbz",
    ]
    for pat in patterns:
        matches = list(output_dir.glob(pat))
        if matches and matches[0].stat().st_size > 5000:
            return matches[0]
    return None


def fetch_weebcentral_chapter_map(
    force_refresh: bool = False,
    log_callback: Callable[[str], None] = print,
) -> Dict[float, str]:
    """
    Fetches the complete chapter-to-ID mapping for One Piece from WeebCentral.
    Caches results locally for 24 hours to ensure high speed.
    """
    now = time.time()
    if not force_refresh and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            cached_time = cached_data.get("_cached_at", 0)
            if now - cached_time < CACHE_TTL_SECONDS:
                raw_map = cached_data.get("chapters", {})
                return {float(k): v for k, v in raw_map.items()}
        except Exception:
            pass

    log_callback("Fetching latest One Piece chapter index from WeebCentral...")
    url = f"{WEEBCENTRAL_BASE}/series/{WEEBCENTRAL_SERIES_ID}/full-chapter-list"
    res = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
    if res.status_code != 200:
        raise RuntimeError(f"Failed to fetch chapter list from WeebCentral (HTTP {res.status_code})")

    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.find_all("a", href=re.compile(r"/chapters/[A-Z0-9]+"))

    chapter_map: Dict[float, str] = {}
    for link in links:
        texts = [s.strip() for s in link.stripped_strings]
        for t in texts:
            m = re.match(r"^Chapter\s+([\d\.]+)$", t)
            if m:
                cid = link["href"].split("/")[-1]
                chapter_map[float(m.group(1))] = cid
                break

    # Save to disk cache
    try:
        cache_payload = {
            "_cached_at": now,
            "chapters": {str(k): v for k, v in chapter_map.items()},
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_payload, f, indent=2)
    except Exception:
        pass

    log_callback(f"Successfully indexed {len(chapter_map)} official B&W chapters from WeebCentral.")
    return chapter_map


def fetch_chapter_title_from_mangadex(chapter_num: int) -> Optional[str]:
    """
    Attempts to fetch official chapter title from MangaDex metadata.
    """
    try:
        url = "https://api.mangadex.org/chapter"
        params = {
            "manga": "a2c1d849-af05-4bbc-b2a7-866ebb10331f",  # Colored edition often retains full chapter title
            "chapter": str(chapter_num),
            "translatedLanguage[]": "en",
            "limit": 1,
        }
        r = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                title = data[0].get("attributes", {}).get("title")
                if title and title.strip():
                    return title.strip()
    except Exception:
        pass
    return None


_CANON_CHAPTER_TITLES: Optional[Dict[int, str]] = None

def get_canonical_chapter_title(chapter_num: int) -> Optional[str]:
    """
    Retrieves the official canonical English chapter title from canon_chapter_titles.json,
    falling back to MangaDex API if not found.
    """
    global _CANON_CHAPTER_TITLES
    if _CANON_CHAPTER_TITLES is None:
        _CANON_CHAPTER_TITLES = {}
        paths = [
            Path(__file__).resolve().parent / "canon_chapter_titles.json",
            Path(__file__).resolve().parent.parent / "frontend" / "public" / "comics" / "canon_chapter_titles.json",
        ]
        for p in paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        _CANON_CHAPTER_TITLES = {int(k): v for k, v in raw.items()}
                        break
                except Exception:
                    pass

    if chapter_num in _CANON_CHAPTER_TITLES:
        return _CANON_CHAPTER_TITLES[chapter_num]

    return fetch_chapter_title_from_mangadex(chapter_num)


def download_weebcentral_chapter(
    chapter_num: int | float,
    output_dir: str | Path,
    chapter_map: Optional[Dict[float, str]] = None,
    sync_catalog: bool = True,
    log_callback: Callable[[str], None] = print,
) -> str:
    """
    Downloads a single official B&W One Piece chapter from WeebCentral,
    packages into Chapter {num} - {title}.cbz with ComicRack ComicInfo.xml,
    and optionally refreshes index.json.
    """
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    ch_float = float(chapter_num)
    ch_int = int(ch_float) if ch_float.is_integer() else ch_float

    if chapter_map is None:
        chapter_map = fetch_weebcentral_chapter_map(log_callback=log_callback)

    cid = chapter_map.get(ch_float)
    if not cid:
        raise RuntimeError(f"Chapter {ch_int} not found in WeebCentral catalog (Available: 1 to {int(max(chapter_map.keys()))}).")

    log_callback(f"Resolving Chapter {ch_int} [ID: {cid}]...")

    # Fetch image URLs from chapter images endpoint
    images_url = f"{WEEBCENTRAL_BASE}/chapters/{cid}/images"
    res = requests.get(images_url, headers=DEFAULT_HEADERS, timeout=20)
    if res.status_code != 200:
        raise RuntimeError(f"Failed to fetch images for Chapter {ch_int} (HTTP {res.status_code})")

    soup = BeautifulSoup(res.text, "html.parser")
    img_tags = soup.find_all("img")
    img_urls = [i.get("src") for i in img_tags if i.get("src")]

    if not img_urls:
        raise RuntimeError(f"No page images found for Chapter {ch_int}.")

    total_pages = len(img_urls)
    log_callback(f"Found {total_pages} official Viz B&W pages for Chapter {ch_int}.")

    # Resolve chapter subtitle using canon database (handles chapters 764-1188+)
    sub_title = get_canonical_chapter_title(int(ch_float)) or ""

    # Determine destination CBZ filename (guaranteeing no duplicate Chapter X - Chapter X prefixes)
    cbz_filename = format_chapter_filename(ch_int, sub_title)
    cbz_dest = out_path / cbz_filename
    vol_num = max(1, (int(ch_float) - 1) // 10 + 1)

    # Build ComicInfo.xml
    title_text = format_chapter_display_title(ch_int, sub_title)
    clean_summary = clean_chapter_sub_title(sub_title, ch_int)
    comic_info_xml = build_comic_info_xml(
        series="One Piece",
        volume=vol_num,
        number=int(ch_float),
        ch_start=int(ch_float),
        ch_end=int(ch_float),
        count=total_pages,
        title=title_text,
        summary=clean_summary or f"One Piece Chapter {ch_int} official English Black & White digital release.",
        language_iso="en",
    )

    log_callback(f"Downloading {total_pages} pages into '{cbz_dest.name}'...")

    with zipfile.ZipFile(cbz_dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ComicInfo.xml", comic_info_xml.encode("utf-8"))

        for i, img_url in enumerate(img_urls, 1):
            ext = ".png" if ".png" in img_url else ".jpg"
            for attempt in range(3):
                try:
                    img_resp = requests.get(img_url, headers=DEFAULT_HEADERS, timeout=25)
                    if img_resp.status_code == 200:
                        z.writestr(f"page_{i:04d}{ext}", img_resp.content)
                        break
                    else:
                        time.sleep(0.5)
                except Exception as dl_err:
                    if attempt == 2:
                        log_callback(f"Warning: Failed to download page {i}: {dl_err}")
                    time.sleep(1)

            if i % 5 == 0 or i == total_pages:
                log_callback(f"Progress: [{i}/{total_pages}] pages saved...")

            # Polite delay
            time.sleep(0.08)

    file_size_kb = cbz_dest.stat().st_size // 1024
    log_callback(f"Successfully packaged: {cbz_dest.name} ({file_size_kb} KB)")

    if sync_catalog:
        index_dest = out_path / "index.json"
        log_callback("Synchronizing catalog index.json...")
        scan_and_index_volumes(out_path, index_dest)
        log_callback("Catalog updated successfully!")

    return str(cbz_dest)


def download_weebcentral_batch(
    chapter_spec: str | int,
    output_dir: str | Path,
    skip_existing: bool = True,
    sync_catalog: bool = True,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    log_callback: Callable[[str], None] = print,
    cancel_flag: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """
    Downloads a batch or range of official Viz B&W chapters (e.g. '1-1190' or '4, 5, 10-20')
    from WeebCentral. Skips already cached CBZ files.
    """
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    chapters = parse_chapter_range(str(chapter_spec))
    total_chapters = len(chapters)

    if total_chapters == 0:
        raise ValueError(f"No valid chapters found in specification: '{chapter_spec}'")

    log_callback(f"=== Starting WeebCentral B&W Batch: {total_chapters} Chapter(s) ({chapter_spec}) ===")
    log_callback(f"Destination: {out_path}\n")

    # Fetch mapping once
    chapter_map = fetch_weebcentral_chapter_map(log_callback=log_callback)

    downloaded = 0
    skipped = 0
    failed = []

    for idx, ch_num in enumerate(chapters, 1):
        if cancel_flag and cancel_flag():
            log_callback("\n[Cancelled] Batch download was cancelled by user.")
            break

        # Check existing
        if skip_existing:
            existing = is_chapter_already_downloaded(out_path, ch_num)
            if existing:
                skipped += 1
                status = f"[{idx}/{total_chapters}] Ch. {ch_num}: Already exists ({existing.name}) -> Skipped"
                log_callback(status)
                if progress_callback:
                    progress_callback(idx / total_chapters, status)
                continue

        status = f"[{idx}/{total_chapters}] Processing Official B&W Chapter {ch_num}..."
        log_callback(status)
        if progress_callback:
            progress_callback(idx / total_chapters, status)

        try:
            download_weebcentral_chapter(
                chapter_num=ch_num,
                output_dir=out_path,
                chapter_map=chapter_map,
                sync_catalog=False,  # Defer sync until end of batch
                log_callback=lambda msg: log_callback(f"   {msg}"),
            )
            downloaded += 1
        except Exception as e:
            log_callback(f"   [Notice] Could not download Chapter {ch_num}: {e}")
            failed.append((ch_num, str(e)))

        # Polite delay between chapters
        time.sleep(0.3)

    log_callback("\n=== WeebCentral B&W Batch Summary ===")
    log_callback(f"Total Requested: {total_chapters}")
    log_callback(f"Successfully Downloaded: {downloaded}")
    log_callback(f"Skipped (Already Cached): {skipped}")
    log_callback(f"Missing / Failed: {len(failed)}")

    if sync_catalog and (downloaded > 0 or not (out_path / "index.json").exists()):
        log_callback("Synchronizing master catalog index.json...")
        scan_and_index_volumes(out_path, out_path / "index.json")
        log_callback("Showcase catalog updated successfully!")

    return {
        "total": total_chapters,
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
    }


def main():
    parser = argparse.ArgumentParser(description="Download official Viz English B&W One Piece chapters from WeebCentral")
    parser.add_argument("chapter", type=str, help="Chapter number or range to download (e.g. 4, '1-10', '1 - 1190')")
    parser.add_argument("-o", "--out", type=str, default="../frontend/public/comics", help="Output directory")
    parser.add_argument("--force", action="store_true", help="Force re-download even if chapter already exists")
    parser.add_argument("--no-sync", action="store_true", help="Do not sync index.json")

    args = parser.parse_args()
    try:
        download_weebcentral_batch(
            chapter_spec=args.chapter,
            output_dir=args.out,
            skip_existing=not args.force,
            sync_catalog=not args.no_sync,
        )
    except Exception as err:
        print(f"\nError: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
