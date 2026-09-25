"""
mangaplus_downloader.py - Direct MangaPlus Downloader & CBZ Packager.
Extracts chapters directly from MangaPlus using authenticated SESSION-TOKEN headers,
decrypts image streams, injects ComicRack-compliant ComicInfo.xml, and syncs the catalog.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import uuid
import zipfile
from pathlib import Path
from typing import Callable, Optional

import requests
from google.protobuf.message import DecodeError

try:
    from mloader.response_pb2 import Response
except ImportError:
    Response = None

try:
    from tools.comic_info import build_comic_info_xml
    from tools.catalog_indexer import scan_and_index_volumes, get_volume_meta
except ImportError:
    from comic_info import build_comic_info_xml
    from catalog_indexer import scan_and_index_volumes, get_volume_meta


API_URL = "https://jumpg-webapi.tokyo-cdn.com/api/manga_viewer"


def extract_chapter_id(url_or_id: str | int) -> int:
    """Extracts numeric chapter ID from viewer URL or string."""
    match = re.search(r"(\d+)", str(url_or_id))
    if not match:
        raise ValueError(f"Could not extract numeric chapter ID from: {url_or_id}")
    return int(match.group(1))


def decrypt_image(encrypted_bytes: bytes, encryption_hex: str) -> bytearray:
    """Decrypts XOR-encrypted image payload from MangaPlus."""
    data = bytearray(encrypted_bytes)
    key = bytes.fromhex(encryption_hex)
    key_len = len(key)
    for i in range(len(data)):
        data[i] ^= key[i % key_len]
    return data


def download_mangaplus_chapter(
    chapter_url_or_id: str | int,
    output_dir: str | Path = "../frontend/public/comics",
    log_callback: Callable[[str], None] = print,
    sync_catalog: bool = True,
) -> str:
    """
    Downloads, decrypts, packs, and indexes a MangaPlus chapter into a clean CBZ.
    """
    chapter_id = extract_chapter_id(chapter_url_or_id)
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    session_token = str(uuid.uuid1())
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Origin": "https://mangaplus.shueisha.co.jp",
        "Referer": "https://mangaplus.shueisha.co.jp/",
        "SESSION-TOKEN": session_token,
    }

    log_callback(f"Connecting to MangaPlus API (Chapter ID: {chapter_id})...")
    resp = requests.get(
        API_URL,
        headers=headers,
        params={
            "chapter_id": chapter_id,
            "split": "yes",
            "img_quality": "super_high",
        },
        timeout=30,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"MangaPlus API returned HTTP {resp.status_code}")

    if b"Account Banned" in resp.content:
        raise RuntimeError("MangaPlus returned Account Banned (missing or invalid SESSION-TOKEN).")

    if Response is None:
        raise ImportError("mloader protobuf definitions not found. Ensure 'mloader' is installed.")

    try:
        api_res = Response.FromString(resp.content)
    except DecodeError as err:
        raise RuntimeError(f"Protobuf decode error: {err}")

    if not api_res.HasField("success"):
        raise RuntimeError("MangaPlus returned an error or unpublished chapter.")

    viewer = api_res.success.manga_viewer
    series_name = viewer.title_name or "One Piece"
    chapter_label = viewer.chapter_name or f"#{chapter_id}"
    chapter_num_match = re.search(r"(\d+)", chapter_label)
    chapter_number = int(chapter_num_match.group(1)) if chapter_num_match else chapter_id

    # Sub title / chapter title
    sub_title = ""
    if viewer.pages and viewer.pages[-1].HasField("last_page"):
        sub_title = viewer.pages[-1].last_page.current_chapter.sub_title or ""

    log_callback(f"Found: {series_name} — Chapter {chapter_label}: {sub_title}")

    # Collect valid pages
    manga_pages = [p.manga_page for p in viewer.pages if p.HasField("manga_page") and p.manga_page.image_url]
    total_pages = len(manga_pages)
    log_callback(f"Downloading {total_pages} decrypted pages...")

    # Determine destination CBZ filename
    clean_series = re.sub(r'[\\/*?:"<>|]', "", series_name)
    cbz_filename = f"{clean_series} - c{chapter_number:04d} [MangaPlus].cbz"
    cbz_dest = out_path / cbz_filename

    # Build ComicInfo.xml
    comic_info_xml = build_comic_info_xml(
        series=series_name,
        volume=112 if "one piece" in series_name.lower() and chapter_number >= 1100 else 1,
        number=chapter_number,
        ch_start=chapter_number,
        ch_end=chapter_number,
        count=total_pages,
        title=f"Chapter {chapter_number}: {sub_title}" if sub_title else f"Chapter {chapter_number}",
        summary=sub_title or f"Chapter {chapter_number} from MangaPlus.",
    )

    with zipfile.ZipFile(cbz_dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ComicInfo.xml", comic_info_xml.encode("utf-8"))

        for i, page in enumerate(manga_pages, 1):
            log_callback(f"Downloading & decrypting page {i}/{total_pages}...")
            img_resp = requests.get(page.image_url, headers=headers, timeout=20)
            if img_resp.status_code == 200:
                decrypted = decrypt_image(img_resp.content, page.encryption_key)
                z.writestr(f"page_{i:04d}.jpg", decrypted)
            else:
                log_callback(f"Warning: Failed to download page {i} (HTTP {img_resp.status_code})")

    log_callback(f"Successfully packaged: {cbz_dest.name} ({cbz_dest.stat().st_size // 1024} KB)")

    if sync_catalog:
        index_dest = out_path / "index.json"
        log_callback("Synchronizing catalog index.json...")
        scan_and_index_volumes(out_path, index_dest)
        log_callback("Catalog updated successfully!")

    return str(cbz_dest)


def main():
    parser = argparse.ArgumentParser(description="Download and package chapters from MangaPlus into CBZ")
    parser.add_argument("url", type=str, help="MangaPlus viewer URL (e.g. https://mangaplus.shueisha.co.jp/viewer/7002654)")
    parser.add_argument("-o", "--out", type=str, default="../frontend/public/comics", help="Output directory")
    parser.add_argument("--no-sync", action="store_true", help="Do not sync index.json")

    args = parser.parse_args()
    cbz_path = download_mangaplus_chapter(
        args.url,
        output_dir=args.out,
        sync_catalog=not args.no_sync,
    )
    print(f"\nDone! CBZ saved to:\n{cbz_path}")


if __name__ == "__main__":
    main()
