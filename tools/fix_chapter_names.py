"""
fix_chapter_names.py - Renames existing chapter CBZ files to include their canonical English titles
and updates ComicRack ComicInfo.xml metadata inside each CBZ archive.
Uses tools/canon_chapter_titles.json.
"""

from __future__ import annotations
import json
import re
import sys
import zipfile
import shutil
import tempfile
from pathlib import Path

try:
    from tools.comic_info import build_comic_info_xml, format_chapter_filename, format_chapter_display_title, clean_chapter_sub_title
    from tools.catalog_indexer import scan_and_index_volumes
except ImportError:
    from comic_info import build_comic_info_xml, format_chapter_filename, format_chapter_display_title, clean_chapter_sub_title
    from catalog_indexer import scan_and_index_volumes


def load_canon_titles() -> dict[int, str]:
    script_dir = Path(__file__).resolve().parent
    json_path = script_dir / "canon_chapter_titles.json"
    if not json_path.exists():
        json_path = script_dir.parent / "frontend" / "public" / "comics" / "canon_chapter_titles.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            return {int(k): v for k, v in raw.items()}
    return {}


def update_cbz_comic_info(cbz_path: Path, ch_num: int, title: str) -> bool:
    """Updates or inserts ComicInfo.xml inside the CBZ."""
    try:
        temp_dir = tempfile.mkdtemp()
        temp_cbz = Path(temp_dir) / "temp.cbz"
        
        display_title = format_chapter_display_title(ch_num, title)
        vol_num = max(1, (ch_num - 1) // 10 + 1)
        
        with zipfile.ZipFile(cbz_path, "r") as zin:
            page_count = len([n for n in zin.namelist() if n.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')) and not n.startswith('__')])
            xml_data = build_comic_info_xml(
                series="One Piece",
                volume=vol_num,
                number=ch_num,
                ch_start=ch_num,
                ch_end=ch_num,
                count=page_count,
                title=display_title,
                summary=f"One Piece Chapter {ch_num}: {title}",
                language_iso="en",
            )
            with zipfile.ZipFile(temp_cbz, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename.lower() != "comicinfo.xml":
                        zout.writestr(item, zin.read(item.filename))
                zout.writestr("ComicInfo.xml", xml_data.encode("utf-8"))

        shutil.move(temp_cbz, cbz_path)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return True
    except Exception as e:
        print(f"Error updating ComicInfo in {cbz_path.name}: {e}")
        return False


def fix_chapters_in_folder(folder_path: Path, canon_dict: dict[int, str]):
    if not folder_path.exists() or not folder_path.is_dir():
        return

    print(f"\nScanning {folder_path} for chapter files to rename...")
    updated_count = 0
    renamed_count = 0

    cbz_files = list(folder_path.glob("*.cbz"))
    for f in cbz_files:
        # Check if single chapter
        m = re.match(r"^Chapter\s+(\d+)(?:\s*-\s*(.*))?\.cbz$", f.name, re.IGNORECASE)
        if not m:
            continue

        ch_num = int(m.group(1))
        current_sub = (m.group(2) or "").strip()
        canon_title = canon_dict.get(ch_num, "")

        if not canon_title:
            continue

        # Check if filename needs fixing (e.g. just "Chapter 764.cbz" or duplicate)
        clean_expected_name = format_chapter_filename(ch_num, canon_title)
        
        target_path = folder_path / clean_expected_name

        if f.name != clean_expected_name:
            try:
                # Test if file is valid and complete before modifying
                with zipfile.ZipFile(f, "r") as test_z:
                    _ = test_z.namelist()
                print(f"Renaming: '{f.name}' -> '{clean_expected_name}'")
                update_cbz_comic_info(f, ch_num, canon_title)
                if target_path.exists() and target_path != f:
                    target_path.unlink()
                f.rename(target_path)
                renamed_count += 1
            except Exception as e:
                print(f"Skipping {f.name} (file may be in-use/downloading): {e}")
        else:
            # Check if internal ComicInfo needs updating
            pass

    print(f"Finished {folder_path.name}: Renamed and updated {renamed_count} chapters.")


def main():
    canon_dict = load_canon_titles()
    print(f"Loaded {len(canon_dict)} canonical chapter titles.")

    script_dir = Path(__file__).resolve().parent
    public_dir = script_dir.parent / "frontend" / "public" / "comics"
    dist_dir = script_dir.parent / "frontend" / "dist" / "comics"

    fix_chapters_in_folder(public_dir, canon_dict)
    if dist_dir.exists():
        fix_chapters_in_folder(dist_dir, canon_dict)

    print("\nRefreshing catalog index.json...")
    scan_and_index_volumes(public_dir, output_json_path=public_dir / "index.json")
    print("Catalog updated successfully!")


if __name__ == "__main__":
    main()
