"""
volume_bundler.py - Canon One Piece volume bundler and auto-detector.
Inspects a directory for chapter CBZ files (strictly ignoring 'covers' subfolder),
matches them against canon volume taxonomy, and bundles constituent chapter CBZs
into official volume archives with:
  1. Official volume cover from /comics/covers as page_0000_cover.jpg (first page)
  2. Constituent chapter pages (page_0001 ... page_NNNN)
  3. Aesthetic dark back-cover with official Viz Media synopsis and metadata (last page)
  4. Standard ComicRack ComicInfo.xml metadata
"""

from __future__ import annotations

import argparse
import io
import json
import os
import random
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from tools.comic_info import (
        build_comic_info_xml,
        clean_volume_sub_title,
        format_volume_filename,
        format_volume_display_title,
        clean_chapter_sub_title,
        format_chapter_filename,
        format_chapter_display_title,
        read_comic_info_from_cbz,
    )
    from tools.catalog_indexer import get_volume_meta, scan_and_index_volumes, CANON_VOLUMES_DATA
except ImportError:
    from comic_info import (
        build_comic_info_xml,
        clean_volume_sub_title,
        format_volume_filename,
        format_volume_display_title,
        clean_chapter_sub_title,
        format_chapter_filename,
        format_chapter_display_title,
        read_comic_info_from_cbz,
    )
    from catalog_indexer import get_volume_meta, scan_and_index_volumes, CANON_VOLUMES_DATA

VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}


def natural_sort_key(s: str) -> List[Any]:
    """Sort strings with embedded numbers naturally (e.g. page 2 before page 10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", str(s))]


def is_covers_path(path: Path | str) -> bool:
    """Checks if a path belongs to the 'covers' directory or contains 'covers'."""
    p = Path(path)
    return any(part.lower() == "covers" for part in p.parts)


def load_canon_volumes_dict() -> Dict[int, Dict[str, Any]]:
    """Loads complete canon volume catalog from canon_volume_titles.json or fallback."""
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir / "canon_volume_titles.json",
        script_dir.parent / "frontend" / "public" / "comics" / "canon_volume_titles.json",
        script_dir / "canon_volumes_complete.json",
    ]
    data: Dict[int, Dict[str, Any]] = {}
    for canon_file in candidates:
        if canon_file.exists():
            try:
                with open(canon_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for k, v in raw.items():
                        v_num = int(k)
                        data[v_num] = {
                            "title": v.get("title") or f"Volume {k}",
                            "japaneseTitle": v.get("japaneseTitle", ""),
                            "ch_start": int(v.get("ch_start", 1)) if v.get("ch_start") is not None else max(1, (v_num - 1) * 10 + 1),
                            "ch_end": int(v.get("ch_end", 1)) if v.get("ch_end") is not None else max(1, (v_num - 1) * 10 + 10),
                            "summary": v.get("summary", ""),
                            "originalReleaseDate": v.get("originalReleaseDate", ""),
                            "licensedReleaseDate": v.get("licensedReleaseDate", ""),
                            "originalISBN": v.get("originalISBN", ""),
                            "licensedISBN": v.get("licensedISBN", ""),
                        }
                    if data:
                        break
            except Exception:
                pass

    # Merge with CANON_VOLUMES_DATA for any remaining gaps
    for k, v in CANON_VOLUMES_DATA.items():
        if k not in data:
            data[k] = {
                "title": v.get("title", f"Volume {k}"),
                "japaneseTitle": v.get("japaneseTitle", ""),
                "ch_start": int(v.get("ch_start", 1)),
                "ch_end": int(v.get("ch_end", 1)),
                "summary": v.get("summary", ""),
            }
    return data


def find_covers_dir(candidate_dirs: Optional[List[Optional[Path | str]]] = None) -> Optional[Path]:
    """Resolves the covers directory containing volume cover images and viz_volumes_metadata.json."""
    if candidate_dirs:
        for cd in candidate_dirs:
            if not cd:
                continue
            p = Path(cd).resolve()
            if p.is_dir() and p.name.lower() == "covers":
                return p
            p_sub = p / "covers"
            if p_sub.is_dir():
                return p_sub

    # Standard project locations fallback
    script_dir = Path(__file__).resolve().parent
    standard_paths = [
        script_dir.parent / "frontend" / "public" / "comics" / "covers",
        script_dir / "covers",
        script_dir.parent / "covers",
    ]
    for sp in standard_paths:
        if sp.is_dir():
            return sp
    return None


def find_volume_cover_file(covers_dir: Optional[Path], vol_num: int) -> Optional[Path]:
    """Finds the front cover image file for a given volume number (e.g. cover-v01.jpg or cover-v14.webp)."""
    if not covers_dir or not covers_dir.is_dir():
        return None

    # Priority candidate names
    v2 = f"{vol_num:02d}" if vol_num < 100 else f"{vol_num}"
    candidates = [
        f"cover-v{v2}.jpg",
        f"cover-v{v2}.webp",
        f"cover-v{v2}.png",
        f"cover-v{vol_num}.jpg",
        f"cover-v{vol_num}.webp",
        f"cover-v{vol_num}.png",
        f"cover_v{v2}.jpg",
        f"cover_v{vol_num}.jpg",
    ]
    for cand in candidates:
        fp = covers_dir / cand
        if fp.is_file() and fp.stat().st_size > 500:
            return fp

    # Regex fallback search in covers_dir
    pattern = re.compile(rf"^cover[-_]v?0*{vol_num}\.(jpg|jpeg|webp|png)$", re.IGNORECASE)
    for f in covers_dir.iterdir():
        if f.is_file() and pattern.match(f.name) and f.stat().st_size > 500:
            return f

    return None


def find_volume_back_cover_file(covers_dir: Optional[Path], vol_num: int) -> Optional[Path]:
    """Finds the back cover image file for a given volume number (e.g. back-cover-v01.jpg or back-cover-v115.webp)."""
    if not covers_dir or not covers_dir.is_dir():
        return None

    v2 = f"{vol_num:02d}" if vol_num < 100 else f"{vol_num}"
    candidates = [
        f"back-cover-v{v2}.jpg",
        f"back-cover-v{v2}.webp",
        f"back-cover-v{v2}.png",
        f"back-cover-v{vol_num}.jpg",
        f"back-cover-v{vol_num}.webp",
        f"back-cover-v{vol_num}.png",
        f"back_cover_v{v2}.jpg",
        f"back_cover_v{vol_num}.jpg",
    ]
    for cand in candidates:
        fp = covers_dir / cand
        if fp.is_file() and fp.stat().st_size > 500:
            return fp

    pattern = re.compile(rf"^back[-_]cover[-_]v?0*{vol_num}\.(jpg|jpeg|webp|png)$", re.IGNORECASE)
    for f in covers_dir.iterdir():
        if f.is_file() and pattern.match(f.name) and f.stat().st_size > 500:
            return f

    return None


def load_viz_volumes_metadata(covers_dir: Optional[Path] = None) -> Dict[int, Dict[str, Any]]:
    """Loads cached Viz Media metadata JSON containing descriptions, ISBNs, and specs for all volumes."""
    search_paths = []
    if covers_dir:
        search_paths.append(covers_dir / "viz_volumes_metadata.json")

    script_dir = Path(__file__).resolve().parent
    search_paths.extend([
        script_dir.parent / "frontend" / "public" / "comics" / "covers" / "viz_volumes_metadata.json",
        script_dir / "viz_volumes_metadata.json",
        script_dir.parent / "viz_volumes_metadata.json",
    ])

    for sp in search_paths:
        if sp.is_file():
            try:
                with open(sp, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    return {int(k): v for k, v in raw.items()}
            except Exception:
                pass
    return {}


def get_system_font(size: int, bold: bool = False):
    """Attempts to load a standard clean system font (Segoe UI, Arial, Calibri, Roboto), fallback to default."""
    if not PIL_AVAILABLE:
        return None
    font_names = [
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for fn in font_names:
        try:
            return ImageFont.truetype(fn, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def wrap_text_lines(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wraps text cleanly within max_width pixels."""
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        try:
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
        except AttributeError:
            try:
                w, _ = draw.textsize(test_line, font=font)
            except Exception:
                w = len(test_line) * 10
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def generate_volume_back_cover_bytes(
    vol_num: int,
    viz_meta: Dict[str, Any],
    width: int = 1200,
    height: int = 1800,
) -> bytes:
    """
    Renders an authentic dark back-cover JPEG resembling the web app's 3D render,
    complete with the official Viz Media synopsis, metadata grid, barcode block, and publisher taglines.
    """
    if not PIL_AVAILABLE:
        # Minimal empty image if Pillow is not available
        img = Image.new("RGB", (width, height), color="#10121a")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()

    img = Image.new("RGB", (width, height), color="#10121a")
    draw = ImageDraw.Draw(img)

    # 1. Subtle background glow / vignette
    for r in range(16):
        alpha = int(8 - r * 0.5)
        if alpha > 0:
            inset = r * 8
            draw.rectangle([inset, inset, width - inset, height - inset], outline="#1a1d2e", width=4)

    # 2. Outer decorative frame
    margin = 44
    draw.rectangle([margin, margin, width - margin, height - margin], outline="#2a2f45", width=2)
    draw.rectangle([margin + 6, margin + 6, width - margin - 6, height - margin - 6], outline="#1a1d2e", width=1)

    # 3. Watermark volume number in background
    f_watermark = get_system_font(320, bold=True)
    if f_watermark:
        wm_text = str(vol_num)
        draw.text((width - 340, height - 520), wm_text, fill="#161926", font=f_watermark)

    # 4. Header banner
    f_head = get_system_font(26, bold=True)
    f_sub = get_system_font(22, bold=True)
    draw.text((margin + 30, margin + 30), "SHONEN JUMP • VIZ MEDIA", fill="#94a3b8", font=f_head)
    vol_tag = f"VOLUME {vol_num}"
    draw.text((width - margin - 180, margin + 30), vol_tag, fill="#38bdf8", font=f_sub)

    # Divider
    draw.line([margin + 30, margin + 75, width - margin - 30, margin + 75], fill="#272c3d", width=2)

    # 5. Synopsis Text
    synopsis = viz_meta.get("description", "")
    if not synopsis:
        synopsis = "Monkey D. Luffy sets out on his grand pirate adventure across the Grand Line in search of the legendary One Piece, said to be the greatest treasure in the world."

    f_quote = get_system_font(42, bold=True)
    draw.text((margin + 30, margin + 95), "“", fill="#38bdf8", font=f_quote)

    f_body = get_system_font(23, bold=False)
    max_text_width = width - (margin * 2) - 80
    lines = wrap_text_lines(synopsis, f_body, max_text_width, draw)

    y_text = margin + 130
    line_height = 36
    for line in lines[:16]:  # Limit to 16 lines max
        draw.text((margin + 40, y_text), line, fill="#cbd5e1", font=f_body)
        y_text += line_height

    # 6. Metadata Section (Two Column Grid)
    y_meta = max(y_text + 40, height - 680)
    draw.line([margin + 30, y_meta - 20, width - margin - 30, y_meta - 20], fill="#272c3d", width=2)

    f_meta_lbl = get_system_font(20, bold=True)
    f_meta_val = get_system_font(20, bold=False)

    meta_items = [
        ("Story & Art by:", viz_meta.get("story_and_art", "Eiichiro Oda")),
        ("Series:", viz_meta.get("series", "One Piece")),
        ("Release Date:", viz_meta.get("release", "")),
        ("ISBN-13:", viz_meta.get("isbn13", "")),
        ("UPC:", viz_meta.get("upc", "")),
        ("Trim Size:", viz_meta.get("trim_size", "5 × 7 1/2")),
        ("Imprint:", viz_meta.get("imprint", "SHONEN JUMP")),
        ("Length:", viz_meta.get("length", "")),
        ("Category:", viz_meta.get("category", "Manga")),
        ("Age Rating:", viz_meta.get("age_rating", "Teen")),
    ]

    col1_x = margin + 40
    col2_x = width // 2 + 20
    cur_y = y_meta

    for i, (label, val) in enumerate(meta_items):
        if not val:
            continue
        cx = col1_x if (i % 2 == 0) else col2_x
        draw.text((cx, cur_y), label, fill="#64748b", font=f_meta_lbl)
        draw.text((cx + 170, cur_y), str(val), fill="#f8fafc", font=f_meta_val)
        if i % 2 == 1:
            cur_y += 42
    if len(meta_items) % 2 == 1:
        cur_y += 42

    # 7. Barcode Box at Bottom
    y_barcode = height - margin - 150
    draw.line([margin + 30, y_barcode - 20, width - margin - 30, y_barcode - 20], fill="#272c3d", width=2)

    bc_x = margin + 40
    bc_w = 260
    bc_h = 75
    draw.rectangle([bc_x, y_barcode, bc_x + bc_w, y_barcode + bc_h], fill="#ffffff")

    # Barcode vertical stripes
    rng = random.Random(vol_num * 42)
    stripe_x = bc_x + 10
    while stripe_x < bc_x + bc_w - 10:
        sw = rng.choice([2, 3, 4, 6])
        draw.rectangle([stripe_x, y_barcode + 6, stripe_x + sw, y_barcode + bc_h - 16], fill="#000000")
        stripe_x += sw + rng.choice([2, 3, 4])

    f_bc_num = get_system_font(12, bold=True)
    draw.text((bc_x + 35, y_barcode + bc_h - 14), viz_meta.get("isbn13", "978-1-56931-901-7"), fill="#000000", font=f_bc_num)

    # Publisher & Format Tagline
    f_pub = get_system_font(16, bold=False)
    draw.text((bc_x + bc_w + 30, y_barcode + 15), "PUBLISHED BY VIZ MEDIA, LLC", fill="#94a3b8", font=f_meta_lbl)
    draw.text((bc_x + bc_w + 30, y_barcode + 45), "AUTHENTIC RIGHT-TO-LEFT MANGA FORMAT", fill="#64748b", font=f_pub)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def first_chapter_has_volume_cover(
    ch_cbz_path: Path,
    vol_num: int,
    covers_dir: Optional[Path] = None,
) -> bool:
    """
    Checks if the first chapter of a volume already includes a volume cover as its opening page.
    VIZ digital releases routinely place the full-color volume cover as page 1 of the opening chapter
    (e.g., Chapter 1, 9, 18, 27...). Later weekly chapters or scanlations do not have volume covers.
    Returns True if detected, preventing duplicate covers.
    """
    if not ch_cbz_path.exists():
        return False

    try:
        with zipfile.ZipFile(ch_cbz_path, "r") as z:
            img_names = [
                n for n in z.namelist()
                if Path(n).suffix.lower() in VALID_IMAGE_EXTS
                and not n.startswith("__MACOSX")
                and not is_covers_path(n)
            ]
            if not img_names:
                return False
            img_names.sort(key=natural_sort_key)
            first_img_name = img_names[0]

            # 1. Direct filename indicator
            if "cover" in first_img_name.lower():
                return True

            if not PIL_AVAILABLE:
                return False

            first_bytes = z.read(first_img_name)
            im1 = Image.open(io.BytesIO(first_bytes))
            stat1 = im1.convert("HSV").split()[1]
            data1 = list(stat1.get_flattened_data()) if hasattr(stat1, "get_flattened_data") else list(stat1.getdata())
            sat1 = sum(data1) / len(data1) if data1 else 0.0

            # If page 1 is grayscale / black & white, it is definitely a story page, not a cover
            if sat1 < 25.0:
                return False

            # If page 1 is color, check page 2 if present
            if len(img_names) > 1:
                p2_bytes = z.read(img_names[1])
                im2 = Image.open(io.BytesIO(p2_bytes))
                stat2 = im2.convert("HSV").split()[1]
                data2 = list(stat2.get_flattened_data()) if hasattr(stat2, "get_flattened_data") else list(stat2.getdata())
                sat2 = sum(data2) / len(data2) if data2 else 0.0

                # Strongest indicator: Page 1 is full-color (volume cover) and page 2 is B&W story page
                if sat1 >= 30.0 and sat2 < 20.0:
                    return True

            # If saturation is high, it's a color cover page
            if sat1 >= 40.0:
                return True

            # Fallback visual diff against cover_file if exists
            cover_file = find_volume_cover_file(covers_dir, vol_num)
            if cover_file and cover_file.exists():
                cov_im = Image.open(cover_file).convert("L").resize((32, 48))
                im1_sm = im1.convert("L").resize((32, 48))
                p1 = list(im1_sm.get_flattened_data()) if hasattr(im1_sm, "get_flattened_data") else list(im1_sm.getdata())
                p2 = list(cov_im.get_flattened_data()) if hasattr(cov_im, "get_flattened_data") else list(cov_im.getdata())
                if p1 and p2 and len(p1) == len(p2):
                    diff = sum(abs(a - b) for a, b in zip(p1, p2)) / len(p1)
                    if diff < 35.0:
                        return True
    except Exception:
        pass

    return False


def generate_volume_blank_page_bytes(
    width: int = 1200,
    height: int = 1800,
    compress_webp: bool = False,
) -> bytes:
    """
    Renders an authentic dark blank end-paper page (pure pitch black #000000).
    Used to ensure physical book 2-page spread parity and outside back cover alignment.
    """
    if not PIL_AVAILABLE:
        return b""
    img = Image.new("RGB", (width, height), color="#000000")
    buf = io.BytesIO()
    if compress_webp:
        img.save(buf, format="WEBP", quality=85)
    else:
        img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def scan_folder_for_bundleable_volumes(
    source_dir: str | Path,
    canon_dict: Optional[Dict[int, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Scans source_dir for CBZ files (strictly ignoring the 'covers' subfolder).
    Identifies chapter CBZ files, checks them against canon volume chapter ranges,
    and returns which volumes are ready to bundle.
    """
    src_path = Path(source_dir).resolve()
    if not src_path.exists() or not src_path.is_dir():
        return {
            "source_path": str(src_path),
            "total_chapters": 0,
            "chapter_map": {},
            "ready_volumes": [],
            "partial_volumes": [],
            "existing_volumes": {},
        }

    if canon_dict is None:
        canon_dict = load_canon_volumes_dict()

    # Find all CBZ files directly in source_dir or in subfolders EXCEPT 'covers'
    cbz_files: List[Path] = []
    for f in src_path.rglob("*.cbz"):
        if not is_covers_path(f) and f.is_file() and not f.name.startswith("."):
            cbz_files.append(f)

    # Distinguish Volume CBZs vs Chapter CBZs
    volume_cbzs: Dict[int, Path] = {}
    chapter_cbzs: Dict[int, Path] = {}

    for f in cbz_files:
        # Check if file is a volume archive (e.g. Volume 14 - Instinct.cbz or One Piece - v01 (c001-008).cbz)
        m_vol = re.match(r"^(?:Volume|Vol\.?)\s*(\d+)", f.name, re.IGNORECASE)
        if not m_vol:
            m_vol = re.search(r"(?:One\s*Piece.*?v|v(?:ol)?\.?\s*)(\d+)\s*(?:\((?:c|ch)?\d+-(?:c|ch)?\d+\))?", f.name, re.IGNORECASE)

        # Avoid false matching Chapter as volume
        if m_vol and not re.match(r"^Chapter\s+\d+", f.name, re.IGNORECASE):
            vol_num = int(m_vol.group(1))
            volume_cbzs[vol_num] = f
            continue

        # Check if file is a single chapter archive (e.g. Chapter 1 - Romance Dawn.cbz or c001.cbz)
        m_ch = re.search(r"(?:Chapter|c)\s*(\d+)", f.name, re.IGNORECASE)
        if m_ch:
            ch_num = int(m_ch.group(1))
            chapter_cbzs[ch_num] = f

    ready_volumes: List[Dict[str, Any]] = []
    partial_volumes: List[Dict[str, Any]] = []

    for v_num in sorted(canon_dict.keys()):
        v_meta = canon_dict[v_num]
        st = v_meta["ch_start"]
        en = v_meta["ch_end"]
        needed = set(range(st, en + 1))
        have = [c for c in sorted(needed) if c in chapter_cbzs]

        is_already_bundled = v_num in volume_cbzs and volume_cbzs[v_num].stat().st_size > 5000

        if len(have) == len(needed):
            ready_volumes.append({
                "volume": v_num,
                "title": v_meta["title"],
                "ch_start": st,
                "ch_end": en,
                "total_chapters": len(needed),
                "is_bundled": is_already_bundled,
                "bundled_file": volume_cbzs[v_num].name if is_already_bundled else None,
                "chapters": have,
            })
        elif len(have) > 0:
            missing = sorted(list(needed - set(have)))
            partial_volumes.append({
                "volume": v_num,
                "title": v_meta["title"],
                "ch_start": st,
                "ch_end": en,
                "have_count": len(have),
                "needed_count": len(needed),
                "missing": missing,
            })

    return {
        "source_path": str(src_path),
        "total_chapters": len(chapter_cbzs),
        "chapter_map": chapter_cbzs,
        "ready_volumes": ready_volumes,
        "partial_volumes": partial_volumes,
        "existing_volumes": volume_cbzs,
    }


def bundle_volume_from_chapters(
    vol_num: int,
    chapter_map: Dict[int, Path],
    output_dir: str | Path,
    canon_dict: Optional[Dict[int, Dict[str, Any]]] = None,
    covers_dir: Optional[str | Path] = None,
    include_cover: bool = True,
    include_back_cover: bool = True,
    compress_webp: bool = False,
    sync_catalog: bool = True,
    prefer_official_cover: bool = False,
    log_callback: Callable[[str], None] = print,
) -> Path:
    """
    Bundles the constituent chapter CBZ files for vol_num into a standardized volume CBZ:
      1. Front cover (smartly handled: keeps chapter cover or replaces with official Shueisha cover)
      2. Constituent chapter pages (page_0001 ... page_NNNN), optionally WebP-compressed
      3. Dark Viz description back cover (page_XXXX_back_cover) with spread parity
      4. Chapter Table of Contents (toc.json)
      5. ComicRack ComicInfo.xml metadata
    """
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    if canon_dict is None:
        canon_dict = load_canon_volumes_dict()

    v_meta = canon_dict.get(vol_num)
    if not v_meta:
        v_meta = get_volume_meta(vol_num)
        st = v_meta.get("chapterStart", max(1, (vol_num - 1) * 10 + 1))
        en = v_meta.get("chapterEnd", st + 9)
        v_meta = {
            "title": v_meta.get("title", f"Volume {vol_num}"),
            "ch_start": st,
            "ch_end": en,
            "summary": v_meta.get("summary", ""),
        }

    st = v_meta["ch_start"]
    en = v_meta["ch_end"]
    raw_title = v_meta.get("title", "").strip()
    archive_filename = format_volume_filename(vol_num, raw_title)
    archive_dest = out_path / archive_filename

    display_title = format_volume_display_title(vol_num, raw_title)
    compression_tag = " [WebP 65% Compressed]" if compress_webp else ""
    log_callback(f"Bundling {display_title} (Chapters {st} to {en}){compression_tag}...")

    # Locate covers folder & Viz metadata
    resolved_covers_dir = find_covers_dir([
        covers_dir,
        out_path,
        list(chapter_map.values())[0].parent if chapter_map else None,
    ])
    viz_catalog = load_viz_volumes_metadata(resolved_covers_dir)
    viz_meta = viz_catalog.get(vol_num, {})

    page_idx = 1
    total_pages_count = 0
    chapter_toc: List[Dict[str, Any]] = []
    last_page_w = 1200
    last_page_h = 1800

    with zipfile.ZipFile(archive_dest, "w", zipfile.ZIP_DEFLATED) as z_out:
        # Check if first chapter already includes a volume cover as its opening page
        first_ch_has_cover = False
        first_ch_path = chapter_map.get(st)
        if first_ch_path and first_ch_path.exists():
            first_ch_has_cover = first_chapter_has_volume_cover(first_ch_path, vol_num, resolved_covers_dir)

        # Determine front cover inclusion and whether to skip first chapter's page 1
        embed_external_cover = False
        skip_first_ch_page1 = False

        if include_cover:
            if prefer_official_cover:
                # User preference: Use high-res official Shueisha cover
                embed_external_cover = True
                if first_ch_has_cover:
                    skip_first_ch_page1 = True
            else:
                # Default preference: If first chapter already has cover, keep it and skip external cover
                # If first chapter lacks a cover, embed official cover
                if not first_ch_has_cover:
                    embed_external_cover = True

        # 1. Official Front Cover (page_0000_cover)
        if embed_external_cover:
            cover_file = find_volume_cover_file(resolved_covers_dir, vol_num)
            if cover_file:
                c_ext = cover_file.suffix.lower() or ".jpg"
                with open(cover_file, "rb") as cf:
                    cover_data = cf.read()
                if compress_webp and PIL_AVAILABLE:
                    try:
                        im = Image.open(io.BytesIO(cover_data))
                        last_page_w, last_page_h = im.size
                        if im.mode not in ("RGB", "L"):
                            im = im.convert("RGB")
                        webp_buf = io.BytesIO()
                        im.save(webp_buf, format="WEBP", quality=85, method=4)
                        cover_data = webp_buf.getvalue()
                        c_ext = ".webp"
                    except Exception:
                        pass
                arc_cover_name = f"page_0000_cover{c_ext}"
                z_out.writestr(arc_cover_name, cover_data)
                total_pages_count += 1
                if skip_first_ch_page1:
                    log_callback(f"   [Front Cover] Embedded official Shueisha cover {cover_file.name} (replacing Chapter {st} cover page 1).")
                else:
                    log_callback(f"   [Front Cover] Embedded {cover_file.name} as {arc_cover_name}")
            else:
                log_callback(f"   [Notice] Front cover not found in covers directory for Volume {vol_num}.")
        elif first_ch_has_cover:
            log_callback(f"   [Front Cover] Chapter {st} already includes front cover as page 1 (retained, external cover skipped).")
        else:
            log_callback(f"   [Front Cover] Front cover skipped as requested.")

        # 2. Constituent Chapter Pages
        for ch in range(st, en + 1):
            ch_cbz_path = chapter_map.get(ch)
            if not ch_cbz_path or not ch_cbz_path.exists():
                raise FileNotFoundError(f"Missing Chapter {ch} CBZ archive needed for Volume {vol_num}.")

            ch_title = f"Chapter {ch}"
            try:
                ch_info = read_comic_info_from_cbz(str(ch_cbz_path))
                if ch_info and ch_info.get("Title"):
                    ch_title = format_chapter_display_title(ch, ch_info["Title"])
            except Exception:
                pass

            ch_start_page = page_idx

            with zipfile.ZipFile(ch_cbz_path, "r") as z_in:
                img_names = [
                    n for n in z_in.namelist()
                    if Path(n).suffix.lower() in VALID_IMAGE_EXTS
                    and not n.startswith("__MACOSX")
                    and not is_covers_path(n)
                ]
                img_names.sort(key=natural_sort_key)

                # Skip chapter's first page if it is an existing cover and official cover was embedded
                if ch == st and skip_first_ch_page1 and len(img_names) > 0:
                    img_names = img_names[1:]

                for n in img_names:
                    data = z_in.read(n)
                    ext = Path(n).suffix.lower() or ".jpg"

                    if PIL_AVAILABLE:
                        try:
                            im = Image.open(io.BytesIO(data))
                            last_page_w, last_page_h = im.size
                            if compress_webp:
                                if im.mode not in ("RGB", "L"):
                                    im = im.convert("RGB")
                                webp_buf = io.BytesIO()
                                im.save(webp_buf, format="WEBP", quality=84, method=4)
                                data = webp_buf.getvalue()
                                ext = ".webp"
                        except Exception:
                            pass

                    arc_name = f"page_{page_idx:04d}{ext}"
                    z_out.writestr(arc_name, data)
                    page_idx += 1
                    total_pages_count += 1

            ch_end_page = page_idx - 1
            chapter_toc.append({
                "chapterNumber": ch,
                "title": ch_title,
                "startPage": ch_start_page,
                "endPage": ch_end_page,
                "pageCount": ch_end_page - ch_start_page + 1,
            })
            log_callback(f"   Integrated Chapter {ch} ({len(img_names)} pages, p.{ch_start_page}-p.{ch_end_page})")

        # 3. Dark Viz Media Back Cover with Physical Book Spread Parity
        if include_back_cover:
            # Physical manga bookbinding rule:
            # If the compiled volume has an EVEN number of pages, add 2 pages: 1 blank endpaper + 1 back cover.
            # If the compiled volume has an ODD (uneven) number of pages, add 1 page: the back cover.
            # This guarantees the volume ALWAYS has an EVEN total page count and the back cover is on the outside.
            if total_pages_count % 2 == 0:
                log_callback(f"   [Parity] Volume pages so far is EVEN ({total_pages_count}). Adding 1 blank endpaper + 1 back cover.")
                blank_bytes = generate_volume_blank_page_bytes(
                    width=last_page_w,
                    height=last_page_h,
                    compress_webp=compress_webp,
                )
                if blank_bytes:
                    blank_ext = ".webp" if compress_webp else ".jpg"
                    blank_name = f"page_{page_idx:04d}_blank{blank_ext}"
                    z_out.writestr(blank_name, blank_bytes)
                    page_idx += 1
                    total_pages_count += 1
            else:
                log_callback(f"   [Parity] Volume pages so far is ODD ({total_pages_count}). Adding 1 back cover directly.")

            real_back_file = find_volume_back_cover_file(resolved_covers_dir, vol_num)
            back_cover_embedded = False

            if real_back_file:
                try:
                    with open(real_back_file, "rb") as rbf:
                        real_bc_data = rbf.read()
                    real_bc_ext = real_back_file.suffix.lower() or ".jpg"
                    if compress_webp and PIL_AVAILABLE:
                        try:
                            im = Image.open(io.BytesIO(real_bc_data))
                            if im.mode not in ("RGB", "L"):
                                im = im.convert("RGB")
                            w_buf = io.BytesIO()
                            im.save(w_buf, format="WEBP", quality=85, method=4)
                            real_bc_data = w_buf.getvalue()
                            real_bc_ext = ".webp"
                        except Exception:
                            pass
                    back_cover_name = f"page_{page_idx:04d}_back_cover{real_bc_ext}"
                    z_out.writestr(back_cover_name, real_bc_data)
                    page_idx += 1
                    total_pages_count += 1
                    back_cover_embedded = True
                    log_callback(f"   [Back Cover] Embedded authentic Shueisha back cover {real_back_file.name} ({back_cover_name})")
                except Exception as e:
                    log_callback(f"   [Notice] Could not load authentic back cover: {e}, falling back to generated.")

            if not back_cover_embedded:
                try:
                    back_cover_bytes = generate_volume_back_cover_bytes(
                        vol_num,
                        viz_meta,
                        width=last_page_w,
                        height=last_page_h,
                    )
                    back_cover_ext = ".jpg"
                    if compress_webp and PIL_AVAILABLE:
                        try:
                            im = Image.open(io.BytesIO(back_cover_bytes))
                            webp_buf = io.BytesIO()
                            im.save(webp_buf, format="WEBP", quality=85, method=4)
                            back_cover_bytes = webp_buf.getvalue()
                            back_cover_ext = ".webp"
                        except Exception:
                            pass
                    back_cover_name = f"page_{page_idx:04d}_back_cover{back_cover_ext}"
                    z_out.writestr(back_cover_name, back_cover_bytes)
                    page_idx += 1
                    total_pages_count += 1
                    log_callback(f"   [Back Cover] Generated & embedded Viz description back cover ({back_cover_name})")
                except Exception as e:
                    log_callback(f"   [Notice] Could not render back cover: {e}")

        # 4. Injected Table of Contents (toc.json)
        toc_payload = {
            "volumeNumber": vol_num,
            "title": display_title,
            "chapters": chapter_toc,
        }
        z_out.writestr("toc.json", json.dumps(toc_payload, indent=2))

        # 5. Injected ComicRack ComicInfo.xml
        summary_text = (
            viz_meta.get("description")
            or v_meta.get("summary")
            or f"One Piece Volume {vol_num} (Chapters {st}-{en})."
        )
        comic_info_xml = build_comic_info_xml(
            series="One Piece",
            volume=vol_num,
            number=vol_num,
            ch_start=st,
            ch_end=en,
            count=total_pages_count,
            title=display_title,
            summary=summary_text,
            language_iso="en",
        )
        z_out.writestr("ComicInfo.xml", comic_info_xml.encode("utf-8"))

    file_size_kb = archive_dest.stat().st_size // 1024
    log_callback(f"Successfully bundled: {archive_dest.name} ({file_size_kb} KB, {total_pages_count} pages)")

    if sync_catalog:
        index_dest = out_path / "index.json"
        log_callback("Synchronizing catalog index.json...")
        scan_and_index_volumes(out_path, index_dest)
        log_callback("Catalog updated successfully!")

    return archive_dest


def bundle_all_ready_volumes(
    source_dir: str | Path,
    output_dir: str | Path,
    covers_dir: Optional[str | Path] = None,
    include_cover: bool = True,
    include_back_cover: bool = True,
    compress_webp: bool = False,
    skip_already_bundled: bool = True,
    sync_catalog: bool = True,
    prefer_official_cover: bool = False,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    log_callback: Callable[[str], None] = print,
    cancel_flag: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """
    Auto-detects all ready volumes in source_dir and bundles them sequentially.
    """
    scan_res = scan_folder_for_bundleable_volumes(source_dir)
    ready = scan_res["ready_volumes"]
    chapter_map = scan_res["chapter_map"]

    if not ready:
        log_callback(f"No volumes with complete chapter sets found in {source_dir}.")
        return {"bundled": 0, "skipped": 0, "failed": []}

    to_process = [v for v in ready if not (skip_already_bundled and v["is_bundled"])]
    skipped_count = len(ready) - len(to_process)

    log_callback(f"=== Starting Volume Bundler ===")
    log_callback(f"Found {len(ready)} ready volume(s) ({skipped_count} already bundled, {len(to_process)} to bundle).\n")

    bundled_count = 0
    failed = []

    for idx, v_info in enumerate(to_process, 1):
        if cancel_flag and cancel_flag():
            log_callback("\n[Cancelled] Bundling was cancelled by user.")
            break

        v_num = v_info["volume"]
        status = f"[{idx}/{len(to_process)}] Bundling Volume {v_num} ({v_info['title']})..."
        log_callback(status)
        if progress_callback:
            progress_callback(idx / len(to_process), status)

        try:
            bundle_volume_from_chapters(
                vol_num=v_num,
                chapter_map=chapter_map,
                output_dir=output_dir,
                covers_dir=covers_dir,
                include_cover=include_cover,
                include_back_cover=include_back_cover,
                compress_webp=compress_webp,
                sync_catalog=False,  # Defer sync until the end
                prefer_official_cover=prefer_official_cover,
                log_callback=lambda msg: log_callback(f"   {msg}"),
            )
            bundled_count += 1
        except Exception as e:
            log_callback(f"   [Error] Failed to bundle Volume {v_num}: {e}")
            failed.append((v_num, str(e)))

    if sync_catalog and bundled_count > 0:
        out_path = Path(output_dir).resolve()
        log_callback("Synchronizing master catalog index.json...")
        scan_and_index_volumes(out_path, out_path / "index.json")
        log_callback("Showcase catalog updated successfully!")

    return {
        "bundled": bundled_count,
        "skipped": skipped_count,
        "failed": failed,
    }


def main():
    parser = argparse.ArgumentParser(description="One Piece Canon Volume Bundler & Detector")
    parser.add_argument("-s", "--source", type=str, default="../frontend/public/comics", help="Source folder with chapter CBZs")
    parser.add_argument("-o", "--out", type=str, default="../frontend/public/comics", help="Output directory for volume CBZs")
    parser.add_argument("--covers-dir", type=str, default=None, help="Directory containing volume cover images and viz_volumes_metadata.json")
    parser.add_argument("--no-cover", action="store_true", help="Do not include front cover image")
    parser.add_argument("--no-back-cover", action="store_true", help="Do not generate/include Viz back cover")
    parser.add_argument("--prefer-official-cover", action="store_true", help="Replace chapter 1 cover with official Shueisha cover (instead of keeping chapter cover)")
    parser.add_argument("--webp", action="store_true", help="Compress images to WebP (saves ~65%% file size, fits 100+ volumes in free 10GB R2 tier)")
    parser.add_argument("--scan", action="store_true", help="Scan and list ready/partial volumes")
    parser.add_argument("--volume", type=int, help="Bundle a specific volume number")
    parser.add_argument("--all", action="store_true", help="Bundle all ready volumes")
    parser.add_argument("--force", action="store_true", help="Re-bundle even if volume already exists")
    parser.add_argument("--no-sync", action="store_true", help="Do not sync index.json")

    args = parser.parse_args()

    if args.scan:
        res = scan_folder_for_bundleable_volumes(args.source)
        print(f"\nScanned: {res['source_path']}")
        print(f"Total Chapter CBZs Found: {res['total_chapters']} (subfolder 'covers' ignored)\n")

        print("=== Ready to Bundle Volumes ===")
        if not res["ready_volumes"]:
            print("  (None found)")
        for v in res["ready_volumes"]:
            tag = "[ALREADY BUNDLED]" if v["is_bundled"] else "[READY!]"
            print(f"  Vol {v['volume']:2d} (Ch {v['ch_start']:3d}-{v['ch_end']:3d}): {v['total_chapters']} chapters {tag} - '{v['title']}'")

        if res["partial_volumes"]:
            print("\n=== Partial Volumes (Need more chapters) ===")
            for v in res["partial_volumes"]:
                print(f"  Vol {v['volume']:2d} (Ch {v['ch_start']:3d}-{v['ch_end']:3d}): {v['have_count']}/{v['needed_count']} chapters - '{v['title']}'")
        sys.exit(0)

    if args.volume:
        scan_res = scan_folder_for_bundleable_volumes(args.source)
        bundle_volume_from_chapters(
            vol_num=args.volume,
            chapter_map=scan_res["chapter_map"],
            output_dir=args.out,
            covers_dir=args.covers_dir,
            include_cover=not args.no_cover,
            include_back_cover=not args.no_back_cover,
            compress_webp=args.webp,
            sync_catalog=not args.no_sync,
            prefer_official_cover=args.prefer_official_cover,
        )
        sys.exit(0)

    if args.all:
        bundle_all_ready_volumes(
            source_dir=args.source,
            output_dir=args.out,
            covers_dir=args.covers_dir,
            include_cover=not args.no_cover,
            include_back_cover=not args.no_back_cover,
            compress_webp=args.webp,
            skip_already_bundled=not args.force,
            sync_catalog=not args.no_sync,
            prefer_official_cover=args.prefer_official_cover,
        )
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
