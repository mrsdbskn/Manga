"""
fetch_canon_chapter_titles.py - Fetches the complete official English titles for all
One Piece chapters (1 to 1193+) directly from Wikipedia and saves to canon_chapter_titles.json.
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


def clean_title(raw: str) -> str:
    s = raw.strip()
    
    # Strip HTML comments <!-- ... -->
    s = re.sub(r"<!--.*?-->", "", s, flags=re.DOTALL).strip()
    s = s.strip('"\'')

    # Handle {{Fraction|3|8}} -> 3/8
    s = re.sub(r"\{\{Fraction\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\}\}", r"\1/\2", s, flags=re.IGNORECASE)

    # Handle {{nihongo|...}}, {{nihongo2|...}}, {{nihongo3|...}}
    # Format: {{nihongo | "Title" | kanji | romaji}}
    m_nihongo = re.match(r"^\{\{nihongo[23]?\s*\|\s*\"?([^\"|\}]+)\"?", s, re.IGNORECASE)
    if m_nihongo:
        val = m_nihongo.group(1).strip().strip('"').strip()
        val = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", val)
        val = re.sub(r"<[^>]+>", "", val)
        return val.strip()

    # Strip citations <ref>...</ref> or <ref ... />
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.DOTALL)
    s = re.sub(r"<ref[^>]*/>", "", s)

    # Strip HTML tags like <del>3D</del>2Y -> 3D2Y
    s = re.sub(r"<[^>]+>", "", s)

    # If the item starts with "Quoted Title" or Quoted Title" (e.g. "God Valley Battle Royale" (G・V・B・R, ...))
    m_quoted = re.match(r'^"?([^"]+)"', s)
    if m_quoted:
        return m_quoted.group(1).strip()

    # Strip wikilinks [[Target|Display]] -> Display, [[Target]] -> Target
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", s)

    # Strip double quotes
    s = s.strip('"\'').strip()
    return s


def parse_numbered_lists(text: str) -> dict[int, str]:
    extracted: dict[int, str] = {}
    idx = 0
    lower_text = text.lower()
    tag = "{{numbered list"
    
    while True:
        pos = lower_text.find(tag, idx)
        if pos == -1:
            break
            
        # Match braces to find the exact closing }}
        depth = 0
        end_pos = pos
        i = pos
        while i < len(text) - 1:
            if text[i:i+2] == "{{":
                depth += 1
                i += 2
                continue
            elif text[i:i+2] == "}}":
                depth -= 1
                if depth == 0:
                    end_pos = i + 2
                    break
                i += 2
                continue
            i += 1

        if depth != 0:
            idx = pos + len(tag)
            continue

        template_str = text[pos:end_pos]
        idx = end_pos

        first_pipe = template_str.find("|")
        if first_pipe == -1:
            continue
        inner = template_str[first_pipe + 1 : -2]

        # Split inner by top-level pipe '|' (respecting nested {{ }} and [[ ]])
        args = []
        cur = []
        d = 0
        b = 0
        for ch in inner:
            if ch == "{":
                d += 1
            elif ch == "}":
                d -= 1
            elif ch == "[":
                b += 1
            elif ch == "]":
                b -= 1
            elif ch == "|" and d == 0 and b == 0:
                args.append("".join(cur).strip())
                cur = []
                continue
            cur.append(ch)
        if cur:
            args.append("".join(cur).strip())

        start_num = None
        items = []
        for arg in args:
            if not arg:
                continue
            m_start = re.match(r"^start\s*=\s*(\d+)", arg, re.IGNORECASE)
            if m_start:
                start_num = int(m_start.group(1))
            else:
                items.append(arg)

        if start_num is not None:
            for offset, it in enumerate(items):
                ch_num = start_num + offset
                t = clean_title(it)
                if t:
                    extracted[ch_num] = t

    return extracted


def fetch_all_chapter_titles() -> dict[int, str]:
    s = requests.Session()
    s.headers.update(HEADERS)
    titles: dict[int, str] = {}

    for page in WIKI_PAGES:
        print(f"Fetching {page}...")
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
                print(f"Failed to fetch {page} (status {r.status_code})")
                continue

            text = r.json().get("parse", {}).get("wikitext", {}).get("*", "")
            page_titles = parse_numbered_lists(text)
            print(f"  -> Extracted {len(page_titles)} chapters from {page}")
            titles.update(page_titles)

        except Exception as e:
            print(f"Error parsing {page}: {e}")

    print(f"Successfully compiled {len(titles)} canon chapter titles (1 to {max(titles.keys()) if titles else 0})!")
    return titles


def main():
    titles = fetch_all_chapter_titles()
    script_dir = Path(__file__).resolve().parent
    out_file = script_dir / "canon_chapter_titles.json"
    frontend_out = script_dir.parent / "frontend" / "public" / "comics" / "canon_chapter_titles.json"
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in sorted(titles.items())}, f, indent=2, ensure_ascii=False)
    print(f"Saved to {out_file}")

    if frontend_out.parent.exists():
        with open(frontend_out, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in sorted(titles.items())}, f, indent=2, ensure_ascii=False)
        print(f"Mirrored to {frontend_out}")

    # Remove temporary test script if it exists
    test_file = script_dir / "test_wiki_parser.py"
    if test_file.exists():
        test_file.unlink()


if __name__ == "__main__":
    main()
