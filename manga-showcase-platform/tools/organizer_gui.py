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
    from tools.comic_info import build_comic_info_xml, write_comic_info_to_cbz
    from tools.catalog_indexer import get_volume_meta, scan_and_index_volumes, CANON_VOLUMES_DATA
except ImportError:
    from comic_info import build_comic_info_xml, write_comic_info_to_cbz
    from catalog_indexer import get_volume_meta, scan_and_index_volumes, CANON_VOLUMES_DATA


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
    archive_name = f"One Piece - v{vol_num:02d} (c{ch_start:03d}-{ch_end:03d}).cbz"
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

    archive_filename = f"One Piece - v{vol_num:02d} (c{start_ch:03d}-{end_ch:03d}).cbz"
    archive_dest = out_path / archive_filename

    log_callback(f"Scanning source directory: {src_path}...")
    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
    
    # Collect all image files recursively
    image_files = [
        f for f in src_path.rglob("*")
        if f.is_file() and f.suffix.lower() in valid_exts and not f.name.startswith(".")
    ]
    image_files.sort(key=lambda p: natural_sort_key(p.name))

    page_count = len(image_files)
    log_callback(f"Found {page_count} image pages in source.")

    comic_info_xml = build_comic_info_xml(
        series="One Piece",
        volume=vol_num,
        number=vol_num,
        ch_start=start_ch,
        ch_end=end_ch,
        count=page_count,
        title=meta["title"],
        summary=meta["summary"],
    )

    log_callback(f"Packing into archive: {archive_dest.name}...")
    with zipfile.ZipFile(archive_dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ComicInfo.xml", comic_info_xml.encode("utf-8"))
        for i, img_path in enumerate(image_files, 1):
            arc_name = f"page_{i:04d}{img_path.suffix.lower()}"
            z.write(img_path, arcname=arc_name)

    log_callback(f"Volume {vol_num} CBZ created successfully! ({archive_dest})")
    return str(archive_dest)


# ============================================================================
# CUSTOMTKINTER DESKTOP GUI
# ============================================================================

class MangaOrganizerApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("One Piece Manga Organizer & Packager — MD3 Edition")
        self.root.geometry("860x680")
        self.root.minsize(780, 580)

        # Style configuration
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Paths
        base_dir = Path(__file__).resolve().parent.parent
        self.default_output_dir = str(base_dir / "frontend" / "public" / "comics")
        self.output_index_path = str(base_dir / "frontend" / "public" / "comics" / "index.json")

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
        self.src_entry.grid(row=1, column=0, sticky="ew", padx=16, pady=4)

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

        # 3. Volume and Metadata Configuration
        meta_frame = ctk.CTkFrame(content_frame, fg_color="#1e2235", corner_radius=8)
        meta_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=12)

        vol_lbl = ctk.CTkLabel(meta_frame, text="Volume #:")
        vol_lbl.grid(row=0, column=0, padx=(12, 4), pady=10)
        self.vol_spin = ctk.CTkEntry(meta_frame, width=60)
        self.vol_spin.insert(0, "1")
        self.vol_spin.grid(row=0, column=1, padx=4, pady=10)
        self.vol_spin.bind("<KeyRelease>", self._on_volume_changed)

        self.meta_preview_lbl = ctk.CTkLabel(
            meta_frame,
            text="Canon: Romance Dawn (Ch 1-8) • East Blue Saga",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#38bdf8",
        )
        self.meta_preview_lbl.grid(row=0, column=2, padx=16, pady=10, sticky="w")

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

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Select Output Directory")
        if folder:
            self.out_entry.delete(0, "end")
            self.out_entry.insert(0, folder)
            self.log(f"Selected output: {folder}")

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

    def _sync_catalog(self):
        out = self.out_entry.get().strip()
        self.log(f"Syncing catalog index for directory: {out}...")
        manifest = scan_and_index_volumes(out, self.output_index_path)
        self.log(f"Catalog indexed: {len(manifest['volumes'])} volumes, {len(manifest['sagas'])} sagas.")
        messagebox.showinfo("Catalog Synced", f"Catalog updated successfully with {len(manifest['volumes'])} volumes.")


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

    args, unknown = parser.parse_known_args()

    # Determine if we should run GUI or CLI
    if args.cli or args.sample or args.source or args.sync_only or not CTK_AVAILABLE or not os.environ.get("DISPLAY", None) and sys.platform.startswith("linux"):
        # Run CLI mode
        out_dir = Path(args.output).resolve()
        index_dest = out_dir / "index.json"

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
