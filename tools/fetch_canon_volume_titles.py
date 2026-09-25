"""
fetch_canon_volume_titles.py - Scrapes and compiles canonical One Piece volume titles,
chapter ranges, original/licensed release dates, and summaries from Wikipedia.
Saves to tools/canon_volume_titles.json and mirrors to frontend/public/comics/canon_volume_titles.json.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
import requests

WIKI_PAGES = [
    "List of One Piece chapters (1–186)",
    "List of One Piece chapters (187–388)",
    "List of One Piece chapters (389–594)",
    "List of One Piece chapters (595–806)",
    "List of One Piece chapters (807–1015)",
    "List of One Piece chapters (1016–current)",
]

HEADERS = {"User-Agent": "OnePiecePlatform/1.0 (https://github.com/onepiece; contact@example.com)"}


def clean_wikitext_value(val: str) -> str:
    if not val:
        return ""
    s = val.strip()
    # Strip HTML comments <!-- ... -->
    s = re.sub(r"<!--.*?-->", "", s, flags=re.DOTALL)
    # Strip citations <ref>...</ref> or <ref ... />
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.DOTALL)
    s = re.sub(r"<ref[^>]*/>", "", s)
    # Strip nested templates iteratively
    while "{{" in s:
        new_s = re.sub(r"\{\{[^\|\}]*\|\s*([^\}]+)\}\}", r"\1", s)
        if new_s == s:
            new_s = re.sub(r"\{\{[^\}]*\}\}", "", s)
            break
        s = new_s
    # Strip wikilinks [[Target|Display]] -> Display, [[Target]] -> Target
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", s)
    # Strip HTML tags
    s = re.sub(r"<[^>]+>", "", s)
    # Normalize whitespace
    s = re.sub(r"\s+", " ", s)
    # Strip quotes
    s = s.strip('"\'').strip()
    return s


def fetch_all_volume_metadata() -> dict[int, dict]:
    s = requests.Session()
    s.headers.update(HEADERS)
    raw_volumes: dict[int, dict] = {}

    for page in WIKI_PAGES:
        print(f"Fetching volume metadata from {page}...")
        try:
            r = s.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "parse",
                    "page": page,
                    "prop": "wikitext",
                    "format": "json",
                },
                timeout=25,
            )
            if r.status_code != 200:
                print(f"  Error fetching {page}: {r.status_code}")
                continue

            text = r.json().get("parse", {}).get("wikitext", {}).get("*", "")
            blocks = text.split("{{Graphic novel list")

            for block in blocks[1:]:
                m_vol = re.search(r"VolumeNumber\s*=\s*(\d+)", block)
                if not m_vol:
                    continue
                v_num = int(m_vol.group(1))

                m_lic = re.search(r"LicensedTitle\s*=\s*([^\n]+)", block)
                m_orig = re.search(r"OriginalTitle\s*=\s*([^\n]+)", block)
                m_trans = re.search(r"TranslitTitle\s*=\s*([^\n]+)", block)
                m_orig_date = re.search(r"OriginalRelDate\s*=\s*([^\n]+)", block)
                m_lic_date = re.search(r"LicensedRelDate\s*=\s*([^\n]+)", block)
                m_orig_isbn = re.search(r"OriginalISBN\s*=\s*([^\n]+)", block)
                m_lic_isbn = re.search(r"LicensedISBN\s*=\s*([^\n]+)", block)

                m_summary = re.search(r"Summary\s*=\s*(.*?)(?=\n\s*\||\n\s*\}\})", block, re.DOTALL)

                lic_title = clean_wikitext_value(m_lic.group(1)) if m_lic else ""
                orig_title = clean_wikitext_value(m_orig.group(1)) if m_orig else ""
                trans_title = clean_wikitext_value(m_trans.group(1)) if m_trans else ""
                summary = clean_wikitext_value(m_summary.group(1)) if m_summary else ""

                ch_starts = [int(n) for n in re.findall(r"\{\{Numbered list\s*\|\s*start\s*=\s*(\d+)", block, re.IGNORECASE)]
                ch_start = min(ch_starts) if ch_starts else None

                best_english = lic_title or trans_title or f"Volume {v_num}"

                raw_volumes[v_num] = {
                    "volume": v_num,
                    "title": best_english,
                    "licensedTitle": lic_title,
                    "japaneseTitle": orig_title,
                    "translitTitle": trans_title,
                    "ch_start": ch_start,
                    "originalReleaseDate": clean_wikitext_value(m_orig_date.group(1)) if m_orig_date else "",
                    "licensedReleaseDate": clean_wikitext_value(m_lic_date.group(1)) if m_lic_date else "",
                    "originalISBN": clean_wikitext_value(m_orig_isbn.group(1)) if m_orig_isbn else "",
                    "licensedISBN": clean_wikitext_value(m_lic_isbn.group(1)) if m_lic_isbn else "",
                    "summary": summary,
                }

        except Exception as e:
            print(f"Error parsing volumes from {page}: {e}")

    # Now calculate precise ch_start and ch_end ranges
    sorted_v_nums = sorted(raw_volumes.keys())
    final_volumes: dict[int, dict] = {}

    for i, v_num in enumerate(sorted_v_nums):
        v_data = raw_volumes[v_num]
        start = v_data.get("ch_start")
        end = None

        if i + 1 < len(sorted_v_nums):
            next_start = raw_volumes[sorted_v_nums[i + 1]].get("ch_start")
            if next_start is not None:
                end = next_start - 1

        if start is not None and end is not None and end >= start:
            v_data["ch_end"] = end
            v_data["totalChapters"] = end - start + 1
        else:
            v_data["ch_end"] = end
            v_data["totalChapters"] = None

        final_volumes[v_num] = v_data

    print(f"Successfully compiled {len(final_volumes)} canon volume titles!")
    return final_volumes


def main():
    volumes = fetch_all_volume_metadata()
    script_dir = Path(__file__).resolve().parent
    out_file = script_dir / "canon_volume_titles.json"
    frontend_out = script_dir.parent / "frontend" / "public" / "comics" / "canon_volume_titles.json"

    payload = {str(k): v for k, v in sorted(volumes.items())}

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(volumes)} volume titles to {out_file}")

    if frontend_out.parent.exists():
        with open(frontend_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"Mirrored to {frontend_out}")


if __name__ == "__main__":
    main()
