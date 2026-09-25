"""
catalog_indexer.py - Master catalog indexer and canon One Piece taxonomy mapper.
Auto-generates frontend/public/comics/index.json with complete canon saga & volume data.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from tools.comic_info import (
        read_comic_info_from_cbz,
        parse_comic_info,
        format_volume_display_title,
        format_chapter_display_title,
    )
except ImportError:
    from comic_info import (
        read_comic_info_from_cbz,
        parse_comic_info,
        format_volume_display_title,
        format_chapter_display_title,
    )


# ============================================================================
# CANON ONE PIECE SAGA & STORYLINE TAXONOMY
# ============================================================================

CANON_SAGAS: List[Dict[str, Any]] = [
    {
        "id": "east-blue",
        "name": "East Blue Saga",
        "japaneseName": "東の海（イーストブルー）編",
        "volumeRange": [1, 12],
        "chapterRange": [1, 100],
        "bannerUrl": "assets/arcs/east-blue.webp",
        "themeColor": "#38bdf8",
        "description": "Luffy sets sail into the East Blue to gather his first crewmates — Zoro, Nami, Usopp, and Sanji — and earn his first pirate bounty on the way to the Grand Line.",
    },
    {
        "id": "arabasta",
        "name": "Arabasta Saga",
        "japaneseName": "アラバスタ編",
        "volumeRange": [12, 24],
        "chapterRange": [101, 217],
        "bannerUrl": "assets/arcs/alabasta.webp",
        "themeColor": "#fbbf24",
        "description": "The Straw Hats enter the Grand Line with Princess Vivi of Arabasta to foil the sinister plot of Warlord Crocodile and Baroque Works.",
    },
    {
        "id": "sky-island",
        "name": "Sky Island Saga",
        "japaneseName": "空島編",
        "volumeRange": [24, 32],
        "chapterRange": [218, 303],
        "bannerUrl": "assets/arcs/skypiea.webp",
        "themeColor": "#a78bfa",
        "description": "Riding the Knock Up Stream into the clouds, the crew discovers Skypiea and battles the thunder god Enel atop the Upper Yard.",
    },
    {
        "id": "water-7",
        "name": "Water 7 Saga",
        "japaneseName": "ウォーターセブン編",
        "volumeRange": [32, 46],
        "chapterRange": [304, 441],
        "bannerUrl": "assets/arcs/water-7.webp",
        "themeColor": "#3b82f6",
        "description": "Betrayal, heartbreak, and government espionage collide in the City of Water, forcing the Straw Hats to declare war on the World Government at Enies Lobby.",
    },
    {
        "id": "thriller-bark",
        "name": "Thriller Bark Saga",
        "japaneseName": "スリラーバーク編",
        "volumeRange": [46, 50],
        "chapterRange": [442, 489],
        "bannerUrl": "assets/arcs/water-7.webp",
        "themeColor": "#c084fc",
        "description": "Trapped in the Florian Triangle, the crew meets the skeleton musician Brook and battles the shadow-stealing Warlord Gecko Moria.",
    },
    {
        "id": "summit-war",
        "name": "Summit War Saga",
        "japaneseName": "頂上戦争編",
        "volumeRange": [50, 61],
        "chapterRange": [490, 597],
        "bannerUrl": "assets/arcs/summit-war.webp",
        "themeColor": "#ef4444",
        "description": "Separated across the world, Luffy infiltrates Impel Down and rushes to Marineford to rescue his brother Portgas D. Ace in the war that reshaped the world.",
    },
    {
        "id": "fish-man-island",
        "name": "Fish-Man Island Saga",
        "japaneseName": "魚人島編",
        "volumeRange": [61, 66],
        "chapterRange": [598, 653],
        "bannerUrl": "assets/arcs/east-blue.webp",
        "themeColor": "#2dd4bf",
        "description": "Reuniting after two years of intense training, the Straw Hats descend 10,000 meters beneath the sea to Fish-Man Island.",
    },
    {
        "id": "dressrosa",
        "name": "Dressrosa Saga",
        "japaneseName": "ドレスローザ編",
        "volumeRange": [66, 80],
        "chapterRange": [654, 801],
        "bannerUrl": "assets/arcs/alabasta.webp",
        "themeColor": "#f43f5e",
        "description": "Forming a pirate alliance with Trafalgar Law, Luffy challenges Donquixote Doflamingo to liberate the puppet kingdom of Dressrosa.",
    },
    {
        "id": "four-emperors",
        "name": "Whole Cake Island Saga",
        "japaneseName": "ホールケーキアイランド編",
        "volumeRange": [80, 90],
        "chapterRange": [802, 908],
        "bannerUrl": "assets/arcs/skypiea.webp",
        "themeColor": "#f472b6",
        "description": "Luffy infiltrates Emperor Big Mom's sweet archipelago territory to rescue Sanji from an arranged political wedding.",
    },
    {
        "id": "wano",
        "name": "Wano Country Saga",
        "japaneseName": "ワノ国編",
        "volumeRange": [90, 105],
        "chapterRange": [909, 1057],
        "bannerUrl": "assets/arcs/wano.webp",
        "themeColor": "#8b5cf6",
        "description": "In the secluded samurai nation of Wano, the Ninja-Pirate-Mink-Samurai Alliance launches an epic raid on Onigashima to overthrow Emperors Kaido and Big Mom.",
    },
    {
        "id": "final-saga",
        "name": "Final Saga",
        "japaneseName": "最終章",
        "volumeRange": [105, 115],
        "chapterRange": [1058, 1200],
        "bannerUrl": "assets/arcs/final-saga.webp",
        "themeColor": "#e11d48",
        "description": "The Straw Hats arrive at the futuristic island of Egghead and onward to Elbaf, meeting Dr. Vegapunk and unveiling ancient world-shattering secrets.",
    },
]

# Sample curated canon volume database (can be dynamically extended)
CANON_VOLUMES_DATA: Dict[int, Dict[str, Any]] = {
    1: {
        "title": "Romance Dawn",
        "japaneseTitle": "ROMANCE DAWN —冒険の夜明け—",
        "arc": "Romance Dawn Arc",
        "ch_start": 1,
        "ch_end": 8,
        "pages": 210,
        "color": "#ef4444",
        "summary": "As a boy, Monkey D. Luffy dreams of becoming the King of the Pirates. Inspired by Red-Haired Shanks, Luffy sets out in a small dinghy to gather a crew.",
        "releaseDate": "1997-12-24",
    },
    2: {
        "title": "Versus!! Buggy's Pirate Crew",
        "japaneseTitle": "VERSUS!! バギー海賊団",
        "arc": "Orange Town Arc",
        "ch_start": 9,
        "ch_end": 17,
        "pages": 196,
        "color": "#f97316",
        "summary": "Luffy and his first mate, swordsman Roronoa Zoro, meet the crafty thief Nami and battle Buggy the Clown and his circus pirate crew.",
        "releaseDate": "1998-04-03",
    },
    3: {
        "title": "Don't Get Fooled Again",
        "japaneseTitle": "偽れぬもの",
        "arc": "Syrup Village Arc",
        "ch_start": 18,
        "ch_end": 26,
        "pages": 194,
        "color": "#eab308",
        "summary": "The Straw Hats arrive at Syrup Village and join the habitual liar Usopp to protect the wealthy heiress Kaya from her traitorous butler, Captain Kuro.",
        "releaseDate": "1998-06-04",
    },
    4: {
        "title": "The Crescent Moon",
        "japaneseTitle": "三日月",
        "arc": "Syrup Village Arc",
        "ch_start": 27,
        "ch_end": 35,
        "pages": 196,
        "color": "#84cc16",
        "summary": "Usopp stands his ground against the Black Cat Pirates. Impressed by his bravery, Luffy invites Usopp to join the crew, gaining their beloved ship, the Going Merry.",
        "releaseDate": "1998-08-04",
    },
    5: {
        "title": "For Whom the Bell Tolls",
        "japaneseTitle": "誰が為に鐘は鳴る",
        "arc": "Baratie Arc",
        "ch_start": 36,
        "ch_end": 44,
        "pages": 192,
        "color": "#10b981",
        "summary": "Seeking a cook, the Straw Hats visit the floating ocean restaurant Baratie, where they meet Sanji and witness the terrifying power of Dracule Mihawk.",
        "releaseDate": "1998-10-02",
    },
    6: {
        "title": "The Oath",
        "japaneseTitle": "誓い",
        "arc": "Baratie Arc",
        "ch_start": 45,
        "ch_end": 53,
        "pages": 192,
        "color": "#06b6d4",
        "summary": "Zoro duels Mihawk and swears never to lose again. Meanwhile, Don Krieg attempts to seize the Baratie by force, leading to a fiery showdown with Luffy.",
        "releaseDate": "1998-12-03",
    },
    7: {
        "title": "The Crap-Geezer",
        "japaneseTitle": "クソジジイ",
        "arc": "Baratie Arc",
        "ch_start": 54,
        "ch_end": 62,
        "pages": 192,
        "color": "#3b82f6",
        "summary": "Sanji recalls his past with Chef Zeff and the shared dream of the All Blue. Luffy dismantles Krieg's armor, and Sanji officially enlists as the crew's chef.",
        "releaseDate": "1999-03-04",
    },
    8: {
        "title": "I Won't Die",
        "japaneseTitle": "死なねェよ",
        "arc": "Arlong Park Arc",
        "ch_start": 63,
        "ch_end": 71,
        "pages": 194,
        "color": "#6366f1",
        "summary": "The crew tracks Nami to Cocoyasi Village, uncovering her tragic childhood under the ruthless Fish-Man pirate Arlong.",
        "releaseDate": "1999-04-30",
    },
    9: {
        "title": "Tears",
        "japaneseTitle": "涙",
        "arc": "Arlong Park Arc",
        "ch_start": 72,
        "ch_end": 81,
        "pages": 196,
        "color": "#8b5cf6",
        "summary": "Nami breaks down in tears and asks Luffy for help. Placing his straw hat on her head, Luffy leads his crew into Arlong Park for retribution.",
        "releaseDate": "1999-07-02",
    },
    10: {
        "title": "OK, Let's STAND UP!",
        "japaneseTitle": "OK, Let's STAND UP!",
        "arc": "Arlong Park Arc",
        "ch_start": 82,
        "ch_end": 90,
        "pages": 192,
        "color": "#d946ef",
        "summary": "Luffy destroys Arlong Park with Gomu Gomu no Battle Axe, freeing Nami from her bondage and declaring her his navigator.",
        "releaseDate": "1999-10-04",
    },
    11: {
        "title": "The Meanest Man in the East",
        "japaneseTitle": "東一番の悪",
        "arc": "Loguetown Arc",
        "ch_start": 91,
        "ch_end": 100,
        "pages": 192,
        "color": "#f43f5e",
        "summary": "With a 30,000,000 Berry bounty on his head, Luffy visits Loguetown — the city of the beginning and the end where Pirate King Gold Roger was executed.",
        "releaseDate": "1999-12-02",
    },
    12: {
        "title": "The Legend Begins",
        "japaneseTitle": "伝説は始まった",
        "arc": "Loguetown / Reverse Mountain",
        "ch_start": 101,
        "ch_end": 109,
        "pages": 192,
        "color": "#fb7185",
        "summary": "Narrowly escaping execution atop the scaffold, the Straw Hats climb Reverse Mountain and enter the legendary Grand Line.",
        "releaseDate": "2000-02-02",
    },
    # Alabasta Highlights
    13: {"title": "It's All Right!", "japaneseTitle": "大丈夫!!!", "arc": "Whiskey Peak Arc", "ch_start": 110, "ch_end": 118, "pages": 194, "color": "#f59e0b", "summary": "The Straw Hats encounter the enigmatic Baroque Works at Whiskey Peak.", "releaseDate": "2000-04-28"},
    14: {"title": "Instinct", "japaneseTitle": "本能", "arc": "Little Garden Arc", "ch_start": 119, "ch_end": 127, "pages": 196, "color": "#10b981", "summary": "Prehistoric giants Dorry and Brogy battle in an eternal duel on Little Garden.", "releaseDate": "2000-07-04"},
    15: {"title": "Straight Ahead!!!", "japaneseTitle": "まっすぐ!!!", "arc": "Drum Island Arc", "ch_start": 128, "ch_end": 136, "pages": 192, "color": "#0284c7", "summary": "Seeking a doctor for a sick Nami, the crew climbs the frozen Drum Rockies.", "releaseDate": "2000-09-04"},
    16: {"title": "Carrying on His Will", "japaneseTitle": "受け継ぐ意志", "arc": "Drum Island Arc", "ch_start": 137, "ch_end": 145, "pages": 192, "color": "#ec4899", "summary": "Tony Tony Chopper reveals his tragic past and joins as the crew's doctor.", "releaseDate": "2000-12-04"},
    22: {"title": "Hope!!", "japaneseTitle": "HOPE!!", "arc": "Arabasta Arc", "ch_start": 196, "ch_end": 206, "pages": 216, "color": "#f59e0b", "summary": "Luffy unleashes Gomu Gomu no Storm to defeat Crocodile and end the civil war.", "releaseDate": "2002-02-04"},
    25: {"title": "The 100 Million Man", "japaneseTitle": "一億の男", "arc": "Jaya Arc", "ch_start": 227, "ch_end": 236, "pages": 208, "color": "#8b5cf6", "summary": "Luffy meets Blackbeard in Mock Town and punches Bellamy with a single blow.", "releaseDate": "2002-09-04"},
    30: {"title": "Capriccio", "japaneseTitle": "狂想曲", "arc": "Skypiea Arc", "ch_start": 276, "ch_end": 285, "pages": 208, "color": "#38bdf8", "summary": "Luffy rings the golden bell of Shandora, echoing his triumph to the seas below.", "releaseDate": "2003-10-03"},
    41: {"title": "Declaration of War", "japaneseTitle": "宣戦布告", "arc": "Enies Lobby Arc", "ch_start": 389, "ch_end": 399, "pages": 208, "color": "#ef4444", "summary": "Sogeking shoots down the World Government flag, and Robin cries out 'I want to live!'", "releaseDate": "2006-04-04"},
    44: {"title": "Let's Go Back", "japaneseTitle": "帰ろう", "arc": "Enies Lobby Arc", "ch_start": 420, "ch_end": 430, "pages": 208, "color": "#f97316", "summary": "Luffy uses Gear Second and Jet Gatling to overcome Rob Lucci. The Merry bids farewell.", "releaseDate": "2006-12-04"},
    59: {"title": "Portgas D. Ace Dies", "japaneseTitle": "ポートガス・D・エース死す", "arc": "Marineford Arc", "ch_start": 574, "ch_end": 584, "pages": 208, "color": "#dc2626", "summary": "The devastating climax of the Paramount War at Marineford.", "releaseDate": "2010-08-04"},
    61: {"title": "Romance Dawn for the New World", "japaneseTitle": "ROMANCE DAWN for the new world", "arc": "Return to Sabaody Arc", "ch_start": 595, "ch_end": 605, "pages": 208, "color": "#14b8a6", "summary": "The crew reunites after two years, stronger and ready to enter the New World.", "releaseDate": "2011-02-04"},
    89: {"title": "BADEND MUSICAL", "japaneseTitle": "BADEND MUSICAL", "arc": "Whole Cake Island Arc", "ch_start": 891, "ch_end": 900, "pages": 200, "color": "#ec4899", "summary": "Luffy uses Snake-man in the mirror world to battle Charlotte Katakuri.", "releaseDate": "2018-06-04"},
    100: {"title": "Color of the Supreme King", "japaneseTitle": "覇王色", "arc": "Wano Country Arc", "ch_start": 1005, "ch_end": 1015, "pages": 208, "color": "#8b5cf6", "summary": "Historic landmark 100th volume. The rooftop clash against Kaido reaches fever pitch.", "releaseDate": "2021-09-03"},
    103: {"title": "Warrior of Liberation", "japaneseTitle": "解放の戦士", "arc": "Wano Country Arc", "ch_start": 1036, "ch_end": 1046, "pages": 208, "color": "#fbbf24", "summary": "Gear 5 Sun God Nika awakens with the drums of liberation!", "releaseDate": "2022-08-04"},
    105: {"title": "Luffy's Dream", "japaneseTitle": "ルフィの夢", "arc": "Egghead Arc", "ch_start": 1056, "ch_end": 1065, "pages": 208, "color": "#f43f5e", "summary": "Departure from Wano and arrival at Egghead, Future Island of Dr. Vegapunk.", "releaseDate": "2023-03-03"},
    108: {"title": "Better Off Dead in This World", "japaneseTitle": "死んだ方がいい世界", "arc": "Egghead Arc", "ch_start": 1089, "ch_end": 1100, "pages": 208, "color": "#6366f1", "summary": "Bartholomew Kuma's heartbreaking past is revealed as Saturn descends on Egghead.", "releaseDate": "2024-03-04"},
}


def get_saga_for_volume(vol_num: int) -> Dict[str, Any]:
    """Finds the corresponding canon saga for a given volume number."""
    for saga in CANON_SAGAS:
        v_min, v_max = saga["volumeRange"]
        if v_min <= vol_num <= v_max:
            return saga
    return CANON_SAGAS[-1]  # Default to Final Saga for modern high volumes


_CANON_VOLUME_TITLES_CACHE: Optional[Dict[int, Dict[str, Any]]] = None

def load_canon_volume_titles() -> Dict[int, Dict[str, Any]]:
    global _CANON_VOLUME_TITLES_CACHE
    if _CANON_VOLUME_TITLES_CACHE is None:
        _CANON_VOLUME_TITLES_CACHE = {}
        paths = [
            Path(__file__).resolve().parent / "canon_volume_titles.json",
            Path(__file__).resolve().parent.parent / "frontend" / "public" / "comics" / "canon_volume_titles.json",
        ]
        for p in paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        _CANON_VOLUME_TITLES_CACHE = {int(k): v for k, v in raw.items()}
                        break
                except Exception:
                    pass
    return _CANON_VOLUME_TITLES_CACHE or {}


def get_volume_meta(vol_num: int) -> Dict[str, Any]:
    """Retrieves canon metadata or calculates sensible canon defaults."""
    v_cache = load_canon_volume_titles()
    if vol_num in v_cache:
        v_info = v_cache[vol_num]
        info = {
            "title": v_info.get("title") or f"Volume {vol_num}",
            "japaneseTitle": v_info.get("japaneseTitle", f"巻{vol_num}"),
            "arc": CANON_VOLUMES_DATA.get(vol_num, {}).get("arc") or f"Volume {vol_num}",
            "ch_start": v_info.get("ch_start") or max(1, (vol_num - 1) * 10 + 1),
            "ch_end": v_info.get("ch_end") or (v_info.get("ch_start") + 9 if v_info.get("ch_start") else vol_num * 10),
            "pages": CANON_VOLUMES_DATA.get(vol_num, {}).get("pages", 200),
            "color": CANON_VOLUMES_DATA.get(vol_num, {}).get("color", "#a8c7fa"),
            "summary": v_info.get("summary") or CANON_VOLUMES_DATA.get(vol_num, {}).get("summary", ""),
            "releaseDate": v_info.get("originalReleaseDate") or v_info.get("licensedReleaseDate") or "2024-01-01",
            "isbn": v_info.get("licensedISBN") or v_info.get("originalISBN") or "",
        }
    elif vol_num in CANON_VOLUMES_DATA:
        info = CANON_VOLUMES_DATA[vol_num].copy()
    else:
        # Calculate approximate canon chapter range (approx ~10-11 chapters per volume)
        ch_start = max(1, (vol_num - 1) * 10 + 1)
        ch_end = ch_start + 9
        info = {
            "title": f"Volume {vol_num}",
            "japaneseTitle": f"巻{vol_num}",
            "arc": f"Grand Line Journey Vol {vol_num}",
            "ch_start": ch_start,
            "ch_end": ch_end,
            "pages": 200,
            "color": "#a8c7fa",
            "summary": f"One Piece Volume {vol_num}, continuing the journey across the Grand Line.",
            "releaseDate": "2024-01-01",
        }

    saga = get_saga_for_volume(vol_num)
    cover_file = f"cover-v{vol_num:02d}.jpg"
    raw_title = info.get("title", "").strip()
    clean_title = raw_title.replace(":", " - ").replace("/", "-").replace("\\", "-")
    clean_title = re.sub(r'[*?"<>|]', "", clean_title).strip()
    cbz_default_name = f"Volume {vol_num} - {clean_title}.cbz" if clean_title else f"Volume {vol_num}.cbz"

    # Check if back cover exists on disk
    script_dir = Path(__file__).resolve().parent
    public_covers = script_dir.parent / "frontend" / "public" / "comics" / "covers"
    back_cover_url = None
    if (public_covers / f"back-cover-v{vol_num:02d}.jpg").exists():
        back_cover_url = f"comics/covers/back-cover-v{vol_num:02d}.jpg"
    elif (public_covers / f"back-cover-v{vol_num:02d}.webp").exists():
        back_cover_url = f"comics/covers/back-cover-v{vol_num:02d}.webp"

    return {
        "id": f"one-piece-v{vol_num:02d}",
        "volumeNumber": vol_num,
        "title": info["title"],
        "japaneseTitle": info.get("japaneseTitle", ""),
        "sagaId": saga["id"],
        "sagaName": saga["name"],
        "arcName": info.get("arc", saga["name"]),
        "chapterStart": info.get("ch_start", 1),
        "chapterEnd": info.get("ch_end", 1),
        "pageCount": info.get("pages", 200),
        "coverUrl": f"comics/covers/{cover_file}",
        "backCoverUrl": back_cover_url,
        "spineColor": info.get("color", saga["themeColor"]),
        "releaseDate": info.get("releaseDate", ""),
        "summary": info.get("summary", ""),
        "cbzFile": cbz_default_name,
        "available": False,
    }


def scan_and_index_volumes(
    comics_dir: str | Path,
    output_json_path: Optional[str | Path] = None,
    extract_covers: bool = True,
) -> Dict[str, Any]:
    """
    Scans comics_dir for CBZ files, parses ComicInfo.xml metadata if present,
    correlates with canon saga taxonomy, maps official Viz covers,
    and returns/writes the master index.json.
    """
    comics_path = Path(comics_dir).resolve()
    comics_path.mkdir(parents=True, exist_ok=True)
    covers_dir = comics_path / "covers"
    if extract_covers:
        covers_dir.mkdir(parents=True, exist_ok=True)

    # Master list of volume entries mapped by volume number
    catalog_volumes: Dict[int, Dict[str, Any]] = {}

    # Load existing manifest to preserve remote cbzUrls and existing chapter TOCs
    existing_remote_urls: Dict[int, str] = {}
    existing_tocs: Dict[int, List[Dict[str, Any]]] = {}
    if output_json_path and Path(output_json_path).exists():
        try:
            with open(output_json_path, "r", encoding="utf-8") as f_ex:
                ex_data = json.load(f_ex)
                for ex_v in ex_data.get("volumes", []):
                    vnum = ex_v.get("volumeNumber")
                    if vnum is not None:
                        if ex_v.get("cbzUrl"):
                            existing_remote_urls[int(vnum)] = ex_v["cbzUrl"]
                        if ex_v.get("chapters"):
                            existing_tocs[int(vnum)] = ex_v["chapters"]
        except Exception as e:
            print(f"Notice: Could not load existing manifest for url preservation: {e}")

    # 1. Populate all canon volumes covering all sagas.
    # Check covers_dir for the highest available cover number (at least 108, up to 113)
    max_vol = 108
    if covers_dir.exists():
        for f in covers_dir.glob("cover-v*.*"):
            m = re.search(r"cover-v(\d+)", f.stem)
            if m:
                v_num = int(m.group(1))
                if v_num > max_vol:
                    max_vol = v_num

    for v_num in range(1, max_vol + 1):
        meta = get_volume_meta(v_num)
        # Verify cover file existence
        if (covers_dir / f"cover-v{v_num:02d}.jpg").exists():
            meta["coverUrl"] = f"comics/covers/cover-v{v_num:02d}.jpg"
        elif (covers_dir / f"cover-v{v_num:02d}.webp").exists():
            meta["coverUrl"] = f"comics/covers/cover-v{v_num:02d}.webp"

        # Verify back cover file existence
        if (covers_dir / f"back-cover-v{v_num:02d}.jpg").exists():
            meta["backCoverUrl"] = f"comics/covers/back-cover-v{v_num:02d}.jpg"
        elif (covers_dir / f"back-cover-v{v_num:02d}.webp").exists():
            meta["backCoverUrl"] = f"comics/covers/back-cover-v{v_num:02d}.webp"
        else:
            meta["backCoverUrl"] = None
        catalog_volumes[v_num] = meta

    # 2. Inspect physical files in comics_dir
    volume_pattern = re.compile(
        r"(?:^Volume\s*(\d+)|One\s*Piece.*?v(?:ol)?\.?\s*(\d+)|v(?:ol)?\.?\s*(\d+))", re.IGNORECASE
    )

    cbz_files = list(comics_path.glob("*.cbz")) + list(comics_path.glob("*.zip"))
    # Sort files so English releases take precedence over fallback language versions
    cbz_files.sort(key=lambda p: (1 if "English" in p.name else 0, p.name))
    for file_path in cbz_files:
        vol_num: Optional[int] = None
        is_chapter_file = bool(re.match(r"^Chapter\s+\d+", file_path.name, re.IGNORECASE))
        is_real_volume_cbz = False

        if not is_chapter_file:
            match = volume_pattern.search(file_path.stem)
            if match:
                vol_num = int(match.group(1) or match.group(2) or match.group(3))
                is_real_volume_cbz = True

        # Check ComicInfo.xml inside CBZ
        comic_info = read_comic_info_from_cbz(str(file_path))
        if comic_info and not is_real_volume_cbz and not is_chapter_file:
            if "Volume" in comic_info and comic_info["Volume"].isdigit():
                vol_num = int(comic_info["Volume"])
                is_real_volume_cbz = True

        if vol_num is None:
            continue

        base_meta = catalog_volumes.get(vol_num, get_volume_meta(vol_num))
        if is_real_volume_cbz or not base_meta.get("isRealVolume"):
            base_meta["cbzFile"] = file_path.name
            base_meta["available"] = True
            base_meta["fileSize"] = file_path.stat().st_size
            if is_real_volume_cbz:
                base_meta["isRealVolume"] = True


        if comic_info and comic_info.get("Title"):
            raw_title = comic_info["Title"]
            if is_real_volume_cbz:
                base_meta["title"] = format_volume_display_title(vol_num, raw_title)
            else:
                base_meta["title"] = format_chapter_display_title(vol_num, raw_title)
            if comic_info.get("Summary"):
                base_meta["summary"] = comic_info["Summary"]
            if comic_info.get("StartChapter") and comic_info["StartChapter"].isdigit():
                base_meta["chapterStart"] = int(comic_info["StartChapter"])
            if comic_info.get("EndChapter") and comic_info["EndChapter"].isdigit():
                base_meta["chapterEnd"] = int(comic_info["EndChapter"])
            if comic_info.get("PageCount") and comic_info["PageCount"].isdigit():
                base_meta["pageCount"] = int(comic_info["PageCount"])
        else:
            # Fallback title from filename
            if is_real_volume_cbz:
                base_meta["title"] = format_volume_display_title(vol_num, file_path.stem)
            else:
                base_meta["title"] = format_chapter_display_title(vol_num, file_path.stem)

        # Retain official Viz cover if present; otherwise extract first page
        if (covers_dir / f"cover-v{vol_num:02d}.jpg").exists():
            base_meta["coverUrl"] = f"comics/covers/cover-v{vol_num:02d}.jpg"
        elif (covers_dir / f"cover-v{vol_num:02d}.webp").exists():
            base_meta["coverUrl"] = f"comics/covers/cover-v{vol_num:02d}.webp"
        elif extract_covers and PIL_AVAILABLE:
            cover_dest = covers_dir / f"cover-v{vol_num:02d}.webp"
            if not cover_dest.exists():
                try:
                    import zipfile
                    with zipfile.ZipFile(file_path, "r") as z:
                        image_files = [
                            f
                            for f in z.namelist()
                            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
                            and not f.startswith("__MACOSX")
                        ]
                        if image_files:
                            image_files.sort()
                            img_data = z.read(image_files[0])
                            img = Image.open(io.BytesIO(img_data)).convert("RGB")
                            img.thumbnail((600, 900), Image.Resampling.LANCZOS)
                            img.save(cover_dest, "WEBP", quality=85)
                            base_meta["coverUrl"] = f"comics/covers/cover-v{vol_num:02d}.webp"
                except Exception as e:
                    print(f"Notice: Could not extract cover for {file_path.name}: {e}")

        # Check for back cover
        if (covers_dir / f"back-cover-v{vol_num:02d}.jpg").exists():
            base_meta["backCoverUrl"] = f"comics/covers/back-cover-v{vol_num:02d}.jpg"
        elif (covers_dir / f"back-cover-v{vol_num:02d}.webp").exists():
            base_meta["backCoverUrl"] = f"comics/covers/back-cover-v{vol_num:02d}.webp"
        else:
            base_meta["backCoverUrl"] = None

        # Check if archive has toc.json
        if is_real_volume_cbz:
            try:
                import zipfile
                with zipfile.ZipFile(file_path, "r") as z_toc:
                    if "toc.json" in z_toc.namelist():
                        toc_content = json.loads(z_toc.read("toc.json").decode("utf-8"))
                        if toc_content.get("chapters"):
                            base_meta["chapters"] = toc_content["chapters"]
            except Exception:
                pass

        # Restore preserved remote cbzUrl and chapters if not set
        if vol_num in existing_remote_urls and not base_meta.get("cbzUrl"):
            base_meta["cbzUrl"] = existing_remote_urls[vol_num]
        if vol_num in existing_tocs and not base_meta.get("chapters"):
            base_meta["chapters"] = existing_tocs[vol_num]

        catalog_volumes[vol_num] = base_meta

    # Sort volumes sequentially
    sorted_volumes = [catalog_volumes[k] for k in sorted(catalog_volumes.keys())]

    # Calculate saga volume counts
    sagas_with_counts = []
    for s in CANON_SAGAS:
        s_copy = s.copy()
        matching_vols = [v for v in sorted_volumes if v["sagaId"] == s["id"]]
        s_copy["volumeCount"] = len(matching_vols)
        sagas_with_counts.append(s_copy)

    manifest = {
        "series": "One Piece",
        "author": "Eiichiro Oda",
        "publisher": "Shueisha",
        "updatedAt": "2026-09-25T07:45:00Z",
        "totalVolumes": len(sorted_volumes),
        "sagas": sagas_with_counts,
        "volumes": sorted_volumes,
    }

    if output_json_path:
        out_path = Path(output_json_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"Catalog manifest successfully written to: {out_path}")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="One Piece Manga Catalog Indexer")
    parser.add_argument(
        "--scan",
        type=str,
        default="../frontend/public/comics",
        help="Directory containing CBZ volumes",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="../frontend/public/comics/index.json",
        help="Path to output index.json manifest",
    )
    parser.add_argument(
        "--no-covers", action="store_true", help="Skip extracting cover images"
    )

    args = parser.parse_args()
    manifest = scan_and_index_volumes(
        comics_dir=args.scan,
        output_json_path=args.output,
        extract_covers=not args.no_covers,
    )
    print(
        f"Indexed {len(manifest['volumes'])} volumes across {len(manifest['sagas'])} sagas."
    )


if __name__ == "__main__":
    main()
