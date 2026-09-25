"""
mangadex_downloader.py - Downloads One Piece chapters from MangaDex
for chapters that are app-locked on MangaPlus.
Supports single chapters and ranges (e.g. '1 - 1190' or '1-10').
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
from typing import Callable, Dict, List, Optional, Set, Tuple

import requests

try:
    from tools.comic_info import build_comic_info_xml, format_chapter_filename, format_chapter_display_title, clean_chapter_sub_title
    from tools.catalog_indexer import scan_and_index_volumes
except ImportError:
    from comic_info import build_comic_info_xml, format_chapter_filename, format_chapter_display_title, clean_chapter_sub_title
    from catalog_indexer import scan_and_index_volumes

MANGADEX_API_BASE = "https://api.mangadex.org"

# MangaDex Series UUIDs for One Piece
ONE_PIECE_MANGA_IDS = {
    "colored": "a2c1d849-af05-4bbc-b2a7-866ebb10331f",  # Official Digital Colored Edition (Ch 1-764+)
    "bw": "a1c7c817-4e59-43b7-9365-09675a149a6f",       # Standard Black & White Edition (MangaPlus external links)
}

try:
    from tools.weebcentral_downloader import download_weebcentral_chapter, download_weebcentral_batch
except ImportError:
    try:
        from weebcentral_downloader import download_weebcentral_chapter, download_weebcentral_batch
    except ImportError:
        download_weebcentral_chapter = None
        download_weebcentral_batch = None


DEFAULT_HEADERS = {
    "User-Agent": "MangaShowcasePlatform/1.0 (https://github.com/mrsdbskn/Manga)",
}


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
            valid_chapters = [
                c for c in data 
                if not c.get("attributes", {}).get("externalUrl") 
                and c.get("attributes", {}).get("pages", 0) > 0
            ]
            if valid_chapters:
                chosen = valid_chapters[0]
                chosen["_edition"] = ed
                return chosen
        except Exception:
            pass

    # Also search global uploads across all One Piece entries
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
    except Exception:
        pass

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
    Downloads a single One Piece chapter from MangaDex, packages into Chapter {num} - {title}.cbz,
    injects ComicInfo.xml, and optionally refreshes the showcase catalog.
    If edition is B&W or if MangaDex lacks internal pages (e.g. app-locked middle chapters or chapters >764),
    gracefully routes/falls back to the official Viz Media B&W provider (WeebCentral).
    """
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    # Route B&W directly to official Viz provider if available
    if edition == "bw" and download_weebcentral_chapter is not None:
        log_callback(f"Edition selected: Standard B&W (Official Viz). Routing to WeebCentral provider...")
        return download_weebcentral_chapter(
            chapter_num=chapter_num,
            output_dir=out_path,
            sync_catalog=sync_catalog,
            log_callback=log_callback,
        )

    ch_meta = find_chapter_on_mangadex(chapter_num, lang=lang, edition=edition, log_callback=log_callback)
    if not ch_meta:
        if download_weebcentral_chapter is not None:
            log_callback(f"Notice: Chapter {chapter_num} ({edition}) not directly downloadable on MangaDex (middle chapters or post-764 lack internal pages due to MangaPlus external redirection).")
            log_callback("Seamlessly falling back to Official Viz Media B&W provider (WeebCentral)...")
            return download_weebcentral_chapter(
                chapter_num=chapter_num,
                output_dir=out_path,
                sync_catalog=sync_catalog,
                log_callback=log_callback,
            )
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
    log_callback(f"Downloading {total_pages} pages from CDN node...")

    # Determine destination CBZ filename (guaranteeing no duplicate Chapter X - Chapter X prefixes)
    cbz_filename = format_chapter_filename(ch_int, sub_title)
    cbz_dest = out_path / cbz_filename

    # Build ComicRack-compliant ComicInfo.xml
    title_text = format_chapter_display_title(ch_int, sub_title)
    clean_summary = clean_chapter_sub_title(sub_title, ch_int)
    comic_info_xml = build_comic_info_xml(
        series="One Piece (Digital Colored)" if ed_used == "colored" else "One Piece",
        volume=vol_num,
        number=ch_int,
        ch_start=ch_int,
        ch_end=ch_int,
        count=total_pages,
        title=title_text,
        summary=clean_summary or f"One Piece Chapter {ch_int} ({ed_used.capitalize()}) from MangaDex.",
        language_iso=lang,
    )

    path_mode = "data-saver" if data_saver else "data"
    with zipfile.ZipFile(cbz_dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ComicInfo.xml", comic_info_xml.encode("utf-8"))

        for i, fname in enumerate(file_list, 1):
            img_url = f"{base_url}/{path_mode}/{ch_hash}/{fname}"
            ext = Path(fname).suffix or ".jpg"

            # Download page with up to 3 retries
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

            # Polite rate limiting
            time.sleep(0.08)

    file_size_kb = cbz_dest.stat().st_size // 1024
    log_callback(f"Successfully packaged: {cbz_dest.name} ({file_size_kb} KB)")

    if sync_catalog:
        index_dest = out_path / "index.json"
        log_callback("Synchronizing catalog index.json...")
        scan_and_index_volumes(out_path, index_dest)
        log_callback("Catalog updated successfully!")

    return str(cbz_dest)


def download_mangadex_batch(
    chapter_spec: str | int,
    output_dir: str | Path,
    lang: str = "en",
    edition: str = "colored",
    data_saver: bool = False,
    skip_existing: bool = True,
    sync_catalog: bool = True,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    log_callback: Callable[[str], None] = print,
    cancel_flag: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """
    Downloads a batch or range of chapters (e.g. '1-1190' or '1, 5, 10-20') from MangaDex.
    Skips already existing CBZ files, logs progress, and synchronizes the catalog index once at the end.
    """
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    chapters = parse_chapter_range(str(chapter_spec))
    total_chapters = len(chapters)

    if total_chapters == 0:
        raise ValueError(f"No valid chapters found in specification: '{chapter_spec}'")

    if edition == "bw" and download_weebcentral_batch is not None:
        log_callback("Standard B&W selected: routing batch to Official Viz Media B&W provider (WeebCentral 1-1193+)...")
        return download_weebcentral_batch(
            chapter_spec=chapter_spec,
            output_dir=out_path,
            skip_existing=skip_existing,
            sync_catalog=sync_catalog,
            progress_callback=progress_callback,
            log_callback=log_callback,
            cancel_flag=cancel_flag,
        )

    log_callback(f"=== Starting MangaDex Batch: {total_chapters} Chapter(s) ({chapter_spec}) ===")
    log_callback(f"Destination: {out_path}")
    log_callback(f"Edition: {edition.upper()} | Language: {lang.upper()}\n")


    downloaded = 0
    skipped = 0
    failed = []

    for idx, ch_num in enumerate(chapters, 1):
        if cancel_flag and cancel_flag():
            log_callback("\n[Cancelled] Batch download was cancelled by user.")
            break

        # Check if already downloaded
        if skip_existing:
            existing = is_chapter_already_downloaded(out_path, ch_num)
            if existing:
                skipped += 1
                status = f"[{idx}/{total_chapters}] Ch. {ch_num}: Already exists ({existing.name}) -> Skipped"
                log_callback(status)
                if progress_callback:
                    progress_callback(idx / total_chapters, status)
                continue

        status = f"[{idx}/{total_chapters}] Processing Chapter {ch_num}..."
        log_callback(status)
        if progress_callback:
            progress_callback(idx / total_chapters, status)

        try:
            download_mangadex_chapter(
                chapter_num=ch_num,
                output_dir=out_path,
                lang=lang,
                edition=edition,
                data_saver=data_saver,
                sync_catalog=False,  # Defer sync until the end of batch
                log_callback=lambda msg: log_callback(f"   {msg}"),
            )
            downloaded += 1
        except Exception as e:
            log_callback(f"   [Notice] Could not download Chapter {ch_num}: {e}")
            failed.append((ch_num, str(e)))

        # Polite delay between chapters
        time.sleep(0.3)

    log_callback("\n=== MangaDex Batch Summary ===")
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
    parser = argparse.ArgumentParser(description="Download One Piece chapters or ranges from MangaDex and package into CBZ")
    parser.add_argument("chapter", type=str, help="Chapter number or range to download (e.g. 4, '1-10', '1 - 1190')")
    parser.add_argument("-o", "--out", type=str, default="../frontend/public/comics", help="Output directory")
    parser.add_argument("-l", "--lang", type=str, default="en", help="Language code (en, es, fr, de, etc.) [default: en]")
    parser.add_argument("-e", "--edition", type=str, default="colored", choices=["colored", "bw"], help="Preferred edition (colored or bw) [default: colored]")
    parser.add_argument("--data-saver", action="store_true", help="Download compressed data-saver images")
    parser.add_argument("--force", action="store_true", help="Force re-download even if chapter already exists")
    parser.add_argument("--no-sync", action="store_true", help="Do not sync index.json")

    args = parser.parse_args()
    try:
        download_mangadex_batch(
            chapter_spec=args.chapter,
            output_dir=args.out,
            lang=args.lang,
            edition=args.edition,
            data_saver=args.data_saver,
            skip_existing=not args.force,
            sync_catalog=not args.no_sync,
        )
    except Exception as err:
        print(f"\nError: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
