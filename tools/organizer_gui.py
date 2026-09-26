"""
organizer_gui.py - CustomTkinter GUI and CLI for Manga Volume Bundling and ComicInfo.xml Injection.
Packages loose chapter folders or chapter CBZs into canon One Piece volume CBZs,
embeds standard ComicRack ComicInfo.xml metadata, and synchronizes the frontend catalog index.json.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import threading
import time
import zipfile
from pathlib import Path
from typing import List, Optional

try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
    CTK_AVAILABLE = True
except Exception:
    CTK_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from tools.comic_info import (
        build_comic_info_xml,
        write_comic_info_to_cbz,
        format_volume_filename,
        format_volume_display_title,
        format_chapter_filename,
        format_chapter_display_title,
        clean_volume_sub_title,
        clean_chapter_sub_title,
    )
    from tools.catalog_indexer import get_volume_meta, scan_and_index_volumes, CANON_VOLUMES_DATA
    from tools.mangadex_downloader import download_mangadex_chapter, download_mangadex_batch, parse_chapter_range
except ImportError:
    from comic_info import (
        build_comic_info_xml,
        write_comic_info_to_cbz,
        format_volume_filename,
        format_volume_display_title,
        format_chapter_filename,
        format_chapter_display_title,
        clean_volume_sub_title,
        clean_chapter_sub_title,
    )
    from catalog_indexer import get_volume_meta, scan_and_index_volumes, CANON_VOLUMES_DATA
    try:
        from mangadex_downloader import download_mangadex_chapter, download_mangadex_batch, parse_chapter_range
    except ImportError:
        download_mangadex_chapter = None
        download_mangadex_batch = None
        parse_chapter_range = None

try:
    from tools.weebcentral_downloader import download_weebcentral_chapter, download_weebcentral_batch, fetch_weebcentral_chapter_map
except ImportError:
    try:
        from weebcentral_downloader import download_weebcentral_chapter, download_weebcentral_batch, fetch_weebcentral_chapter_map
    except ImportError:
        download_weebcentral_chapter = None
        download_weebcentral_batch = None
        fetch_weebcentral_chapter_map = None

try:
    from tools.volume_bundler import (
        scan_folder_for_bundleable_volumes,
        bundle_volume_from_chapters,
        bundle_all_ready_volumes,
        is_covers_path,
        find_covers_dir,
        find_volume_cover_file,
        find_volume_back_cover_file,
        load_viz_volumes_metadata,
        generate_volume_back_cover_bytes,
    )
except ImportError:
    try:
        from volume_bundler import (
            scan_folder_for_bundleable_volumes,
            bundle_volume_from_chapters,
            bundle_all_ready_volumes,
            is_covers_path,
            find_covers_dir,
            find_volume_cover_file,
            find_volume_back_cover_file,
            load_viz_volumes_metadata,
            generate_volume_back_cover_bytes,
        )
    except ImportError:
        scan_folder_for_bundleable_volumes = None
        bundle_volume_from_chapters = None
        bundle_all_ready_volumes = None
        find_covers_dir = None
        find_volume_cover_file = None
        find_volume_back_cover_file = None
        load_viz_volumes_metadata = None
        generate_volume_back_cover_bytes = None
        def is_covers_path(p):
            return any(part.lower() == "covers" for part in Path(p).parts)

try:
    from tools.r2_sync import (
        load_r2_config,
        save_r2_config,
        test_r2_connection,
        configure_r2_cors,
        sync_comics_folder_to_r2,
        upload_file_to_r2,
        StorageLimitExceededError,
    )
except ImportError:
    try:
        from r2_sync import (
            load_r2_config,
            save_r2_config,
            test_r2_connection,
            configure_r2_cors,
            sync_comics_folder_to_r2,
            upload_file_to_r2,
            StorageLimitExceededError,
        )
    except ImportError:
        load_r2_config = None
        save_r2_config = None
        test_r2_connection = None
        configure_r2_cors = None
        sync_comics_folder_to_r2 = None
        upload_file_to_r2 = None
        StorageLimitExceededError = Exception

try:
    from tools.sync_r2_catalog import sync_catalog
except ImportError:
    try:
        from sync_r2_catalog import sync_catalog
    except ImportError:
        sync_catalog = None



def natural_sort_key(s: str):
    """Sort strings with embedded numbers naturally (e.g., page 2 before page 10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", str(s))]


def create_dummy_sample_volume(
    output_dir: str | Path,
    vol_num: int = 1,
    page_count: int = 12,
    log_callback=print,
) -> str:
    """
    Creates a valid, high-aesthetic sample CBZ archive with dummy manga pages
    and valid ComicInfo.xml for immediate testing and showcase display.
    """
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = get_volume_meta(vol_num)
    ch_start = meta["chapterStart"]
    ch_end = meta["chapterEnd"]
    raw_title = meta.get("title", "").strip()
    archive_name = format_volume_filename(vol_num, raw_title)
    archive_path = out_dir / archive_name

    log_callback(f"Generating aesthetic sample volume: {archive_name}...")


    # Generate sample manga pages in memory
    pages_data = []
    width, height = 800, 1200
    theme_color = meta.get("spineColor", "#38bdf8")

    for p in range(1, page_count + 1):
        if PIL_AVAILABLE:
            img = Image.new("RGB", (width, height), color="#12131a")
            draw = ImageDraw.Draw(img)

            # Elegant frame
            draw.rectangle([20, 20, width - 20, height - 20], outline=theme_color, width=3)
            draw.rectangle([30, 30, width - 30, height - 30], outline="#2a2e3f", width=1)

            # Header bar
            draw.rectangle([40, 40, width - 40, 120], fill="#1e2235")
            
            # Content
            if p == 1:
                # Cover Page
                draw.rectangle([60, 160, width - 60, height - 160], fill="#181a26", outline=theme_color, width=2)
                # Text labels
                draw.text((width // 2 - 100, 70), "ONE PIECE", fill="#ffffff")
                draw.text((width // 2 - 80, 220), f"VOLUME {vol_num}", fill=theme_color)
                draw.text((width // 2 - 120, 300), meta["title"].upper(), fill="#ffffff")
                draw.text((width // 2 - 90, 360), f"Chapters {ch_start} - {ch_end}", fill="#94a3b8")
                draw.text((width // 2 - 70, 500), f"Arc: {meta['arcName']}", fill="#cbd5e1")
                draw.text((width // 2 - 80, height - 220), "EIICHIRO ODA", fill="#e2e8f0")
                draw.text((width // 2 - 70, height - 190), "SHUEISHA / JUMP COMICS", fill="#64748b")
            else:
                # Manga story page mockup
                draw.text((width // 2 - 120, 70), f"ONE PIECE • VOL {vol_num}", fill="#94a3b8")
                draw.text((width - 120, 70), f"PAGE {p:02d}", fill=theme_color)
                
                # Mock manga panels
                # Panel 1
                draw.rectangle([60, 160, width - 60, 480], outline="#475569", fill="#1a1d2e", width=2)
                draw.text((80, 180), f"Chapter {ch_start} — {meta['title']}", fill="#f8fafc")
                draw.text((80, 220), "Luffy: I'm gonna be King of the Pirates!", fill="#38bdf8")
                
                # Panel 2 (Left)
                draw.rectangle([60, 510, width // 2 - 10, 840], outline="#475569", fill="#161826", width=2)
                draw.text((80, 530), "Zoro: If you get in the way of my dream...", fill="#34d399")
                
                # Panel 3 (Right)
                draw.rectangle([width // 2 + 10, 510, width - 60, 840], outline="#475569", fill="#161826", width=2)
                draw.text((width // 2 + 30, 530), "Nami: Keep your hands off my treasure!", fill="#fbbf24")
                
                # Panel 4 (Bottom spread)
                draw.rectangle([60, 870, width - 60, height - 80], outline="#475569", fill="#1e2235", width=2)
                draw.text((80, 890), f"Manga showcase demonstration page {p} of {page_count}", fill="#94a3b8")
                draw.text((80, 930), "Reading in authentic Right-to-Left (RTL) mode.", fill="#cbd5e1")
                draw.text((width // 2 - 30, height - 60), f"- {p} -", fill="#64748b")

            import io
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            pages_data.append((f"page_{p:03d}.jpg", buf.getvalue()))
        else:
            # Simple text dummy if PIL is not available
            dummy_content = f"Page {p} of Volume {vol_num} - One Piece".encode("utf-8")
            pages_data.append((f"page_{p:03d}.txt", dummy_content))

    # ComicInfo.xml metadata
    comic_info_xml = build_comic_info_xml(
        series="One Piece",
        volume=vol_num,
        number=vol_num,
        ch_start=ch_start,
        ch_end=ch_end,
        count=page_count,
        title=meta["title"],
        summary=meta["summary"],
    )

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ComicInfo.xml", comic_info_xml.encode("utf-8"))
        for fname, data in pages_data:
            z.writestr(fname, data)

    log_callback(f"Successfully generated sample CBZ archive: {archive_path}")
    return str(archive_path)


def pack_folder_to_volume_cbz(
    source_folder: str | Path,
    output_dir: str | Path,
    vol_num: int,
    ch_start: Optional[int] = None,
    ch_end: Optional[int] = None,
    log_callback=print,
) -> str:
    """
    Packs images from source_folder into a standardized volume CBZ archive:
    One Piece - v[Vol] (c[Start]-[End]).cbz
    with injected ComicInfo.xml.
    """
    src_path = Path(source_folder).resolve()
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    meta = get_volume_meta(vol_num)
    start_ch = ch_start if ch_start is not None else meta["chapterStart"]
    end_ch = ch_end if ch_end is not None else meta["chapterEnd"]

    # 1. First check if chapter CBZ archives are available in source
    if scan_folder_for_bundleable_volumes is not None and bundle_volume_from_chapters is not None:
        scan_res = scan_folder_for_bundleable_volumes(src_path)
        ch_map = scan_res.get("chapter_map", {})
        needed_chs = set(range(start_ch, end_ch + 1))
        have_chs = [c for c in needed_chs if c in ch_map]
        if len(have_chs) == len(needed_chs):
            log_callback(f"Detected complete chapter CBZs ({start_ch}-{end_ch}) in {src_path}. Bundling from chapters...")
            archive = bundle_volume_from_chapters(
                vol_num=vol_num,
                chapter_map=ch_map,
                output_dir=out_path,
                sync_catalog=False,
                log_callback=log_callback,
            )
            return str(archive)

    # 2. Fallback: Pack loose image files in source_folder (STRICTLY ignoring 'covers' subfolder!)
    raw_title = meta.get("title", "").strip()
    archive_filename = format_volume_filename(vol_num, raw_title)
    archive_dest = out_path / archive_filename


    log_callback(f"Scanning source directory for loose images: {src_path} (excluding 'covers' subfolder)...")
    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
    
    # Collect all image files recursively, strictly excluding 'covers'
    image_files = [
        f for f in src_path.rglob("*")
        if f.is_file() and f.suffix.lower() in valid_exts and not f.name.startswith(".") and not is_covers_path(f)
    ]
    image_files.sort(key=lambda p: natural_sort_key(p.name))

    page_count = len(image_files)
    if page_count == 0:
        raise FileNotFoundError(
            f"No loose image pages or complete chapter CBZs found in {src_path} for Volume {vol_num} (Chapters {start_ch}-{end_ch}). Note: 'covers' subfolder is intentionally excluded."
        )

    log_callback(f"Found {page_count} loose image pages in source (covers excluded).")

    # Locate covers & Viz metadata
    resolved_covers = find_covers_dir([src_path, out_path]) if find_covers_dir else None
    cover_file = find_volume_cover_file(resolved_covers, vol_num) if find_volume_cover_file else None
    viz_meta = load_viz_volumes_metadata(resolved_covers).get(vol_num, {}) if load_viz_volumes_metadata else {}

    display_title = format_volume_display_title(vol_num, raw_title)
    total_pages = 0

    log_callback(f"Packing into archive: {archive_dest.name}...")
    with zipfile.ZipFile(archive_dest, "w", zipfile.ZIP_DEFLATED) as z:
        # Front cover
        if cover_file:
            c_ext = cover_file.suffix.lower() or ".jpg"
            z.write(cover_file, arcname=f"page_0000_cover{c_ext}")
            total_pages += 1
            log_callback(f"   [Front Cover] Embedded {cover_file.name} as page_0000_cover{c_ext}")

        # Loose story pages
        page_idx = 1
        loose_imgs_to_pack = list(image_files)
        if cover_file and loose_imgs_to_pack and ("cover" in loose_imgs_to_pack[0].name.lower() or "page_0000" in loose_imgs_to_pack[0].name.lower()):
            log_callback(f"   [Notice] Skipping loose cover page {loose_imgs_to_pack[0].name} to prevent duplication with official cover.")
            loose_imgs_to_pack = loose_imgs_to_pack[1:]

        for img_path in loose_imgs_to_pack:
            arc_name = f"page_{page_idx:04d}{img_path.suffix.lower()}"
            z.write(img_path, arcname=arc_name)
            page_idx += 1
            total_pages += 1

        # Back cover
        real_back_file = find_volume_back_cover_file(resolved_covers, vol_num) if find_volume_back_cover_file else None
        if real_back_file:
            bc_ext = real_back_file.suffix.lower() or ".jpg"
            z.write(real_back_file, arcname=f"page_{page_idx:04d}_back_cover{bc_ext}")
            total_pages += 1
            log_callback(f"   [Back Cover] Embedded authentic Shueisha back cover {real_back_file.name}")
        elif generate_volume_back_cover_bytes:
            try:
                bc_bytes = generate_volume_back_cover_bytes(vol_num, viz_meta)
                bc_name = f"page_{page_idx:04d}_back_cover.jpg"
                z.writestr(bc_name, bc_bytes)
                total_pages += 1
                log_callback(f"   [Back Cover] Generated & embedded Viz description back cover ({bc_name})")
            except Exception as e:
                log_callback(f"   [Notice] Could not render back cover: {e}")

        # ComicInfo.xml
        summary_text = (
            viz_meta.get("description")
            or meta.get("summary")
            or f"One Piece Volume {vol_num} (Chapters {start_ch}-{end_ch})."
        )
        comic_info_xml = build_comic_info_xml(
            series="One Piece",
            volume=vol_num,
            number=vol_num,
            ch_start=start_ch,
            ch_end=end_ch,
            count=total_pages,
            title=display_title,
            summary=summary_text,
            language_iso="en",
        )
        z.writestr("ComicInfo.xml", comic_info_xml.encode("utf-8"))

    log_callback(f"Volume {vol_num} CBZ created successfully! ({archive_dest}, {total_pages} pages)")

    return str(archive_dest)


# ============================================================================
# CUSTOMTKINTER DESKTOP GUI
# ============================================================================

class MangaOrganizerApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("One Piece Manga Organizer & Packager — MD3 Edition")
        self.root.geometry("860x730")
        self.root.minsize(780, 600)

        # Style configuration
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Paths
        base_dir = Path(__file__).resolve().parent.parent
        self.default_output_dir = str(base_dir / "frontend" / "public" / "comics")
        self.output_index_path = str(base_dir / "frontend" / "public" / "comics" / "index.json")
        self.cancel_download = False

        self._build_ui()

    def _build_ui(self):
        # Header banner
        header_frame = ctk.CTkFrame(self.root, corner_radius=12, fg_color="#181a26")
        header_frame.pack(fill="x", padx=16, pady=(16, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text="One Piece Manga Volume Organizer",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#a8c7fa",
        )
        title_label.pack(anchor="w", padx=16, pady=(12, 2))

        sub_label = ctk.CTkLabel(
            header_frame,
            text="Canon Volume Bundler • ComicRack ComicInfo.xml Ingestion • Catalog Indexer",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        )
        sub_label.pack(anchor="w", padx=16, pady=(0, 12))

        # Main controls container
        content_frame = ctk.CTkFrame(self.root, corner_radius=12)
        content_frame.pack(fill="x", padx=16, pady=8)

        # 1. Source Folder Picker
        src_label = ctk.CTkLabel(content_frame, text="Source Chapter/Images Folder:", font=ctk.CTkFont(size=13, weight="bold"))
        src_label.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))

        self.src_entry = ctk.CTkEntry(content_frame, placeholder_text="Select folder with loose images or chapter files...", width=520)
        self.src_entry.insert(0, self.default_output_dir)
        self.src_entry.grid(row=1, column=0, sticky="ew", padx=16, pady=4)
        self.src_entry.bind("<KeyRelease>", lambda e: self._scan_and_update_ready_volumes())

        browse_src_btn = ctk.CTkButton(content_frame, text="Browse...", width=110, command=self._browse_source)
        browse_src_btn.grid(row=1, column=1, padx=(0, 16), pady=4)

        # 2. Output Folder Picker
        out_label = ctk.CTkLabel(content_frame, text="Output Directory (frontend/public/comics):", font=ctk.CTkFont(size=13, weight="bold"))
        out_label.grid(row=2, column=0, sticky="w", padx=16, pady=(10, 2))

        self.out_entry = ctk.CTkEntry(content_frame, width=520)
        self.out_entry.insert(0, self.default_output_dir)
        self.out_entry.grid(row=3, column=0, sticky="ew", padx=16, pady=4)

        browse_out_btn = ctk.CTkButton(content_frame, text="Browse...", width=110, command=self._browse_output)
        browse_out_btn.grid(row=3, column=1, padx=(0, 16), pady=4)

        # 3. Auto-Detected Volume Bundler (From Chapter CBZs)
        bundler_frame = ctk.CTkFrame(content_frame, fg_color="#181d2e", corner_radius=10, border_width=1, border_color="#2b3350")
        bundler_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 12))

        # Status Line + Rescan button
        header_row = ctk.CTkFrame(bundler_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=12, pady=(10, 4))

        self.bundler_status_lbl = ctk.CTkLabel(
            header_row,
            text="Scanning folder for chapter CBZs...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8",
            justify="left",
        )
        self.bundler_status_lbl.pack(side="left", anchor="w")

        rescan_btn = ctk.CTkButton(
            header_row,
            text="🔄 Re-Scan",
            width=80,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=12),
            command=self._scan_and_update_ready_volumes,
        )
        rescan_btn.pack(side="right")

        # Action Buttons, Checkbox & Volume Dropdown
        action_row = ctk.CTkFrame(bundler_frame, fg_color="transparent")
        action_row.pack(fill="x", padx=12, pady=(4, 6))

        self.bundle_all_btn = ctk.CTkButton(
            action_row,
            text="📦 Bundle All Ready Volumes",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            width=200,
            command=self._start_bundle_all_thread,
        )
        self.bundle_all_btn.pack(side="left", padx=(0, 8))

        # WebP Compression Checkbox
        self.webp_var = ctk.BooleanVar(value=True)
        self.webp_check = ctk.CTkCheckBox(
            action_row,
            text="🗜️ WebP (Save 65%)",
            variable=self.webp_var,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8",
            width=140,
        )
        self.webp_check.pack(side="left", padx=(0, 8))

        # Bundle & Push to R2 Button
        self.bundle_push_r2_btn = ctk.CTkButton(
            action_row,
            text="🚀 Bundle & Push to R2",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#ea580c",
            hover_color="#c2410c",
            width=160,
            command=self._start_bundle_and_push_r2_thread,
        )
        self.bundle_push_r2_btn.pack(side="left", padx=(0, 8))

        # Check New Chapters Button
        self.check_new_ch_btn = ctk.CTkButton(
            action_row,
            text="🔔 Check New Chs",
            font=ctk.CTkFont(weight="bold", size=11),
            fg_color="#4f46e5",
            hover_color="#4338ca",
            width=135,
            command=self._check_for_new_chapters,
        )
        self.check_new_ch_btn.pack(side="left", padx=(0, 8))

        # Secondary Row for Single Volume selection
        action_row_2 = ctk.CTkFrame(bundler_frame, fg_color="transparent")
        action_row_2.pack(fill="x", padx=12, pady=(0, 8))

        sel_lbl = ctk.CTkLabel(action_row_2, text="Or Select Volume:", font=ctk.CTkFont(size=12, weight="bold"))
        sel_lbl.pack(side="left", padx=(0, 6))

        self.ready_vol_menu = ctk.CTkOptionMenu(
            action_row_2,
            values=["(Scanning...)"],
            width=260,
            fg_color="#1e2235",
            button_color="#2d3246",
        )
        self.ready_vol_menu.pack(side="left", padx=(0, 8))

        self.bundle_selected_btn = ctk.CTkButton(
            action_row_2,
            text="📦 Bundle Selected",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            width=140,
            command=self._start_bundle_selected_thread,
        )
        self.bundle_selected_btn.pack(side="left", padx=(0, 10))

        # Cover Option Toggle (OFF = Keep Chapter Cover if present; ON = Replace with official Shueisha cover)
        self.shueisha_cover_var = ctk.BooleanVar(value=False)
        self.shueisha_cover_check = ctk.CTkCheckBox(
            action_row_2,
            text="🎨 Use Shueisha Cover (Replaces Ch 1 Cover)",
            variable=self.shueisha_cover_var,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f59e0b",
            width=280,
        )
        self.shueisha_cover_check.pack(side="left")

        # Third Row for Partial Volumes (1-Click Missing Chapters Download)
        action_row_3 = ctk.CTkFrame(bundler_frame, fg_color="transparent")
        action_row_3.pack(fill="x", padx=12, pady=(0, 8))

        partial_lbl = ctk.CTkLabel(action_row_3, text="Partial Volumes:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f59e0b")
        partial_lbl.pack(side="left", padx=(0, 6))

        self.partial_vol_menu = ctk.CTkOptionMenu(
            action_row_3,
            values=["(Scanning partials...)"],
            width=260,
            fg_color="#1e2235",
            button_color="#2d3246",
        )
        self.partial_vol_menu.pack(side="left", padx=(0, 8))

        self.download_missing_btn = ctk.CTkButton(
            action_row_3,
            text="⚡ Download Missing",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#d97706",
            hover_color="#b45309",
            width=150,
            command=self._start_download_missing_thread,
        )
        self.download_missing_btn.pack(side="left")


        # 4. MangaPlus URL Downloader & Language Selector
        mp_container = ctk.CTkFrame(content_frame, fg_color="transparent")
        mp_container.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 4))

        mp_label = ctk.CTkLabel(mp_container, text="Or Download Chapter Directly from MangaPlus:", font=ctk.CTkFont(size=13, weight="bold"))
        mp_label.pack(side="left", anchor="w")

        lang_label = ctk.CTkLabel(mp_container, text="Target Language:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#a8c7fa")
        lang_label.pack(side="right", padx=(0, 4))

        mp_input_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        mp_input_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 10))

        self.mp_entry = ctk.CTkEntry(mp_input_frame, placeholder_text="e.g. https://mangaplus.shueisha.co.jp/viewer/7002654", width=420)
        self.mp_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.lang_menu = ctk.CTkOptionMenu(
            mp_input_frame,
            values=[
                "English (eng)",
                "Spanish (spa)",
                "French (fre)",
                "Indonesian (ind)",
                "Portuguese (por)",
                "German (deu)",
                "Thai (tha)",
                "Russian (rus)",
                "Vietnamese (vie)",
            ],
            width=140,
            fg_color="#1e2235",
            button_color="#2d3246",
        )
        self.lang_menu.set("English (eng)")
        self.lang_menu.pack(side="left", padx=(0, 8))

        download_mp_btn = ctk.CTkButton(
            mp_input_frame, 
            text="📥 Fetch Chapter", 
            width=120, 
            fg_color="#e11d48", 
            hover_color="#be123c", 
            font=ctk.CTkFont(weight="bold"),
            command=self._start_mangaplus_thread
        )
        download_mp_btn.pack(side="left")

        # 5. Manga Chapter Downloader (MangaDex Colored & WeebCentral Official B&W)
        md_container = ctk.CTkFrame(content_frame, fg_color="transparent")
        md_container.grid(row=7, column=0, columnspan=2, sticky="ew", padx=16, pady=(6, 2))

        md_label = ctk.CTkLabel(
            md_container, 
            text="Download Chapters / Ranges (Supports 1-10, 1-1190, etc.):", 
            font=ctk.CTkFont(size=13, weight="bold")
        )
        md_label.pack(side="left", anchor="w")

        md_input_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        md_input_frame.grid(row=8, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 10))

        self.md_entry = ctk.CTkEntry(md_input_frame, placeholder_text="Chapter or Range (e.g. 1-10 or 1-1190)", width=230)
        self.md_entry.pack(side="left", padx=(0, 8))

        self.md_edition_menu = ctk.CTkOptionMenu(
            md_input_frame,
            values=["Official Colored (Ch 1-764+)", "Official Viz B&W (Ch 1-1193+)"],
            width=210,
            fg_color="#1e2235",
            button_color="#2d3246",
        )
        self.md_edition_menu.set("Official Colored (Ch 1-764+)")
        self.md_edition_menu.pack(side="left", padx=(0, 8))

        self.download_md_btn = ctk.CTkButton(
            md_input_frame, 
            text="📥 Download Range", 
            width=150, 
            fg_color="#0284c7", 
            hover_color="#0369a1", 
            font=ctk.CTkFont(weight="bold"),
            command=self._start_mangadex_thread
        )
        self.download_md_btn.pack(side="left", padx=(0, 6))

        self.stop_md_btn = ctk.CTkButton(
            md_input_frame, 
            text="⏹ Stop", 
            width=70, 
            fg_color="#475569", 
            hover_color="#334155", 
            font=ctk.CTkFont(weight="bold"),
            command=self._stop_mangadex_thread,
            state="disabled"
        )
        self.stop_md_btn.pack(side="left")

        # Action Buttons Row
        btn_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=8)

        self.pack_btn = ctk.CTkButton(
            btn_frame,
            text="📦 Pack Volume CBZ",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self._start_pack_thread,
        )
        self.pack_btn.pack(side="left", padx=(0, 8))

        self.sample_btn = ctk.CTkButton(
            btn_frame,
            text="✨ Generate Demo Sample CBZ",
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            command=self._start_sample_thread,
        )
        self.sample_btn.pack(side="left", padx=8)

        self.sync_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 Sync Catalog index.json",
            fg_color="#10b981",
            hover_color="#059669",
            command=self._sync_catalog,
        )
        self.sync_btn.pack(side="left", padx=8)

        self.r2_btn = ctk.CTkButton(
            btn_frame,
            text="☁️ Cloudflare R2 Sync",
            fg_color="#ea580c",
            hover_color="#c2410c",
            font=ctk.CTkFont(weight="bold"),
            command=self._open_r2_dialog,
        )
        self.r2_btn.pack(side="left", padx=8)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.root)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=16, pady=6)

        # Log box
        log_label = ctk.CTkLabel(self.root, text="Activity Log:", font=ctk.CTkFont(size=12, weight="bold"))
        log_label.pack(anchor="w", padx=16, pady=(6, 2))

        self.log_box = ctk.CTkTextbox(self.root, height=180, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_box.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.log("Ready. Select source images or click 'Generate Demo Sample CBZ' to test immediately.")

        # Initial scan after UI loads
        self.root.after(300, self._scan_and_update_ready_volumes)

    def log(self, text: str):
        timestamp = time.strftime("[%H:%M:%S] ")
        self.log_box.insert("end", timestamp + text + "\n")
        self.log_box.see("end")

    def _browse_source(self):
        folder = filedialog.askdirectory(title="Select Manga Chapter / Image Folder")
        if folder:
            self.src_entry.delete(0, "end")
            self.src_entry.insert(0, folder)
            self.log(f"Selected source: {folder}")
            self._scan_and_update_ready_volumes()

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Select Output Directory")
        if folder:
            self.out_entry.delete(0, "end")
            self.out_entry.insert(0, folder)
            self.log(f"Selected output: {folder}")

    def _scan_and_update_ready_volumes(self):
        src = self.src_entry.get().strip() or self.default_output_dir
        if not os.path.exists(src):
            self.bundler_status_lbl.configure(
                text="Source directory does not exist yet.",
                text_color="#f87171"
            )
            self.ready_vol_menu.configure(values=["(No folder)"])
            self.bundle_all_btn.configure(state="disabled", text="📦 Bundle All Ready Volumes")
            return

        if scan_folder_for_bundleable_volumes is None:
            self.bundler_status_lbl.configure(text="volume_bundler module not available.")
            return

        res = scan_folder_for_bundleable_volumes(src)
        self.last_scan_res = res

        ready = res.get("ready_volumes", [])
        unbundled_ready = [v for v in ready if not v["is_bundled"]]
        already_bundled = [v for v in ready if v["is_bundled"]]
        partials = res.get("partial_volumes", [])
        total_ch = res.get("total_chapters", 0)

        # Status message
        if unbundled_ready:
            status_text = (
                f"📁 Found {total_ch} Chapter CBZs • {len(unbundled_ready)} Volumes Ready to Bundle! "
                f"({len(already_bundled)} already bundled)\n"
                f"   [Subfolder 'covers' safely excluded]"
            )
            text_color = "#38bdf8"
        elif ready:
            status_text = (
                f"📁 Found {total_ch} Chapter CBZs • All {len(ready)} ready volumes are already bundled!\n"
                f"   [Subfolder 'covers' safely excluded]"
            )
            text_color = "#34d399"
        else:
            status_text = (
                f"📁 Found {total_ch} Chapter CBZs in source • No complete volume chapter sets detected yet.\n"
                f"   [Subfolder 'covers' safely excluded]"
            )
            text_color = "#94a3b8"

        self.bundler_status_lbl.configure(text=status_text, text_color=text_color)

        # Populate option menu
        menu_items = []
        for v in unbundled_ready:
            menu_items.append(f"Vol {v['volume']:02d}: {v['title']} (Ch {v['ch_start']}-{v['ch_end']}) [READY]")
        for v in already_bundled:
            menu_items.append(f"Vol {v['volume']:02d}: {v['title']} (Ch {v['ch_start']}-{v['ch_end']}) [BUNDLED]")

        if not menu_items:
            menu_items = ["(No volumes available)"]

        self.ready_vol_menu.configure(values=menu_items)
        self.ready_vol_menu.set(menu_items[0])

        # Populate partial volumes menu
        self.partial_volumes_data = partials
        partial_items = []
        for p in partials:
            missing_str = ", ".join(str(c) for c in p["missing"][:4])
            if len(p["missing"]) > 4:
                missing_str += "..."
            partial_items.append(f"Vol {p['volume']:02d}: {p['title']} (Missing {len(p['missing'])}: Ch {missing_str})")
        if not partial_items:
            partial_items = ["(No partial volumes - all complete!)"]
        self.partial_vol_menu.configure(values=partial_items)
        self.partial_vol_menu.set(partial_items[0])
        self.download_missing_btn.configure(state="normal" if partials else "disabled")

        # Configure bundle all button
        btn_text = f"📦 Bundle All Ready Volumes ({len(unbundled_ready)})" if unbundled_ready else "📦 All Ready Volumes Bundled"
        self.bundle_all_btn.configure(
            text=btn_text,
            state="normal" if unbundled_ready else "disabled"
        )

    def _start_bundle_all_thread(self):
        src = self.src_entry.get().strip() or self.default_output_dir
        out = self.out_entry.get().strip() or self.default_output_dir
        if not os.path.exists(src):
            messagebox.showerror("Error", f"Source folder not found: {src}")
            return

        self.bundle_all_btn.configure(state="disabled")
        self.bundle_selected_btn.configure(state="disabled")
        self.progress_bar.set(0.0)

        def worker():
            try:
                def on_prog(pct, msg):
                    self.root.after(0, lambda: self.progress_bar.set(pct))

                summary = bundle_all_ready_volumes(
                    source_dir=src,
                    output_dir=out,
                    compress_webp=self.webp_var.get(),
                    prefer_official_cover=self.shueisha_cover_var.get(),
                    skip_already_bundled=True,
                    sync_catalog=True,
                    progress_callback=on_prog,
                    log_callback=self.log,
                )
                self.root.after(0, lambda: self.progress_bar.set(1.0))
                self.root.after(0, self._scan_and_update_ready_volumes)
                messagebox.showinfo(
                    "Bundling Complete",
                    f"Successfully bundled {summary['bundled']} volume(s) into CBZ!\n"
                    f"• Bundled: {summary['bundled']}\n"
                    f"• Skipped (Already Bundled): {summary['skipped']}\n\n"
                    f"Catalog index.json updated."
                )
            except Exception as e:
                self.log(f"ERROR: {e}")
                messagebox.showerror("Bundling Failed", str(e))
            finally:
                self.root.after(0, lambda: self.bundle_all_btn.configure(state="normal"))
                self.root.after(0, lambda: self.bundle_selected_btn.configure(state="normal"))
                if hasattr(self, "bundle_push_r2_btn"):
                    self.root.after(0, lambda: self.bundle_push_r2_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _start_bundle_selected_thread(self):
        src = self.src_entry.get().strip() or self.default_output_dir
        out = self.out_entry.get().strip() or self.default_output_dir

        sel_text = self.ready_vol_menu.get()
        m = re.search(r"Vol\s+(\d+)", sel_text)
        if not m:
            messagebox.showwarning("Selection", "Please select a valid volume from the dropdown.")
            return
        vol_num = int(m.group(1))

        self.bundle_all_btn.configure(state="disabled")
        self.bundle_selected_btn.configure(state="disabled")
        if hasattr(self, "bundle_push_r2_btn"):
            self.bundle_push_r2_btn.configure(state="disabled")
        self.progress_bar.set(0.3)

        def worker():
            try:
                scan_res = scan_folder_for_bundleable_volumes(src)
                ch_map = scan_res.get("chapter_map", {})
                archive = bundle_volume_from_chapters(
                    vol_num=vol_num,
                    chapter_map=ch_map,
                    output_dir=out,
                    compress_webp=self.webp_var.get(),
                    prefer_official_cover=self.shueisha_cover_var.get(),
                    sync_catalog=True,
                    log_callback=self.log,
                )
                self.root.after(0, lambda: self.progress_bar.set(1.0))
                self.root.after(0, self._scan_and_update_ready_volumes)
                messagebox.showinfo(
                    "Volume Bundled",
                    f"Successfully bundled Volume {vol_num}!\nDestination: {archive.name}"
                )
            except Exception as e:
                self.log(f"ERROR: {e}")
                messagebox.showerror("Bundling Failed", str(e))
            finally:
                self.root.after(0, lambda: self.bundle_all_btn.configure(state="normal"))
                self.root.after(0, lambda: self.bundle_selected_btn.configure(state="normal"))
                if hasattr(self, "bundle_push_r2_btn"):
                    self.root.after(0, lambda: self.bundle_push_r2_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _start_bundle_and_push_r2_thread(self):
        """Bundles all ready volumes and pushes them directly to Cloudflare R2."""
        src = self.src_entry.get().strip() or self.default_output_dir
        out = self.out_entry.get().strip() or self.default_output_dir
        if not os.path.exists(src):
            messagebox.showerror("Error", f"Source folder not found: {src}")
            return

        cfg = load_r2_config() if load_r2_config else {}
        if not cfg or not cfg.get("access_key_id"):
            messagebox.showwarning(
                "R2 Credentials Needed",
                "Please configure Cloudflare R2 credentials first using the '☁️ Cloudflare R2 Sync' button."
            )
            return

        self.bundle_all_btn.configure(state="disabled")
        self.bundle_selected_btn.configure(state="disabled")
        self.bundle_push_r2_btn.configure(state="disabled")
        self.progress_bar.set(0.0)

        def worker():
            try:
                self.log("\n[1/2] Bundling ready volumes with WebP compression...")
                def on_prog(pct, msg):
                    self.root.after(0, lambda: self.progress_bar.set(pct * 0.5))

                summary = bundle_all_ready_volumes(
                    source_dir=src,
                    output_dir=out,
                    compress_webp=self.webp_var.get(),
                    prefer_official_cover=self.shueisha_cover_var.get(),
                    skip_already_bundled=True,
                    sync_catalog=True,
                    progress_callback=on_prog,
                    log_callback=self.log,
                )

                self.log(f"\n[2/2] Pushing volume archives to Cloudflare R2 (bucket: {cfg.get('bucket_name')})...")
                def on_r2_prog(pct, msg):
                    self.root.after(0, lambda: self.progress_bar.set(0.5 + pct * 0.5))

                r2_res = sync_comics_folder_to_r2(
                    source_dir=out,
                    only_volumes=True,
                    sync_catalog_json=True,
                    progress_callback=on_r2_prog,
                    log_callback=self.log,
                )
                self.root.after(0, lambda: self.progress_bar.set(1.0))
                self.root.after(0, self._scan_and_update_ready_volumes)
                messagebox.showinfo(
                    "Bundle & R2 Push Complete",
                    f"Pipeline successfully completed!\n\n"
                    f"• Bundled: {summary['bundled']} volume(s)\n"
                    f"• Uploaded to R2: {r2_res['uploaded']} archive(s)\n"
                    f"• R2 Skipped: {r2_res['skipped']} (already synced)\n\n"
                    f"Showcase catalog updated with live Cloudflare streaming URLs!"
                )
            except StorageLimitExceededError as se:
                self.log(f"\n[Free Tier Limit Exceeded] {se}")
                info = getattr(se, 'storage_info', {})
                current_gb = info.get('current_gb', 0)
                incoming_gb = info.get('incoming_gb', 0)
                projected_gb = info.get('projected_gb', 0)
                excess_gb = info.get('excess_gb', 0)
                self.root.after(0, lambda: messagebox.showwarning(
                    "Cloudflare R2 10 GB Free Tier Limit",
                    f"⚠️ Upload Aborted: Exceeds 10 GB Free Tier Limit!\n\n"
                    f"• Current R2 Usage: {current_gb:.2f} GB\n"
                    f"• Incoming Upload:  {incoming_gb:.2f} GB\n"
                    f"• Projected Total:  {projected_gb:.2f} GB\n"
                    f"• Excess over 10GB: {excess_gb:.2f} GB\n\n"
                    f"Sync was automatically stopped to prevent unexpected Cloudflare billing charges.\n"
                    f"To free up space, delete older archives from your R2 bucket or reduce the upload batch."
                ))
            except Exception as e:
                self.log(f"ERROR: {e}")
                messagebox.showerror("Pipeline Failed", str(e))
            finally:
                self.root.after(0, lambda: self.bundle_all_btn.configure(state="normal"))
                self.root.after(0, lambda: self.bundle_selected_btn.configure(state="normal"))
                self.root.after(0, lambda: self.bundle_push_r2_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _start_download_missing_thread(self):
        """1-Click download for missing chapters in the selected partial volume."""
        src = self.src_entry.get().strip() or self.default_output_dir
        if not hasattr(self, "partial_volumes_data") or not self.partial_volumes_data:
            messagebox.showinfo("Complete", "No partial volumes with missing chapters found!")
            return

        sel_text = self.partial_vol_menu.get()
        m = re.search(r"Vol\s+(\d+)", sel_text)
        if not m:
            messagebox.showwarning("Selection", "Please select a partial volume from the dropdown.")
            return
        vol_num = int(m.group(1))

        target = next((p for p in self.partial_volumes_data if p["volume"] == vol_num), None)
        if not target or not target["missing"]:
            messagebox.showinfo("Complete", f"Volume {vol_num} is not missing any chapters!")
            return

        missing_chapters = target["missing"]
        self.download_missing_btn.configure(state="disabled")
        self.bundle_all_btn.configure(state="disabled")
        self.progress_bar.set(0.1)

        def worker():
            try:
                self.log(f"\n⚡ Starting 1-Click download of {len(missing_chapters)} missing chapter(s) for Volume {vol_num}: {missing_chapters}")
                if download_weebcentral_batch:
                    download_weebcentral_batch(
                        chapters=missing_chapters,
                        output_dir=src,
                        sync_catalog=True,
                        log_callback=self.log,
                    )
                else:
                    raise RuntimeError("WeebCentral downloader module not available.")

                self.root.after(0, lambda: self.progress_bar.set(1.0))
                self.root.after(0, self._scan_and_update_ready_volumes)
                messagebox.showinfo(
                    "Download Complete",
                    f"Successfully downloaded {len(missing_chapters)} missing chapter(s) for Volume {vol_num}!\n"
                    f"Volume {vol_num} is now ready to bundle."
                )
            except Exception as e:
                self.log(f"ERROR: {e}")
                messagebox.showerror("Download Failed", str(e))
            finally:
                self.root.after(0, lambda: self.download_missing_btn.configure(state="normal"))
                self.root.after(0, lambda: self.bundle_all_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _check_for_new_chapters(self):
        """Checks online providers for newly released One Piece chapters and prompts to download."""
        src = self.src_entry.get().strip() or self.default_output_dir
        self.check_new_ch_btn.configure(state="disabled")

        def worker():
            try:
                self.log("\n🔔 Checking online providers for newly published One Piece chapters...")
                if not fetch_weebcentral_chapter_map:
                    raise RuntimeError("Chapter indexer module not available.")

                ch_map = fetch_weebcentral_chapter_map(force_refresh=True, log_callback=self.log)
                latest_remote = int(max(ch_map.keys()))

                scan_res = scan_folder_for_bundleable_volumes(src)
                local_chs = scan_res.get("chapter_map", {}).keys()
                highest_local = max(local_chs) if local_chs else 0

                self.log(f"Latest Online Chapter: {latest_remote} | Highest Local Chapter: {highest_local}")

                if latest_remote > highest_local:
                    new_count = latest_remote - highest_local
                    new_range = list(range(highest_local + 1, latest_remote + 1))
                    if messagebox.askyesno(
                        "New Chapters Available!",
                        f"Found {new_count} new One Piece chapter(s) published online!\n\n"
                        f"• Latest Online: Chapter {latest_remote}\n"
                        f"• Your Library: Chapter {highest_local}\n"
                        f"• New: Chapters {new_range[0]} to {new_range[-1]}\n\n"
                        f"Would you like to download them now?"
                    ):
                        self.log(f"Downloading {new_count} new chapters: {new_range}...")
                        download_weebcentral_batch(new_range, output_dir=src, sync_catalog=True, log_callback=self.log)
                        self.root.after(0, self._scan_and_update_ready_volumes)
                        messagebox.showinfo("Downloaded", f"Successfully downloaded {new_count} new chapter(s)!")
                else:
                    messagebox.showinfo(
                        "Up to Date",
                        f"Your One Piece library is completely up to date!\n\n"
                        f"Latest Chapter: {latest_remote}"
                    )
            except Exception as e:
                self.log(f"Error checking new chapters: {e}")
                messagebox.showerror("Check Failed", str(e))
            finally:
                self.root.after(0, lambda: self.check_new_ch_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()


    def _on_volume_changed(self, event=None):
        try:
            v = int(self.vol_spin.get().strip())
            meta = get_volume_meta(v)
            self.meta_preview_lbl.configure(
                text=f"Canon: {meta['title']} (Ch {meta['chapterStart']}-{meta['chapterEnd']}) • {meta['sagaName']}"
            )
        except Exception:
            pass

    def _start_pack_thread(self):
        src = self.src_entry.get().strip()
        out = self.out_entry.get().strip()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "Please choose a valid source folder first.")
            return

        try:
            vol = int(self.vol_spin.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid volume number.")
            return

        self.pack_btn.configure(state="disabled")
        self.progress_bar.set(0.3)

        def worker():
            try:
                self.log(f"Starting packaging for Volume {vol}...")
                archive = pack_folder_to_volume_cbz(src, out, vol, log_callback=self.log)
                self.progress_bar.set(0.8)
                self.log("Syncing index.json...")
                scan_and_index_volumes(out, self.output_index_path)
                self.progress_bar.set(1.0)
                self.log(f"SUCCESS: Volume {vol} ready at {archive}")
                messagebox.showinfo("Success", f"Volume {vol} packaged successfully!\n{archive}")
            except Exception as e:
                self.log(f"ERROR: {e}")
                messagebox.showerror("Packaging Failed", str(e))
            finally:
                self.pack_btn.configure(state="normal")

        threading.Thread(target=worker, daemon=True).start()

    def _start_sample_thread(self):
        out = self.out_entry.get().strip()
        try:
            vol = int(self.vol_spin.get().strip())
        except ValueError:
            vol = 1

        self.sample_btn.configure(state="disabled")
        self.progress_bar.set(0.4)

        def worker():
            try:
                archive = create_dummy_sample_volume(out, vol_num=vol, page_count=12, log_callback=self.log)
                self.progress_bar.set(0.8)
                self.log("Syncing index.json...")
                scan_and_index_volumes(out, self.output_index_path)
                self.progress_bar.set(1.0)
                self.log(f"Demo Volume {vol} created at: {archive}")
                messagebox.showinfo("Demo Volume Generated", f"Demo Volume {vol} generated with ComicInfo.xml and pages!\n{archive}")
            except Exception as e:
                self.log(f"ERROR: {e}")
            finally:
                self.sample_btn.configure(state="normal")

        threading.Thread(target=worker, daemon=True).start()

    def _start_mangaplus_thread(self):
        url = self.mp_entry.get().strip()
        out = self.out_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please paste a MangaPlus viewer URL or chapter ID first.")
            return

        selected_lang_raw = self.lang_menu.get()
        match = re.search(r"\(([a-z]{3})\)", selected_lang_raw, re.IGNORECASE)
        target_lang = match.group(1).lower() if match else "eng"

        self.progress_bar.set(0.2)

        def worker():
            try:
                self.log(f"Connecting to MangaPlus ({target_lang.upper()}): {url}...")
                try:
                    from tools.mangaplus_downloader import download_mangaplus_chapter
                except ImportError:
                    from mangaplus_downloader import download_mangaplus_chapter

                archive = download_mangaplus_chapter(
                    url, 
                    output_dir=out, 
                    target_lang=target_lang,
                    log_callback=self.log, 
                    sync_catalog=True
                )
                self.progress_bar.set(1.0)
                self.log(f"SUCCESS: Chapter saved at: {archive}")
                messagebox.showinfo("Success", f"MangaPlus chapter downloaded & indexed successfully!\n{archive}")
            except Exception as e:
                self.log(f"ERROR: {e}")
                messagebox.showerror("Download Failed", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _stop_mangadex_thread(self):
        self.cancel_download = True
        self.log("\n[User Request] Stopping MangaDex batch download...")

    def _start_mangadex_thread(self):
        ch_str = self.md_entry.get().strip()
        if not ch_str:
            messagebox.showwarning("Missing Chapter Specification", "Please enter a chapter number or range (e.g. 1-10 or 1-1190).")
            return

        edition = "colored" if "colored" in self.md_edition_menu.get().lower() else "bw"
        out = self.out_entry.get().strip()

        # Extract language ISO from lang_menu
        raw_lang = self.lang_menu.get()
        m = re.search(r"\((.*?)\)", raw_lang)
        target_lang = m.group(1).lower() if m else "en"
        lang_iso_map = {"eng": "en", "spa": "es", "fre": "fr", "ind": "id", "por": "pt-br", "deu": "de", "tha": "th", "rus": "ru", "vie": "vi"}
        lang_code = lang_iso_map.get(target_lang, target_lang)

        self.cancel_download = False
        self.download_md_btn.configure(state="disabled")
        self.stop_md_btn.configure(state="normal")
        self.progress_bar.set(0.0)

        def worker():
            try:
                if download_mangadex_batch is None:
                    raise ImportError("mangadex_downloader module not found.")

                def on_progress(pct, status_text):
                    self.root.after(0, lambda: self.progress_bar.set(pct))

                summary = download_mangadex_batch(
                    chapter_spec=ch_str,
                    output_dir=out,
                    lang=lang_code,
                    edition=edition,
                    skip_existing=True,
                    sync_catalog=True,
                    progress_callback=on_progress,
                    log_callback=self.log,
                    cancel_flag=lambda: self.cancel_download,
                )
                self.root.after(0, lambda: self.progress_bar.set(1.0))
                self.log(f"\n[Finished] Batch finished: {summary['downloaded']} downloaded, {summary['skipped']} skipped.")
                messagebox.showinfo(
                    "MangaDex Batch Complete",
                    f"Processed chapters: {ch_str}\n"
                    f"• Downloaded: {summary['downloaded']}\n"
                    f"• Skipped (Already Cached): {summary['skipped']}\n"
                    f"• Missing/Failed: {len(summary['failed'])}"
                )
            except Exception as e:
                self.log(f"ERROR: {e}")
                messagebox.showerror("Download Failed", str(e))
            finally:
                self.root.after(0, lambda: self.download_md_btn.configure(state="normal"))
                self.root.after(0, lambda: self.stop_md_btn.configure(state="disabled"))

        threading.Thread(target=worker, daemon=True).start()

    def _sync_catalog(self):
        out = self.out_entry.get().strip()
        self.log(f"Syncing catalog index for directory: {out}...")
        manifest = scan_and_index_volumes(out, self.output_index_path)
        self.log(f"Catalog indexed: {len(manifest['volumes'])} volumes, {len(manifest['sagas'])} sagas.")
        messagebox.showinfo("Catalog Synced", f"Catalog updated successfully with {len(manifest['volumes'])} volumes.")

    def _open_r2_dialog(self):
        """Opens the Cloudflare R2 Free Storage manager window."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Cloudflare R2 Free Storage (Zero Egress Bandwidth)")
        dialog.geometry("680x600")
        dialog.minsize(620, 520)
        dialog.grab_set()

        cfg = load_r2_config() if load_r2_config else {}

        # Header info
        header_frame = ctk.CTkFrame(dialog, fg_color="#181a26")
        header_frame.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(
            header_frame,
            text="☁️ Cloudflare R2 Storage (10 GB Free Forever • 0 Bandwidth Fees)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f97316"
        ).pack(anchor="w", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            header_frame,
            text="Host your volume CBZs on Cloudflare R2 for free with zero egress fees.\n"
                 "No custom domain required! Uses the free 'pub-xxxx.r2.dev' public URL.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 10))

        # Form fields
        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=4)

        # 1. Account ID
        ctk.CTkLabel(form, text="Cloudflare Account ID:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", pady=4)
        acc_entry = ctk.CTkEntry(form, width=380, placeholder_text="Found in Cloudflare dashboard URL or R2 overview")
        acc_entry.insert(0, cfg.get("account_id", ""))
        acc_entry.grid(row=0, column=1, sticky="ew", pady=4, padx=(8, 0))

        # 2. Access Key ID
        ctk.CTkLabel(form, text="R2 Access Key ID:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", pady=4)
        key_entry = ctk.CTkEntry(form, width=380, placeholder_text="From 'Manage R2 API Tokens'")
        key_entry.insert(0, cfg.get("access_key_id", ""))
        key_entry.grid(row=1, column=1, sticky="ew", pady=4, padx=(8, 0))

        # 3. Secret Access Key
        ctk.CTkLabel(form, text="R2 Secret Access Key:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", pady=4)
        sec_entry = ctk.CTkEntry(form, width=380, show="•", placeholder_text="From 'Manage R2 API Tokens'")
        sec_entry.insert(0, cfg.get("secret_access_key", ""))
        sec_entry.grid(row=2, column=1, sticky="ew", pady=4, padx=(8, 0))

        # 4. Bucket Name
        ctk.CTkLabel(form, text="R2 Bucket Name:", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, sticky="w", pady=4)
        bucket_entry = ctk.CTkEntry(form, width=380, placeholder_text="e.g. one-piece-comics")
        bucket_entry.insert(0, cfg.get("bucket_name", ""))
        bucket_entry.grid(row=3, column=1, sticky="ew", pady=4, padx=(8, 0))

        # 5. Public R2.dev URL
        ctk.CTkLabel(form, text="Public R2.dev URL:", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, sticky="w", pady=4)
        pub_entry = ctk.CTkEntry(form, width=380, placeholder_text="e.g. https://pub-xxxxxx.r2.dev")
        pub_entry.insert(0, cfg.get("public_url", ""))
        pub_entry.grid(row=4, column=1, sticky="ew", pady=4, padx=(8, 0))

        form.columnconfigure(1, weight=1)

        # Status label
        status_lbl = ctk.CTkLabel(dialog, text="", font=ctk.CTkFont(size=11))
        status_lbl.pack(pady=4)

        # Buttons Row 1: Save & Test
        row1 = ctk.CTkFrame(dialog, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=4)

        def get_current_inputs():
            return {
                "account_id": acc_entry.get().strip(),
                "access_key_id": key_entry.get().strip(),
                "secret_access_key": sec_entry.get().strip(),
                "bucket_name": bucket_entry.get().strip(),
                "public_url": pub_entry.get().strip(),
            }

        def on_save():
            if save_r2_config is None:
                messagebox.showerror("Error", "r2_sync module not found.")
                return
            vals = get_current_inputs()
            save_r2_config(**vals)
            status_lbl.configure(text="✅ Configuration saved to r2_config.json", text_color="#34d399")

        def on_test():
            if test_r2_connection is None:
                messagebox.showerror("Error", "r2_sync module not found.")
                return
            vals = get_current_inputs()
            if save_r2_config:
                save_r2_config(**vals)
            status_lbl.configure(text="Testing connection...", text_color="#38bdf8")
            def worker():
                ok, msg = test_r2_connection(vals)
                color = "#34d399" if ok else "#f87171"
                dialog.after(0, lambda: status_lbl.configure(text=msg, text_color=color))
            threading.Thread(target=worker, daemon=True).start()

        def on_cors():
            if configure_r2_cors is None:
                messagebox.showerror("Error", "r2_sync module not found.")
                return
            vals = get_current_inputs()
            if save_r2_config:
                save_r2_config(**vals)
            status_lbl.configure(text="Configuring public CORS on bucket...", text_color="#38bdf8")
            def worker():
                ok = configure_r2_cors(vals)
                msg = "✅ Public CORS configured! Web browsers can stream from this bucket." if ok else "❌ Failed to set CORS."
                color = "#34d399" if ok else "#f87171"
                dialog.after(0, lambda: status_lbl.configure(text=msg, text_color=color))
            threading.Thread(target=worker, daemon=True).start()

        ctk.CTkButton(row1, text="💾 Save Config", command=on_save, fg_color="#334155", width=120).pack(side="left", padx=(0, 8))
        ctk.CTkButton(row1, text="⚡ Test Connection", command=on_test, fg_color="#0284c7", hover_color="#0369a1", width=140).pack(side="left", padx=4)
        ctk.CTkButton(row1, text="🌐 Set Bucket CORS", command=on_cors, fg_color="#475569", hover_color="#334155", width=150).pack(side="left", padx=4)

        # Upload Actions Row
        row2 = ctk.CTkFrame(dialog, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(12, 4))

        def start_sync(only_vols: bool):
            if sync_comics_folder_to_r2 is None:
                messagebox.showerror("Error", "r2_sync module not found.")
                return
            vals = get_current_inputs()
            if save_r2_config:
                save_r2_config(**vals)
            src = self.src_entry.get().strip() or self.default_output_dir
            status_lbl.configure(text="Starting sync to Cloudflare R2...", text_color="#f97316")
            dialog.destroy()

            self.progress_bar.set(0.0)
            def worker():
                try:
                    summary = sync_comics_folder_to_r2(
                        source_dir=src,
                        config=vals,
                        only_volumes=only_vols,
                        progress_callback=lambda pct, msg: self.root.after(0, lambda: (self.progress_bar.set(pct), self.log(msg))),
                        log_callback=self.log,
                    )
                    self.root.after(0, lambda: self.progress_bar.set(1.0))
                    messagebox.showinfo(
                        "Cloudflare R2 Sync Complete",
                        f"Sync complete!\n"
                        f"• Uploaded: {summary['uploaded']}\n"
                        f"• Skipped (Up to date): {summary['skipped']}\n"
                        f"• Failed: {len(summary['failed'])}\n\n"
                        f"Manga showcase index.json updated."
                    )
                except StorageLimitExceededError as se:
                    self.log(f"\n[Free Tier Limit Exceeded] {se}")
                    info = getattr(se, 'storage_info', {})
                    current_gb = info.get('current_gb', 0)
                    incoming_gb = info.get('incoming_gb', 0)
                    projected_gb = info.get('projected_gb', 0)
                    excess_gb = info.get('excess_gb', 0)
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Cloudflare R2 10 GB Free Tier Limit",
                        f"⚠️ Upload Aborted: Exceeds 10 GB Free Tier Limit!\n\n"
                        f"• Current R2 Usage: {current_gb:.2f} GB\n"
                        f"• Incoming Upload:  {incoming_gb:.2f} GB\n"
                        f"• Projected Total:  {projected_gb:.2f} GB\n"
                        f"• Excess over 10GB: {excess_gb:.2f} GB\n\n"
                        f"Sync was automatically stopped to prevent unexpected Cloudflare billing charges.\n"
                        f"To free up space, delete older archives from your R2 bucket or reduce the upload batch."
                    ))
                except Exception as e:
                    self.log(f"R2 Sync Error: {e}")
                    messagebox.showerror("R2 Sync Error", str(e))

            threading.Thread(target=worker, daemon=True).start()

        ctk.CTkButton(
            row2,
            text="🚀 Sync Volume CBZs to Cloudflare R2",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#f97316",
            hover_color="#ea580c",
            command=lambda: start_sync(only_vols=True)
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            row2,
            text="📦 Sync All (Volumes + Chapters + Covers)",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#d97706",
            hover_color="#b45309",
            command=lambda: start_sync(only_vols=False)
        ).pack(side="left", fill="x", expand=True, padx=(6, 0))

        # Row 3: Discover files already uploaded in Cloudflare dashboard
        row3 = ctk.CTkFrame(dialog, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=(10, 16))

        def on_refresh_r2_catalog():
            status_lbl.configure(text="Connecting to R2 and discovering remote files...", text_color="#38bdf8")
            def worker():
                try:
                    if sync_catalog is None:
                        raise RuntimeError("sync_r2_catalog module not found.")
                    sync_catalog()
                    dialog.after(0, lambda: (
                        status_lbl.configure(text="✅ index.json refreshed with files in your R2 bucket!", text_color="#34d399"),
                        messagebox.showinfo(
                            "Cloudflare R2 Catalog Refreshed",
                            "Successfully scanned your Cloudflare R2 bucket and updated index.json!\n\n"
                            "All matching volumes are now marked as available to stream in the web app."
                        )
                    ))
                except Exception as e:
                    dialog.after(0, lambda: (
                        status_lbl.configure(text=f"❌ Refresh failed: {e}", text_color="#f87171"),
                        messagebox.showerror("R2 Refresh Error", str(e))
                    ))
            threading.Thread(target=worker, daemon=True).start()

        ctk.CTkButton(
            row3,
            text="🔄 Discover Remote R2 Files & Update Catalog (For Dashboard Uploads)",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            command=on_refresh_r2_catalog
        ).pack(fill="x", expand=True)


# ============================================================================
# CLI RUNNER (Headless / Automated Execution)
# ============================================================================

def run_cli():
    parser = argparse.ArgumentParser(description="One Piece Manga Organizer CLI")
    parser.add_argument("--cli", action="store_true", help="Run in headless CLI mode")
    parser.add_argument("--source", type=str, help="Source directory containing chapter images")
    parser.add_argument("--output", type=str, default="../frontend/public/comics", help="Output directory for CBZs")
    parser.add_argument("--volume", type=int, default=1, help="Volume number to pack")
    parser.add_argument("--sample", action="store_true", help="Generate a sample dummy volume CBZ")
    parser.add_argument("--pages", type=int, default=12, help="Page count for sample volume")
    parser.add_argument("--sync-only", action="store_true", help="Only sync catalog index.json")
    parser.add_argument("--mangaplus", type=str, help="Download chapter from MangaPlus viewer URL")
    parser.add_argument("--mangadex", type=str, help="Download chapter from MangaDex by chapter number (e.g. 4 or 14)")
    parser.add_argument("--edition", type=str, default="colored", choices=["colored", "bw"], help="Edition for MangaDex (colored or bw) [default: colored]")
    parser.add_argument("--lang", type=str, default="eng", help="Target language (eng, spa, fre, ind, por, deu, tha, rus, vie) [default: eng]")
    parser.add_argument("--bundle-all", action="store_true", help="Auto-bundle all ready volumes from chapter CBZs in source folder")
    parser.add_argument("--bundle-volume", type=int, help="Bundle a specific volume number from chapter CBZs in source folder")
    parser.add_argument("--scan-bundles", action="store_true", help="Scan source folder and list ready/partial volumes")
    parser.add_argument("--prefer-official-cover", action="store_true", help="Replace chapter 1 cover with official Shueisha cover (default: keep chapter cover if present)")

    args, unknown = parser.parse_known_args()

    # Determine if we should run GUI or CLI
    if args.cli or args.sample or args.source or args.sync_only or args.mangaplus or args.mangadex or args.bundle_all or args.bundle_volume or args.scan_bundles or not CTK_AVAILABLE or not os.environ.get("DISPLAY", None) and sys.platform.startswith("linux"):
        # Run CLI mode
        out_dir = Path(args.output).resolve()
        index_dest = out_dir / "index.json"

        if args.scan_bundles:
            src = args.source or str(out_dir)
            if scan_folder_for_bundleable_volumes is None:
                raise ImportError("volume_bundler module not found.")
            res = scan_folder_for_bundleable_volumes(src)
            print(f"\n[CLI] Scanned: {res['source_path']}")
            print(f"Total Chapter CBZs Found: {res['total_chapters']} (subfolder 'covers' ignored)\n")
            print("=== Ready to Bundle Volumes ===")
            for v in res["ready_volumes"]:
                tag = "[ALREADY BUNDLED]" if v["is_bundled"] else "[READY!]"
                print(f"  Vol {v['volume']:2d} (Ch {v['ch_start']:3d}-{v['ch_end']:3d}): {v['total_chapters']} chapters {tag} - '{v['title']}'")
            if res["partial_volumes"]:
                print("\n=== Partial Volumes ===")
                for v in res["partial_volumes"]:
                    print(f"  Vol {v['volume']:2d} (Ch {v['ch_start']:3d}-{v['ch_end']:3d}): {v['have_count']}/{v['needed_count']} chapters - '{v['title']}'")
            return 0

        if args.bundle_all:
            src = args.source or str(out_dir)
            print(f"[CLI] Auto-bundling all ready volumes from '{src}' into '{args.output}'...")
            if bundle_all_ready_volumes is None:
                raise ImportError("volume_bundler module not found.")
            res = bundle_all_ready_volumes(source_dir=src, output_dir=out_dir, sync_catalog=True, prefer_official_cover=args.prefer_official_cover)
            print(f"[CLI] Finished! Bundled: {res['bundled']}, Skipped: {res['skipped']}, Failed: {len(res['failed'])}")
            return 0

        if args.bundle_volume:
            src = args.source or str(out_dir)
            print(f"[CLI] Bundling Volume {args.bundle_volume} from '{src}' into '{args.output}'...")
            if scan_folder_for_bundleable_volumes is None or bundle_volume_from_chapters is None:
                raise ImportError("volume_bundler module not found.")
            scan_res = scan_folder_for_bundleable_volumes(src)
            archive = bundle_volume_from_chapters(vol_num=args.bundle_volume, chapter_map=scan_res["chapter_map"], output_dir=out_dir, sync_catalog=True, prefer_official_cover=args.prefer_official_cover)
            print(f"[CLI] Finished! Archive: {archive}")
            return 0

        if args.mangaplus:
            print(f"[CLI] Downloading MangaPlus chapter ({args.lang.upper()}): {args.mangaplus}...")
            try:
                from tools.mangaplus_downloader import download_mangaplus_chapter
            except ImportError:
                from mangaplus_downloader import download_mangaplus_chapter
            archive = download_mangaplus_chapter(args.mangaplus, output_dir=out_dir, target_lang=args.lang)

            print(f"[CLI] Finished! Archive: {archive}")
            return 0

        if args.mangadex:
            lang_iso_map = {"eng": "en", "spa": "es", "fre": "fr", "ind": "id", "por": "pt-br", "deu": "de", "tha": "th", "rus": "ru", "vie": "vi"}
            lang_code = lang_iso_map.get(args.lang, args.lang)
            print(f"[CLI] Processing MangaDex chapters ({args.mangadex}) [{args.edition.upper()}, lang: {lang_code}]...")
            if download_mangadex_batch is None:
                raise ImportError("mangadex_downloader module not found.")
            summary = download_mangadex_batch(
                chapter_spec=args.mangadex,
                output_dir=out_dir,
                lang=lang_code,
                edition=args.edition,
                skip_existing=True,
                sync_catalog=True,
            )
            print(f"[CLI] Finished! Downloaded: {summary['downloaded']}, Skipped: {summary['skipped']}, Failed: {len(summary['failed'])}")
            return 0

        if args.sample:
            print(f"[CLI] Generating sample Volume {args.volume}...")
            archive = create_dummy_sample_volume(out_dir, vol_num=args.volume, page_count=args.pages)
            scan_and_index_volumes(out_dir, index_dest)
            print(f"[CLI] Finished! Archive: {archive}")
            return 0

        if args.source:
            print(f"[CLI] Packing source '{args.source}' into Volume {args.volume}...")
            archive = pack_folder_to_volume_cbz(args.source, out_dir, vol_num=args.volume)
            scan_and_index_volumes(out_dir, index_dest)
            print(f"[CLI] Finished! Archive: {archive}")
            return 0

        if args.sync_only:
            print(f"[CLI] Syncing catalog index...")
            manifest = scan_and_index_volumes(out_dir, index_dest)
            print(f"[CLI] Synced {len(manifest['volumes'])} volumes.")
            return 0

        # Default help
        parser.print_help()
        return 0

    # Launch GUI
    root = ctk.CTk()
    app = MangaOrganizerApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(run_cli())
