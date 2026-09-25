"""
comic_info.py - Generates and parses ComicRack-compliant ComicInfo.xml metadata.
Adheres strictly to the ComicInfo schema specification for digital manga.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, Dict, Optional


def build_comic_info_xml(
    series: str = "One Piece",
    volume: int | str = 1,
    number: int | str = 1,
    ch_start: int | str = 1,
    ch_end: Optional[int | str] = None,
    count: int | str = 0,
    title: str = "",
    summary: str = "",
    writer: str = "Eiichiro Oda",
    penciller: str = "Eiichiro Oda",
    publisher: str = "Shueisha",
    genre: str = "Action, Adventure, Fantasy, Shounen",
    manga: str = "YesAndRightToLeft",
    format_type: str = "Digital",
    language_iso: str = "en",
    age_rating: str = "Teen",
    web: str = "https://onepiece.fandom.com",
    extra_fields: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Constructs a well-formed ComicInfo.xml string.
    """
    root = ET.Element(
        "ComicInfo",
        {
            "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        },
    )

    fields = [
        ("Title", title or (f"Volume {volume}" if not title else title)),
        ("Series", series),
        ("Volume", str(volume)),
        ("Number", str(number if number is not None else volume)),
        ("StartChapter", str(ch_start)),
        ("EndChapter", str(ch_end) if ch_end is not None else str(ch_start)),
        ("PageCount", str(count)),
        ("Format", format_type),
        ("Manga", manga),
        ("Summary", summary),
        ("Writer", writer),
        ("Penciller", penciller),
        ("Publisher", publisher),
        ("Genre", genre),
        ("LanguageISO", language_iso),
        ("AgeRating", age_rating),
        ("Web", web),
    ]

    for tag, val in fields:
        if val is not None and val != "":
            el = ET.SubElement(root, tag)
            el.text = str(val)

    if extra_fields:
        for k, v in extra_fields.items():
            if v is not None and v != "":
                el = ET.SubElement(root, k)
                el.text = str(v)

    # Indent for clean formatting
    ET.indent(root, space="  ")
    raw_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return raw_xml.decode("utf-8")


def parse_comic_info(xml_content: str | bytes) -> Dict[str, str]:
    """
    Parses a ComicInfo.xml string or bytes into a dictionary.
    """
    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")

    result: Dict[str, str] = {}
    try:
        root = ET.fromstring(xml_content)
        for child in root:
            # Strip XML namespace if any
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            result[tag] = (child.text or "").strip()
    except Exception as e:
        result["_error"] = str(e)

    return result


def read_comic_info_from_cbz(cbz_path: str) -> Optional[Dict[str, str]]:
    """
    Extracts and parses ComicInfo.xml from a .cbz archive if it exists.
    """
    try:
        with zipfile.ZipFile(cbz_path, "r") as z:
            for filename in z.namelist():
                if filename.lower().endswith("comicinfo.xml"):
                    content = z.read(filename)
                    return parse_comic_info(content)
    except Exception:
        return None
    return None


def write_comic_info_to_cbz(cbz_path: str, comic_info_xml: str) -> bool:
    """
    Updates or inserts ComicInfo.xml inside an existing .cbz archive.
    """
    try:
        # Re-pack zip with updated ComicInfo.xml
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        temp_zip = f"{temp_dir}/temp.cbz"

        with zipfile.ZipFile(cbz_path, "r") as zin:
            with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename.lower() != "comicinfo.xml":
                        zout.writestr(item, zin.read(item.filename))
                zout.writestr("ComicInfo.xml", comic_info_xml.encode("utf-8"))

        shutil.move(temp_zip, cbz_path)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return True
    except Exception as err:
        print(f"Error writing ComicInfo.xml to {cbz_path}: {err}")
        return False


def clean_chapter_sub_title(raw_title: str, ch_num: Optional[int | float | str] = None) -> str:
    """
    Cleans a chapter subtitle by aggressively stripping redundant prefixes like
    'Chapter X', 'Ch. X', 'c001', chapter numbers, duplicate hyphens, colons,
    and Windows-illegal characters.
    Prevents duplicate naming like 'Chapter 1 - Chapter 1 - Romance Dawn.cbz'.
    """
    if not raw_title:
        return ""
    t = str(raw_title).strip()

    # If ch_num is provided, specifically strip variations of that chapter number
    if ch_num is not None:
        try:
            ch_float = float(ch_num)
            int_str = str(int(ch_float)) if ch_float.is_integer() else str(ch_float)
        except Exception:
            int_str = str(ch_num)
        ch_raw = str(ch_num).strip()
        num_patterns = [re.escape(ch_raw), re.escape(int_str), rf"0+{re.escape(int_str)}"]
        combined_num = "(?:" + "|".join(num_patterns) + ")"

        # Match "Chapter 1 - ", "Ch 01: ", "c1 ", "1 - ", etc.
        pat = rf"^(?:chapter\b|ch\b|ch\.|c)?\s*{combined_num}\s*[:\-–—]?\s*"
        while re.search(pat, t, re.IGNORECASE):
            new_t = re.sub(pat, "", t, count=1, flags=re.IGNORECASE).strip()
            if new_t == t:
                break
            t = new_t

    # Generic strip of any remaining leading "Chapter X", "Ch. X" with or without punctuation
    generic_pat = r"^(?:chapter\b|ch\b|ch\.|c)\s*\d+(?:\.\d+)?\s*[:\-–—]?\s*"
    while re.search(generic_pat, t, re.IGNORECASE):
        new_t = re.sub(generic_pat, "", t, count=1, flags=re.IGNORECASE).strip()
        if new_t == t:
            break
        t = new_t

    # Strip any leading 'Chapter' or 'Ch' word without number (require word boundary)
    t = re.sub(r"^(?:chapter\b|ch\b|ch\.)\s*[:\-–—]?\s*", "", t, flags=re.IGNORECASE).strip()

    # Strip leftover leading hyphens, colons, or punctuation
    t = re.sub(r"^[:\-–—\s]+", "", t).strip()

    # Clean Windows-illegal characters: \ / : * ? " < > |
    t = t.replace(":", " - ").replace("/", "-").replace("\\", "-")
    t = re.sub(r'[*?"<>|]', "", t)

    # Normalize whitespace and collapse multiple dashes
    t = re.sub(r"\s*-\s*-\s*", " - ", t)
    t = re.sub(r"\s*-\s*:\s*", " - ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^[:\-–—\s]+", "", t).strip()

    # If nothing meaningful remains
    if t.lower() in {"", "chapter", "ch", "none", "null", "undefined"}:
        return ""

    return t


def format_chapter_filename(ch_num: int | float | str, raw_title: str = "") -> str:
    """
    Returns a standardized chapter CBZ filename:
    'Chapter {ch_num} - {cleaned_title}.cbz' or 'Chapter {ch_num}.cbz'.
    GUARANTEES that duplicate prefixes like 'Chapter 1 - Chapter 1 - ...' never happen.
    """
    try:
        ch_float = float(ch_num)
        clean_num = int(ch_float) if ch_float.is_integer() else ch_float
    except Exception:
        clean_num = str(ch_num).strip()

    sub = clean_chapter_sub_title(raw_title, ch_num)
    if sub:
        return f"Chapter {clean_num} - {sub}.cbz"
    return f"Chapter {clean_num}.cbz"


def format_chapter_display_title(ch_num: int | float | str, raw_title: str = "") -> str:
    """
    Returns a standardized display title for ComicInfo.xml and UI:
    'Chapter {ch_num}: {cleaned_title}' or 'Chapter {ch_num}'.
    """
    try:
        ch_float = float(ch_num)
        clean_num = int(ch_float) if ch_float.is_integer() else ch_float
    except Exception:
        clean_num = str(ch_num).strip()

    sub = clean_chapter_sub_title(raw_title, ch_num)
    if sub:
        return f"Chapter {clean_num}: {sub}"
    return f"Chapter {clean_num}"


def clean_volume_sub_title(raw_title: str, vol_num: Optional[int | str] = None) -> str:
    """
    Cleans a volume subtitle by aggressively stripping redundant prefixes like
    'Volume X', 'Vol. X', 'v01', volume numbers, duplicate hyphens, colons,
    and Windows-illegal characters.
    Prevents duplicate naming like 'Volume 1 - Volume 1 - Romance Dawn.cbz'.
    """
    if not raw_title:
        return ""
    t = str(raw_title).strip()

    if vol_num is not None:
        try:
            v_int = int(vol_num)
            int_str = str(v_int)
        except Exception:
            int_str = str(vol_num)
        v_raw = str(vol_num).strip()
        num_patterns = [re.escape(v_raw), re.escape(int_str), rf"0+{re.escape(int_str)}"]
        combined_num = "(?:" + "|".join(num_patterns) + ")"

        pat = rf"^(?:volume\b|vol\b|vol\.|v)?\s*{combined_num}\s*[:\-–—]?\s*"
        while re.search(pat, t, re.IGNORECASE):
            new_t = re.sub(pat, "", t, count=1, flags=re.IGNORECASE).strip()
            if new_t == t:
                break
            t = new_t

    generic_pat = r"^(?:volume\b|vol\b|vol\.|v)\s*\d+\s*[:\-–—]?\s*"
    while re.search(generic_pat, t, re.IGNORECASE):
        new_t = re.sub(generic_pat, "", t, count=1, flags=re.IGNORECASE).strip()
        if new_t == t:
            break
        t = new_t

    # Strip any leading 'Volume' or 'Vol' word (require word boundary)
    t = re.sub(r"^(?:volume\b|vol\b|vol\.)\s*[:\-–—]?\s*", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"^[:\-–—\s]+", "", t).strip()

    # Clean Windows-illegal characters
    t = t.replace(":", " - ").replace("/", "-").replace("\\", "-")
    t = re.sub(r'[*?"<>|]', "", t)

    # Normalize whitespace and collapse multiple dashes
    t = re.sub(r"\s*-\s*-\s*", " - ", t)
    t = re.sub(r"\s*-\s*:\s*", " - ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^[:\-–—\s]+", "", t).strip()

    if t.lower() in {"", "volume", "vol", "none", "null", "undefined"}:
        return ""

    return t


def format_volume_filename(vol_num: int | str, raw_title: str = "") -> str:
    """
    Returns a standardized volume CBZ filename:
    'Volume {vol_num} - {cleaned_title}.cbz' or 'Volume {vol_num}.cbz'.
    GUARANTEES that duplicate prefixes like 'Volume 1 - Volume 1 - ...' never happen.
    """
    try:
        clean_vol = int(vol_num)
    except Exception:
        clean_vol = str(vol_num).strip()

    sub = clean_volume_sub_title(raw_title, vol_num)
    if sub:
        return f"Volume {clean_vol} - {sub}.cbz"
    return f"Volume {clean_vol}.cbz"


def format_volume_display_title(vol_num: int | str, raw_title: str = "") -> str:
    """
    Returns a standardized display title for ComicInfo.xml and UI:
    'Volume {vol_num}: {cleaned_title}' or 'Volume {vol_num}'.
    """
    try:
        clean_vol = int(vol_num)
    except Exception:
        clean_vol = str(vol_num).strip()

    sub = clean_volume_sub_title(raw_title, vol_num)
    if sub:
        return f"Volume {clean_vol}: {sub}"
    return f"Volume {clean_vol}"


if __name__ == "__main__":
    # Test generation
    sample = build_comic_info_xml(
        series="One Piece",
        volume=1,
        number=1,
        ch_start=1,
        ch_end=8,
        count=210,
        title="Romance Dawn",
        summary="Monkey D. Luffy embarks on his journey to become the Pirate King!",
    )
    print("Generated ComicInfo.xml:")
    print(sample)
    parsed = parse_comic_info(sample)
    assert parsed["Series"] == "One Piece"
    assert parsed["Volume"] == "1"
    assert parsed["StartChapter"] == "1"
    assert parsed["Manga"] == "YesAndRightToLeft"
    print("\nParsing verified successfully!")
