"""
generate_banners.py - Generates aesthetic widescreen banner artworks for canon One Piece sagas.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

BANNERS = [
    {
        "filename": "east-blue.webp",
        "title": "EAST BLUE SAGA",
        "japanese": "東の海 編",
        "c1": (14, 165, 233),   # Ocean Blue
        "c2": (15, 23, 42),     # Deep Navy
        "accent": (56, 189, 248),
    },
    {
        "filename": "alabasta.webp",
        "title": "ARABASTA SAGA",
        "japanese": "アラバスタ 編",
        "c1": (217, 119, 6),    # Desert Sand Amber
        "c2": (69, 26, 3),      # Warm Earth
        "accent": (251, 191, 36),
    },
    {
        "filename": "skypiea.webp",
        "title": "SKY ISLAND SAGA",
        "japanese": "空島 編",
        "c1": (124, 58, 237),   # Sky Lightning Violet
        "c2": (30, 27, 75),     # Cloud Shadow
        "accent": (167, 139, 250),
    },
    {
        "filename": "water-7.webp",
        "title": "WATER 7 SAGA",
        "japanese": "ウォーターセブン 編",
        "c1": (37, 99, 235),    # Aqua Tide
        "c2": (15, 23, 42),     # Night Sea
        "accent": (96, 165, 250),
    },
    {
        "filename": "summit-war.webp",
        "title": "SUMMIT WAR SAGA",
        "japanese": "頂上戦争 編",
        "c1": (220, 38, 38),    # Magma / Fire
        "c2": (69, 10, 10),     # Ash Crimson
        "accent": (248, 113, 113),
    },
    {
        "filename": "wano.webp",
        "title": "WANO COUNTRY SAGA",
        "japanese": "ワノ国 編",
        "c1": (147, 51, 234),   # Royal Violet / Cherry
        "c2": (49, 10, 82),     # Sakura Night
        "accent": (192, 132, 252),
    },
    {
        "filename": "final-saga.webp",
        "title": "FINAL SAGA",
        "japanese": "最終章",
        "c1": (225, 29, 72),    # Future Crimson
        "c2": (23, 23, 23),     # Obsidian
        "accent": (251, 113, 133),
    },
]


def create_banner(info, out_dir: Path):
    w, h = 1200, 420
    img = Image.new("RGB", (w, h), color=info["c2"])
    draw = ImageDraw.Draw(img)

    # Gradient blend
    r1, g1, b1 = info["c1"]
    r2, g2, b2 = info["c2"]

    for x in range(w):
        t = x / w
        r = int(r1 * (1 - t) + r2 * t)
        g = int(g1 * (1 - t) + g2 * t)
        b = int(b1 * (1 - t) + b2 * t)
        draw.line([(x, 0), (x, h)], fill=(r, g, b))

    # Add artistic geometric waves/clouds and particle circles
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    # Stylized radial circles
    ar, ag, ab = info["accent"]
    ov_draw.ellipse([w - 450, -100, w + 200, 500], fill=(ar, ag, ab, 35))
    ov_draw.ellipse([w - 300, 50, w + 100, 450], fill=(ar, ag, ab, 25))
    ov_draw.ellipse([-100, -50, 400, 450], fill=(r1, g1, b1, 40))

    # Dark atmospheric vignette
    for y in range(h):
        alpha = int(180 * (y / h))
        ov_draw.line([(0, y), (w, y)], fill=(10, 12, 18, alpha))

    # Border frame
    ov_draw.rectangle([10, 10, w - 10, h - 10], outline=(255, 255, 255, 30), width=2)

    # Merge
    img.paste(overlay, (0, 0), overlay)

    # Save WebP
    dest = out_dir / info["filename"]
    img.save(dest, "WEBP", quality=90)
    print(f"Generated saga banner: {dest.name}")


def main():
    base_dir = Path(__file__).resolve().parent.parent
    arcs_dir = base_dir / "frontend" / "public" / "assets" / "arcs"
    arcs_dir.mkdir(parents=True, exist_ok=True)

    for item in BANNERS:
        create_banner(item, arcs_dir)

    print("All saga banners generated successfully!")


if __name__ == "__main__":
    main()
