"""
mangaplus_downloader.py - Direct MangaPlus Downloader & CBZ Packager with Multi-Language Support.
Extracts chapters directly from MangaPlus using authenticated SESSION-TOKEN headers,
resolves chapters to the desired language (English, Spanish, French, etc.),
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
from typing import Callable, Optional, Tuple

import requests
from google.protobuf.internal.decoder import _DecodeVarint
from google.protobuf.message import DecodeError

try:
    from mloader.response_pb2 import Response
except ImportError:
    Response = None

try:
    from tools.comic_info import build_comic_info_xml
    from tools.catalog_indexer import scan_and_index_volumes
except ImportError:
    from comic_info import build_comic_info_xml
    from catalog_indexer import scan_and_index_volumes


API_VIEWER_URL = "https://jumpg-webapi.tokyo-cdn.com/api/manga_viewer"
API_TITLE_DETAIL_URL = "https://jumpg-webapi.tokyo-cdn.com/api/title_detailV3"

LANGUAGE_INFO = {
    "eng": {"name": "English", "iso": "en", "code": 0},
    "spa": {"name": "Spanish", "iso": "es", "code": 1},
    "fre": {"name": "French", "iso": "fr", "code": 2},
    "ind": {"name": "Indonesian", "iso": "id", "code": 3},
    "por": {"name": "Portuguese", "iso": "pt", "code": 4},
    "rus": {"name": "Russian", "iso": "ru", "code": 5},
    "tha": {"name": "Thai", "iso": "th", "code": 6},
    "deu": {"name": "German", "iso": "de", "code": 7},
    "vie": {"name": "Vietnamese", "iso": "vi", "code": 9},
}

# Cross-language MangaPlus title ID mappings for major series
TITLE_LANGUAGE_CATALOG = {
    "one piece": {
        "eng": 100020,
        "spa": 100037,
        "fre": 700005,
        "ind": 100080,
        "por": 100081,
        "rus": 100082,
        "tha": 100083,
        "deu": 100199,
    },
    "my hero academia": {
        "eng": 100017,
        "spa": 100038,
        "fre": 700007,
    },
    "jujutsu kaisen": {
        "eng": 100034,
        "spa": 100043,
        "fre": 700008,
    },
    "chainsaw man": {
        "eng": 100037,
        "spa": 100050,
        "fre": 700009,
    },
    "spy x family": {
        "eng": 100056,
        "spa": 100057,
        "fre": 700010,
    }
}


def get_default_headers(session_token: Optional[str] = None) -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Origin": "https://mangaplus.shueisha.co.jp",
        "Referer": "https://mangaplus.shueisha.co.jp/",
        "SESSION-TOKEN": session_token or str(uuid.uuid1()),
    }


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


def find_chapter_in_title_detail(
    title_id: int, 
    target_chapter_str: str, 
    headers: dict
) -> Optional[int]:
    """Finds the chapter ID in title_detailV3 matching target_chapter_str (e.g. '#1191')."""
    try:
        r = requests.get(
            API_TITLE_DETAIL_URL,
            headers=headers,
            params={"title_id": title_id},
            timeout=15,
        )
        if r.status_code != 200:
            return None

        norm_target = target_chapter_str.strip().replace("#", "")
        patterns = []
        if norm_target.isdigit():
            patterns.append(f"#{int(norm_target):0>3}".encode())
            patterns.append(f"#{int(norm_target)}".encode())
        else:
            patterns.append(target_chapter_str.encode())

        pos = -1
        for p in patterns:
            pos = r.content.find(p)
            if pos != -1:
                break

        if pos == -1:
            return None

        # Search backwards from pos for \x10 (field 2, varint chapter_id)
        for offset in range(3, 16):
            if r.content[pos - offset] == 0x10:
                val, _ = _DecodeVarint(r.content[pos - offset + 1:pos], 0)
                return val

        return None
    except Exception:
        return None


def resolve_chapter_to_language(
    chapter_id: int, 
    target_lang: str = "eng", 
    headers: Optional[dict] = None,
    log_callback: Callable[[str], None] = print,
) -> Tuple[int, str]:
    """
    Checks the language of the requested chapter_id.
    If it doesn't match target_lang, attempts cross-referencing to target_lang.
    Returns (resolved_chapter_id, actual_language_code).
    """
    hdrs = headers or get_default_headers()
    target_lang = target_lang.lower().strip()

    try:
        resp = requests.get(
            API_VIEWER_URL,
            headers=hdrs,
            params={"chapter_id": chapter_id, "split": "yes", "img_quality": "super_high"},
            timeout=20,
        )
        if resp.status_code != 200 or Response is None:
            return chapter_id, target_lang

        api_res = Response.FromString(resp.content)
        if not api_res.HasField("success"):
            return chapter_id, target_lang

        viewer = api_res.success.manga_viewer
        series_name = (viewer.title_name or "").strip()
        series_key = series_name.lower()
        chapter_label = viewer.chapter_name or ""
        current_title_id = getattr(viewer, "title_id", 0)

        # Look up target title ID in catalog
        if series_key in TITLE_LANGUAGE_CATALOG:
            lang_dict = TITLE_LANGUAGE_CATALOG[series_key]
            if target_lang in lang_dict:
                target_title_id = lang_dict[target_lang]
                if target_title_id != current_title_id:
                    lang_name = LANGUAGE_INFO.get(target_lang, {}).get("name", target_lang)
                    log_callback(f"Target language is {lang_name} ({target_lang}). Cross-referencing {series_name} {chapter_label}...")
                    found_id = find_chapter_in_title_detail(target_title_id, chapter_label, hdrs)
                    if found_id:
                        log_callback(f"Successfully resolved to {lang_name} Chapter ID: {found_id}")
                        return found_id, target_lang
                    else:
                        log_callback(f"Notice: Chapter {chapter_label} not found in {lang_name} catalog. Retaining original.")
                else:
                    return chapter_id, target_lang

        return chapter_id, target_lang
    except Exception as e:
        log_callback(f"Language resolution notice: {e}")
        return chapter_id, target_lang


def download_mangaplus_chapter(
    chapter_url_or_id: str | int,
    output_dir: str | Path = "../frontend/public/comics",
    target_lang: str = "eng",
    log_callback: Callable[[str], None] = print,
    sync_catalog: bool = True,
) -> str:
    """
    Downloads, decrypts, packs, and indexes a MangaPlus chapter into a clean CBZ
    with the selected language translation.
    """
    raw_chapter_id = extract_chapter_id(chapter_url_or_id)
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    headers = get_default_headers()

    # Resolve to desired language
    chapter_id, active_lang = resolve_chapter_to_language(
        raw_chapter_id, 
        target_lang=target_lang, 
        headers=headers, 
        log_callback=log_callback
    )

    lang_meta = LANGUAGE_INFO.get(active_lang, {"name": active_lang.upper(), "iso": active_lang})
    lang_label = lang_meta["name"]
    lang_iso = lang_meta["iso"]

    log_callback(f"Connecting to MangaPlus API (Chapter ID: {chapter_id}, Language: {lang_label})...")
    resp = requests.get(
        API_VIEWER_URL,
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

    log_callback(f"Downloading: {series_name} — Chapter {chapter_label} [{lang_label}]: {sub_title}")

    # Collect valid pages
    manga_pages = [p.manga_page for p in viewer.pages if p.HasField("manga_page") and p.manga_page.image_url]
    total_pages = len(manga_pages)
    if total_pages == 0:
        raise RuntimeError(f"No pages found for chapter {chapter_id} in {lang_label}.")

    log_callback(f"Unpacking {total_pages} decrypted pages...")

    # Determine destination CBZ filename: Chapter {number} - {sub_title}.cbz
    # (Note: Windows filesystems forbid colons, so ':' in titles is safely mapped to ' - ' in filenames)
    if sub_title:
        clean_sub = sub_title.replace(":", " - ").replace("/", "-").replace("\\", "-")
        clean_sub = re.sub(r'[*?"<>|]', "", clean_sub).strip()
        cbz_filename = f"Chapter {chapter_number} - {clean_sub}.cbz"
    else:
        cbz_filename = f"Chapter {chapter_number}.cbz"
    cbz_dest = out_path / cbz_filename

    # Build ComicRack-compliant ComicInfo.xml
    title_text = f"Chapter {chapter_number}: {sub_title}" if sub_title else f"Chapter {chapter_number}"
    comic_info_xml = build_comic_info_xml(
        series=series_name,
        volume=112 if "one piece" in series_name.lower() and chapter_number >= 1100 else 1,
        number=chapter_number,
        ch_start=chapter_number,
        ch_end=chapter_number,
        count=total_pages,
        title=title_text,
        summary=sub_title or f"Chapter {chapter_number} [{lang_label}] from MangaPlus.",
        language_iso=lang_iso,
    )

    with zipfile.ZipFile(cbz_dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ComicInfo.xml", comic_info_xml.encode("utf-8"))

        for i, page in enumerate(manga_pages, 1):
            if i % 3 == 0 or i == total_pages:
                log_callback(f"Decrypting page {i}/{total_pages}...")
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
    parser = argparse.ArgumentParser(description="Download and package chapters from MangaPlus into CBZ with language selection")
    parser.add_argument("url", type=str, help="MangaPlus viewer URL (e.g. https://mangaplus.shueisha.co.jp/viewer/7002654)")
    parser.add_argument("-o", "--out", type=str, default="../frontend/public/comics", help="Output directory")
    parser.add_argument("-l", "--lang", type=str, default="eng", choices=list(LANGUAGE_INFO.keys()), help="Target language (eng, spa, fre, ind, por, deu, tha, rus, vie) [default: eng]")
    parser.add_argument("--no-sync", action="store_true", help="Do not sync index.json")

    args = parser.parse_args()
    cbz_path = download_mangaplus_chapter(
        args.url,
        output_dir=args.out,
        target_lang=args.lang,
        sync_catalog=not args.no_sync,
    )
    print(f"\nDone! CBZ saved to:\n{cbz_path}")


if __name__ == "__main__":
    main()
