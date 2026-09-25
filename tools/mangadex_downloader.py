"""
mangadex_downloader.py - Downloads One Piece chapters from MangaDex
for chapters that are app-locked on MangaPlus.
Embeds ComicInfo.xml, outputs Chapter {number} - {title}.cbz, and syncs index.json.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import requests

try:
    from tools.comic_info import build_comic_info_xml
    from tools.catalog_indexer import scan_and_index_volumes
except ImportError:
    from comic_info import build_comic_info_xml
    from catalog_indexer import scan_and_index_volumes

MANGADEX_API_BASE = "https://api.mangadex.org"

# MangaDex Series UUIDs for One Piece
ONE_PIECE_MANGA_IDS = {
    "colored": "a2c1d849-af05-4bbc-b2a7-866ebb10331f",  # Official Digital Colored Edition (Ch 1-764+)
    "bw": "a1c7c817-4e59-43b7-9365-09675a149a6f",       # Standard Black & White Edition
}

DEFAULT_HEADERS = {
    "User-Agent": "MangaShowcasePlatform/1.0 (https://github.com/mrsdbskn/Manga)",
}


def find_chapter_on_mangadex(
    chapter_num: int | str,
    lang: str = "en",
    edition: str = "colored",
    log_callback: Callable[[str], None] = print,
) -> Optional[Dict]:
    """
    Finds a chapter on MangaDex with internal (downloadable) page data.
    First checks the preferred edition; falls back to the other if needed.
    """
    target_editions = [edition] + [e for e in ["colored", "bw"] if e != edition]

    for ed in target_editions:
        manga_id = ONE_PIECE_MANGA_IDS.get(ed)
        if not manga_id:
            continue

        log_callback(f"Querying MangaDex for Chapter {chapter_num} ({ed.upper()} edition, lang: {lang})...")
        try:
            params = {
                "manga": manga_id,
                "chapter": str(chapter_num),
                "translatedLanguage[]": lang,
                "limit": 10,
                "order[readableAt]": "desc",
            }
            res = requests.get(f"{MANGADEX_API_BASE}/chapter", params=params, headers=DEFAULT_HEADERS, timeout=15)
            if res.status_code != 200:
                continue

            data = res.json().get("data", [])
            # Filter chapters that have real internal pages (no externalUrl)
            valid_chapters = [c for c in data if not c.get("attributes", {}).get("externalUrl") and c.get("attributes", {}).get("pages", 0) > 0]
            if valid_chapters:
                chosen = valid_chapters[0]
                chosen["_edition"] = ed
                return chosen
        except Exception as e:
            log_callback(f"Notice: Query error for {ed} edition: {e}")

    # Also search globally across all One Piece chapters for this chapter number and language
    log_callback(f"Searching global MangaDex uploads for Chapter {chapter_num} in '{lang}'...")
    try:
        params = {
            "chapter": str(chapter_num),
            "translatedLanguage[]": lang,
            "limit": 20,
            "order[readableAt]": "desc",
        }
        res = requests.get(f"{MANGADEX_API_BASE}/chapter", params=params, headers=DEFAULT_HEADERS, timeout=15)
        if res.status_code == 200:
            data = res.json().get("data", [])
            for c in data:
                if not c.get("attributes", {}).get("externalUrl") and c.get("attributes", {}).get("pages", 0) > 0:
                    c["_edition"] = "community"
                    return c
    except Exception as e:
        log_callback(f"Notice: Global query error: {e}")

    return None


def download_mangadex_chapter(
    chapter_num: int | str,
    output_dir: str | Path,
    lang: str = "en",
    edition: str = "colored",
    data_saver: bool = False,
    sync_catalog: bool = True,
    log_callback: Callable[[str], None] = print,
) -> str:
    """
    Downloads a One Piece chapter from MangaDex, packages it into Chapter {num} - {title}.cbz,
    injects ComicInfo.xml, and optionally refreshes the showcase catalog.
    """
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    ch_meta = find_chapter_on_mangadex(chapter_num, lang=lang, edition=edition, log_callback=log_callback)
    if not ch_meta:
        raise RuntimeError(f"Chapter {chapter_num} not found with downloadable pages on MangaDex for language '{lang}'.")

    ch_id = ch_meta["id"]
    attrs = ch_meta["attributes"]
    ch_number_str = attrs.get("chapter", str(chapter_num))
    try:
        ch_int = int(float(ch_number_str))
    except ValueError:
        ch_int = int(chapter_num) if str(chapter_num).isdigit() else 1

    sub_title = (attrs.get("title") or "").strip()
    volume_val = attrs.get("volume")
    vol_num = int(volume_val) if volume_val and volume_val.isdigit() else max(1, (ch_int - 1) // 10 + 1)

    ed_used = ch_meta.get("_edition", edition)
    log_callback(f"Found Chapter {ch_int} ({ed_used.capitalize()}) - '{sub_title}' [ID: {ch_id}]")

    # Request At-Home CDN server endpoint
    log_callback("Requesting MangaDex At-Home CDN node...")
    server_res = requests.get(f"{MANGADEX_API_BASE}/at-home/server/{ch_id}", headers=DEFAULT_HEADERS, timeout=20)
    if server_res.status_code != 200:
        raise RuntimeError(f"MangaDex At-Home server request failed (HTTP {server_res.status_code})")

    server_data = server_res.json()
    base_url = server_data.get("baseUrl")
    chapter_info = server_data.get("chapter", {})
    ch_hash = chapter_info.get("hash")
    file_list = chapter_info.get("dataSaver" if data_saver else "data", [])

    if not base_url or not ch_hash or not file_list:
        raise RuntimeError("Incomplete At-Home server data received from MangaDex.")

    total_pages = len(file_list)
    log_callback(f"Downloading {total_pages} pages from CDN: {base_url}...")

    # Determine destination CBZ filename
    if sub_title:
        clean_sub = sub_title.replace(":", " - ").replace("/", "-").replace("\\", "-")
        clean_sub = re.sub(r'[*?"<>|]', "", clean_sub).strip()
        cbz_filename = f"Chapter {ch_int} - {clean_sub}.cbz"
    else:
        cbz_filename = f"Chapter {ch_int}.cbz"

    cbz_dest = out_path / cbz_filename

    # Build ComicRack-compliant ComicInfo.xml
    title_text = f"Chapter {ch_int}: {sub_title}" if sub_title else f"Chapter {ch_int}"
    comic_info_xml = build_comic_info_xml(
        series="One Piece (Digital Colored)" if ed_used == "colored" else "One Piece",
        volume=vol_num,
        number=ch_int,
        ch_start=ch_int,
        ch_end=ch_int,
        count=total_pages,
        title=title_text,
        summary=sub_title or f"One Piece Chapter {ch_int} ({ed_used.capitalize()}) from MangaDex.",
        language_iso=lang,
    )

    path_mode = "data-saver" if data_saver else "data"
    with zipfile.ZipFile(cbz_dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ComicInfo.xml", comic_info_xml.encode("utf-8"))

        for i, fname in enumerate(file_list, 1):
            img_url = f"{base_url}/{path_mode}/{ch_hash}/{fname}"
            ext = Path(fname).suffix or ".jpg"

            # Download page
            for attempt in range(3):
                try:
                    img_resp = requests.get(img_url, headers=DEFAULT_HEADERS, timeout=20)
                    if img_resp.status_code == 200:
                        z.writestr(f"page_{i:04d}{ext}", img_resp.content)
                        break
                    else:
                        time.sleep(0.5)
                except Exception as dl_err:
                    if attempt == 2:
                        log_callback(f"Warning: Failed to download page {i} ({fname}): {dl_err}")
                    time.sleep(1)

            if i % 5 == 0 or i == total_pages:
                log_callback(f"Progress: [{i}/{total_pages}] pages saved...")

            # Respectful rate limiting
            time.sleep(0.08)

    file_size_kb = cbz_dest.stat().st_size // 1024
    log_callback(f"Successfully packaged: {cbz_dest.name} ({file_size_kb} KB)")

    if sync_catalog:
        index_dest = out_path / "index.json"
        log_callback("Synchronizing catalog index.json...")
        scan_and_index_volumes(out_path, index_dest)
        log_callback("Catalog updated successfully!")

    return str(cbz_dest)


def main():
    parser = argparse.ArgumentParser(description="Download One Piece chapters from MangaDex and package into CBZ")
    parser.add_argument("chapter", type=str, help="Chapter number to download (e.g. 4 or 14)")
    parser.add_argument("-o", "--out", type=str, default="../frontend/public/comics", help="Output directory")
    parser.add_argument("-l", "--lang", type=str, default="en", help="Language code (en, es, fr, de, etc.) [default: en]")
    parser.add_argument("-e", "--edition", type=str, default="colored", choices=["colored", "bw"], help="Preferred edition (colored or bw) [default: colored]")
    parser.add_argument("--data-saver", action="store_true", help="Download compressed data-saver images")
    parser.add_argument("--no-sync", action="store_true", help="Do not sync index.json")

    args = parser.parse_args()
    try:
        download_mangadex_chapter(
            chapter_num=args.chapter,
            output_dir=args.out,
            lang=args.lang,
            edition=args.edition,
            data_saver=args.data_saver,
            sync_catalog=not args.no_sync,
        )
    except Exception as err:
        print(f"\nError: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
