"""
fetch_shueisha_covers.py - Downloads official high-resolution front and back covers (1200px)
for all One Piece volumes directly from Shueisha's official catalog (seriesid=35169).
Generates both .jpg and optimized .webp for 3D showcase renders.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import sys
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

SHUEISHA_SEARCH_URL = "https://www.shueisha.co.jp/books/search/search.html?seriesid=35169&order=1"
SHUEISHA_CONTENTS_URL = "https://www.shueisha.co.jp/books/items/contents.html?isbn={isbn}"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.shueisha.co.jp/books/",
}


def get_all_series_items() -> List[Dict[str, Any]]:
    """Fetches the complete volume listing for ONE PIECE from Shueisha series search."""
    print("Fetching volume index from Shueisha (seriesid=35169)...")
    res = requests.get(SHUEISHA_SEARCH_URL, headers=DEFAULT_HEADERS, timeout=20)
    if res.status_code != 200:
        raise RuntimeError(f"Failed to fetch Shueisha search page (status {res.status_code})")

    m = re.search(r"var\s+ssd\s*=\s*(\{.*?\});\s*\n", res.text)
    if not m:
        raise RuntimeError("Could not find embedded 'ssd' volume data on Shueisha search page.")

    data = json.loads(m.group(1))
    items = data.get("data", {}).get("item_datas", [])
    print(f"Discovered {len(items)} volumes on official Shueisha platform.")
    return items


def fetch_volume_cover_urls(item: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieves front and back cover URLs from individual volume contents page."""
    vol_raw = item.get("volume_number") or item.get("view_volume_number")
    try:
        vol_num = int(float(vol_raw))
    except Exception:
        vol_num = int(re.search(r"\d+", str(vol_raw)).group(0))

    isbn = item.get("isbn", "").strip()
    result = {
        "volume": vol_num,
        "isbn": isbn,
        "releaseDate": item.get("release_date", ""),
        "frontUrl": None,
        "backUrl": None,
        "spineUrl": None,
    }

    if not isbn:
        return result

    # Fetch volume details page
    try:
        url = SHUEISHA_CONTENTS_URL.format(isbn=isbn)
        res = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
        if res.status_code == 200:
            m = re.search(r"var\s+ssd\s*=\s*(\{.*?\});\s*\n", res.text)
            if m:
                v_data = json.loads(m.group(1))
                datas = v_data.get("datas", [])
                if datas:
                    image_datas = datas[0].get("image_datas", [])
                    for img in image_datas:
                        b_type = str(img.get("book_type", ""))
                        seq = img.get("seq", 0)
                        img_url = img.get("image_url_l") or img.get("image_url_m")
                        if not img_url:
                            continue

                        # Front cover: book_type 1 or seq 100
                        if (b_type == "1" or seq == 100) and not result["frontUrl"]:
                            result["frontUrl"] = img_url
                        # Back cover: book_type 3 or seq 130 or _130 in URL
                        elif (b_type == "3" or seq == 130 or "_130" in img_url) and not result["backUrl"]:
                            result["backUrl"] = img_url
                        # Spine / other flap: seq 150
                        elif (b_type == "9" or seq == 150) and not result["spineUrl"]:
                            result["spineUrl"] = img_url

                    # Fallback if frontUrl not set
                    if not result["frontUrl"] and image_datas:
                        result["frontUrl"] = image_datas[0].get("image_url_l")
    except Exception as e:
        print(f"  [Vol {vol_num}] Error fetching contents page: {e}")

    # Direct CloudFront fallback if front or back cover URL was missing
    clean_isbn = isbn.replace("-", "")
    if not result["frontUrl"]:
        result["frontUrl"] = f"https://dosbg3xlm0x1t.cloudfront.net/images/items/{clean_isbn}/1200/{clean_isbn}.jpg"
    if not result["backUrl"]:
        result["backUrl"] = f"https://dosbg3xlm0x1t.cloudfront.net/images/items/{clean_isbn}/1200/{clean_isbn}_130.jpg"

    return result


def save_image_as_jpg_and_webp(image_bytes: bytes, jpg_path: Path, webp_path: Path, force: bool = False):
    """Saves raw bytes to JPG and generates an optimized WebP version."""
    if not force and jpg_path.exists() and webp_path.exists():
        return

    jpg_path.parent.mkdir(parents=True, exist_ok=True)
    webp_path.parent.mkdir(parents=True, exist_ok=True)

    im = Image.open(BytesIO(image_bytes))
    if im.mode in ("RGBA", "P"):
        im = im.convert("RGB")

    # Save JPG
    im.save(jpg_path, format="JPEG", quality=92, optimize=True)

    # Save WebP
    im.save(webp_path, format="WEBP", quality=85)


def download_and_save_cover(
    vol_num: int,
    cover_type: str,  # 'front', 'back', or 'spine'
    url: str,
    target_dirs: List[Path],
    force: bool = False,
) -> bool:
    """Downloads an image from URL and saves to target directories as JPG and WebP."""
    if cover_type == "front":
        prefix = "cover"
    elif cover_type == "back":
        prefix = "back-cover"
    else:
        prefix = "spine"
    base_name = f"{prefix}-v{vol_num:02d}"

    # Check if first target directory already has both files
    primary_jpg = target_dirs[0] / f"{base_name}.jpg"
    primary_webp = target_dirs[0] / f"{base_name}.webp"
    if not force and primary_jpg.exists() and primary_webp.exists() and primary_jpg.stat().st_size > 10000:
        # Just ensure other target dirs have copies
        for td in target_dirs[1:]:
            td_jpg = td / f"{base_name}.jpg"
            td_webp = td / f"{base_name}.webp"
            if not td_jpg.exists() or force:
                td_jpg.write_bytes(primary_jpg.read_bytes())
            if not td_webp.exists() or force:
                td_webp.write_bytes(primary_webp.read_bytes())
        return True

    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=20)
        if r.status_code != 200 or len(r.content) < 5000:
            return False

        # Save to primary and mirror to others
        save_image_as_jpg_and_webp(r.content, primary_jpg, primary_webp, force=force)
        for td in target_dirs[1:]:
            td_jpg = td / f"{base_name}.jpg"
            td_webp = td / f"{base_name}.webp"
            td.mkdir(parents=True, exist_ok=True)
            td_jpg.write_bytes(primary_jpg.read_bytes())
            td_webp.write_bytes(primary_webp.read_bytes())

        return True
    except Exception as e:
        print(f"  [Vol {vol_num}] Failed downloading {cover_type} cover from {url}: {e}")
        return False


def process_volume(
    meta: Dict[str, Any],
    target_dirs: List[Path],
    force_front: bool = False,
    force_back: bool = False,
    include_spine: bool = False,
) -> Dict[str, Any]:
    vol_num = meta["volume"]
    front_ok = False
    back_ok = False
    spine_ok = False

    if meta.get("frontUrl"):
        front_ok = download_and_save_cover(
            vol_num=vol_num,
            cover_type="front",
            url=meta["frontUrl"],
            target_dirs=target_dirs,
            force=force_front,
        )

    if meta.get("backUrl"):
        back_ok = download_and_save_cover(
            vol_num=vol_num,
            cover_type="back",
            url=meta["backUrl"],
            target_dirs=target_dirs,
            force=force_back,
        )

    if include_spine and meta.get("spineUrl"):
        spine_ok = download_and_save_cover(
            vol_num=vol_num,
            cover_type="spine",
            url=meta["spineUrl"],
            target_dirs=target_dirs,
            force=force_front,
        )

    status = []
    if front_ok: status.append("Front OK")
    if back_ok: status.append("Back OK")
    if spine_ok: status.append("Spine OK")
    print(f"Volume {vol_num:02d}: {', '.join(status) if status else 'None'}")

    return {
        "volume": vol_num,
        "isbn": meta.get("isbn"),
        "frontSaved": front_ok,
        "backSaved": back_ok,
        "spineSaved": spine_ok,
        "frontUrl": meta.get("frontUrl"),
        "backUrl": meta.get("backUrl"),
        "spineUrl": meta.get("spineUrl"),
    }


def main():
    parser = argparse.ArgumentParser(description="Download official Shueisha Front, Back & Spine Covers")
    parser.add_argument("--workers", type=int, default=8, help="Parallel worker threads")
    parser.add_argument("--volume", type=int, default=None, help="Download only a specific volume number (e.g. 115)")
    parser.add_argument("--force", action="store_true", help="Force re-download all covers")
    parser.add_argument("--force-front", action="store_true", help="Force update front covers with 1200px Shueisha covers")
    parser.add_argument("--include-spine", action="store_true", help="Also download official 3D perspective spine/cover image (_150.jpg) when available")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    public_covers = script_dir.parent / "frontend" / "public" / "comics" / "covers"
    dist_covers = script_dir.parent / "frontend" / "dist" / "comics" / "covers"
    root_covers = script_dir.parent.parent / "frontend" / "public" / "comics" / "covers"

    target_dirs: List[Path] = [public_covers]
    if dist_covers.parent.exists():
        target_dirs.append(dist_covers)
    if root_covers.parent.exists() and root_covers != public_covers:
        target_dirs.append(root_covers)

    for td in target_dirs:
        td.mkdir(parents=True, exist_ok=True)

    items = get_all_series_items()
    if args.volume:
        items = [it for it in items if int(float(it.get("volume_number") or it.get("view_volume_number") or 0)) == args.volume]
        print(f"Filtered to Volume {args.volume}.")

    print(f"\nResolving cover image URLs for all {len(items)} volumes in parallel...")
    volume_metas: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_volume_cover_urls, it): it for it in items}
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                volume_metas.append(res)
            except Exception as e:
                print(f"Error resolving volume cover URLs: {e}")

    volume_metas.sort(key=lambda x: x["volume"])
    print(f"Resolved cover endpoints for {len(volume_metas)} volumes.")

    print(f"\nDownloading high-res covers (1200px) & generating WebPs with {args.workers} workers...")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                process_volume,
                meta,
                target_dirs,
                args.force or args.force_front,
                args.force or True,  # Back covers are always downloaded since they were missing!
                args.include_spine,
            ): meta
            for meta in volume_metas
        }
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda x: x["volume"])

    # Save summary metadata
    meta_path = script_dir / "shueisha_covers_metadata.json"
    pub_meta = public_covers / "shueisha_covers_metadata.json"

    payload = {str(r["volume"]): r for r in results}
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(pub_meta, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    front_count = len(list(public_covers.glob("cover-v*.jpg")))
    back_count = len(list(public_covers.glob("back-cover-v*.jpg")))
    print(f"\nDone! Public covers directory now has {front_count} Front Covers and {back_count} Back Covers!")


if __name__ == "__main__":
    main()
