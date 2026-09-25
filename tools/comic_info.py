"""
comic_info.py - Generates and parses ComicRack-compliant ComicInfo.xml metadata.
Adheres strictly to the ComicInfo schema specification for digital manga.
"""

from __future__ import annotations

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
